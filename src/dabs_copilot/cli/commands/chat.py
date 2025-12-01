"""Chat command - Interactive REPL for DABs Copilot.

Provides a multi-turn conversational interface for generating,
validating, and deploying Databricks Asset Bundles.
"""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from ..auth import AuthenticationError, resolve_llm_config
from ..output import StreamingOutputHandler, create_welcome_panel
from ..utils import async_command, confirm_destructive_action, write_bundle_with_confirmation

# Import agent - handle both package and standalone imports
try:
    from ...agent import DABsAgent, get_custom_tool_names
except ImportError:
    from dabs_copilot.agent import DABsAgent, get_custom_tool_names


@async_command
async def chat(
    ctx: typer.Context,
    initial_message: Optional[str] = typer.Argument(
        None,
        help="Optional initial message to start the conversation",
    ),
    tool_mode: str = typer.Option(
        "custom",
        "--tool-mode",
        help="Tool backend mode: auto, mcp, or custom",
    ),
):
    """
    Start an interactive chat session with DABs Copilot.

    This provides a multi-turn conversational interface for generating,
    validating, and deploying Databricks Asset Bundles.

    [bold]Examples:[/bold]

        # Start interactive session
        dabs-copilot chat

        # Start with an initial message
        dabs-copilot chat "Help me create a bundle for job 12345"

    [bold]Commands in chat:[/bold]

        /quit, /exit  - Exit the session
        /reset        - Start new conversation
        /tools        - List available tools
        /help         - Show this help
        /save PATH    - Save last generated YAML
    """
    console: Console = ctx.obj.get("console", Console())
    verbose: bool = ctx.obj.get("verbose", False)

    # Validate LLM auth first
    try:
        resolve_llm_config()
    except AuthenticationError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    # Show welcome panel
    console.print(create_welcome_panel())
    console.print()

    # Initialize output handler
    output = StreamingOutputHandler(console=console, verbose=verbose)

    # Track last YAML for /save command
    last_yaml: Optional[str] = None

    agent = None
    try:
        while True:
            # Create agent if needed
            if agent is None:
                try:
                    agent = DABsAgent(
                        tool_mode=tool_mode,
                        confirm_destructive=confirm_destructive_action,
                    )
                    await agent.__aenter__()
                    console.print(f"[dim]Session started. Tools: {len(get_custom_tool_names())}[/dim]")
                    console.print()
                except Exception as e:
                    console.print(f"[red]Failed to initialize agent:[/red] {e}")
                    raise typer.Exit(1)

            # Handle initial message on first iteration
            if initial_message:
                user_input = initial_message
                initial_message = None  # Only use once
                console.print(f"[bold]You:[/bold] {user_input}")
            else:
                # Get user input
                try:
                    user_input = console.input("[bold]You:[/bold] ").strip()
                except (EOFError, KeyboardInterrupt):
                    console.print("\n[dim]Goodbye![/dim]")
                    break

            if not user_input:
                continue

            # Handle slash commands
            if user_input.startswith("/"):
                cmd = user_input.lower().split()[0]
                args = user_input.split()[1:] if len(user_input.split()) > 1 else []

                if cmd in ("/quit", "/exit"):
                    console.print("[dim]Goodbye![/dim]")
                    break

                elif cmd == "/reset":
                    if agent:
                        await agent.__aexit__(None, None, None)
                        agent = None
                    last_yaml = None
                    console.print("[dim]Session reset. Starting fresh...[/dim]\n")
                    continue

                elif cmd == "/tools":
                    _print_tools(console)
                    continue

                elif cmd == "/help":
                    _print_help(console)
                    continue

                elif cmd == "/save":
                    if not last_yaml:
                        console.print("[yellow]No YAML generated yet.[/yellow]")
                        continue
                    if not args:
                        console.print("[yellow]Usage: /save PATH[/yellow]")
                        continue
                    save_path = Path(args[0]).resolve()
                    write_bundle_with_confirmation(
                        last_yaml, save_path, force=False, console=console
                    )
                    continue

                else:
                    console.print(f"[yellow]Unknown command:[/yellow] {cmd}")
                    _print_help(console)
                    continue

            # Send message to agent and stream response
            console.print()
            try:
                yaml_content = await output.stream_response(agent, user_input)
                if yaml_content:
                    last_yaml = yaml_content
                    console.print()
                    console.print(
                        "[dim]Tip: Use /save PATH to save the YAML, "
                        "or ask me to refine it[/dim]"
                    )
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")

            console.print()

    finally:
        if agent:
            await agent.__aexit__(None, None, None)


def _print_help(console: Console):
    """Print help for chat commands."""
    help_text = Text()
    help_text.append("\nCommands:\n", style="bold")
    help_text.append("  /quit, /exit  - Exit the session\n")
    help_text.append("  /reset        - Start new conversation\n")
    help_text.append("  /tools        - List available tools\n")
    help_text.append("  /help         - Show this help\n")
    help_text.append("  /save PATH    - Save last generated YAML\n")
    console.print(help_text)


def _print_tools(console: Console):
    """Print available tools."""
    try:
        tools = get_custom_tool_names()
        console.print(f"\n[bold]Available tools ({len(tools)}):[/bold]")
        for tool in sorted(tools):
            # Strip the mcp__databricks__ prefix for readability
            short_name = tool.replace("mcp__databricks__", "")
            console.print(f"  • {short_name}")
        console.print()
    except Exception as e:
        console.print(f"[red]Error listing tools:[/red] {e}")
