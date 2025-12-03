"""Output handlers for DABs Copilot CLI.

Provides rich console output with streaming support, progress display,
and YAML extraction from agent responses.
"""

import re
from typing import Optional

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.text import Text

from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ToolUseBlock,
)


class StreamingOutputHandler:
    """Handle streaming output from DABsAgent with rich formatting."""

    def __init__(self, console: Optional[Console] = None, verbose: bool = False):
        """
        Initialize the output handler.

        Args:
            console: Rich console for output. Creates one if not provided.
            verbose: If True, show detailed tool calls and intermediate steps.
        """
        self.console = console or Console()
        self.verbose = verbose
        self.last_yaml_content: Optional[str] = None

    async def stream_response(
        self,
        agent,
        message: str,
        session_id: str = "default",
    ) -> Optional[str]:
        """
        Stream agent response and extract YAML content if present.

        Args:
            agent: DABsAgent instance
            message: User message to send
            session_id: Session ID for multi-turn conversations

        Returns:
            Extracted YAML content if databricks.yml was generated, else None
        """
        self.last_yaml_content = None
        full_response = ""
        tool_calls = []  # Track tool calls for display

        if self.verbose:
            # Verbose mode: show everything with live updating
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
                transient=True,
            ) as progress:
                task = progress.add_task("Thinking...", total=None)

                async for msg in agent.chat(message, session_id=session_id):
                    if isinstance(msg, AssistantMessage):
                        for block in msg.content:
                            if isinstance(block, TextBlock):
                                progress.update(task, description="Responding...")
                                full_response += block.text
                                # Check for YAML in response
                                yaml_content = self._extract_yaml(block.text)
                                if yaml_content:
                                    self.last_yaml_content = yaml_content
                            elif isinstance(block, ToolUseBlock):
                                if self._is_subagent_call(block):
                                    subagent, description = self._get_subagent_info(block)
                                    tool_calls.append(f"subagent:{subagent}")
                                    progress.update(task, description=f"Subagent: {subagent}")
                                else:
                                    tool_name = self._clean_tool_name(block.name)
                                    tool_calls.append(tool_name)
                                    progress.update(task, description=f"Using {tool_name}...")
                                self._print_tool_call(block)

                    elif isinstance(msg, ResultMessage):
                        progress.update(task, description="Complete", completed=True)
                        self._print_result(msg)

            # Print the full response at the end
            if full_response.strip():
                self.console.print()
                self.console.print(Markdown(full_response))
        else:
            # Clean mode: stream text and show tool progress
            status_text = Text()
            status_text.append("⠋ ", style="bold blue")
            status_text.append("Thinking...")

            live = Live(status_text, console=self.console, refresh_per_second=4)
            live.start()

            try:
                async for msg in agent.chat(message, session_id=session_id):
                    if isinstance(msg, AssistantMessage):
                        for block in msg.content:
                            if isinstance(block, TextBlock):
                                # Stop live to print text immediately
                                live.stop()

                                # Print the text as it arrives
                                self.console.print(block.text)
                                full_response += block.text

                                # Check for YAML in response
                                yaml_content = self._extract_yaml(block.text)
                                if yaml_content:
                                    self.last_yaml_content = yaml_content

                                # Restart live on new line (so it doesn't overwrite text)
                                live.start()

                            elif isinstance(block, ToolUseBlock):
                                # Update status to show current tool or subagent
                                status_text = Text()
                                status_text.append("⠋ ", style="bold blue")
                                if self._is_subagent_call(block):
                                    subagent, description = self._get_subagent_info(block)
                                    tool_calls.append(f"subagent:{subagent}")
                                    status_text.append(f"Subagent: {subagent}", style="bold cyan")
                                else:
                                    tool_name = self._clean_tool_name(block.name)
                                    tool_calls.append(tool_name)
                                    status_text.append(f"→ {tool_name}")
                                live.update(status_text)

                    elif isinstance(msg, ResultMessage):
                        pass  # Don't print cost in clean mode
            finally:
                live.stop()

            # Show summary of tool calls if any were made
            if tool_calls:
                self.console.print(f"[dim]Tools used: {', '.join(tool_calls)}[/dim]")

        return self.last_yaml_content

    def _clean_tool_name(self, tool_name: str) -> str:
        """Clean up tool name for display."""
        # Remove MCP prefixes
        for prefix in ["mcp__databricks-mcp__", "mcp__databricks__"]:
            if tool_name.startswith(prefix):
                return tool_name.replace(prefix, "")
        return tool_name

    def _is_subagent_call(self, block: ToolUseBlock) -> bool:
        """Check if this tool call is a subagent invocation."""
        return block.name == "Task"

    def _get_subagent_info(self, block: ToolUseBlock) -> tuple[str, str]:
        """Extract subagent type and description from Task tool call.

        Returns:
            (subagent_type, description)
        """
        if hasattr(block, "input") and block.input:
            subagent = block.input.get("subagent_type", "unknown")
            description = block.input.get("description", "")
            return (subagent, description)
        return ("unknown", "")

    def _extract_yaml(self, text: str) -> Optional[str]:
        """
        Extract databricks.yml content from text.

        Looks for YAML code blocks or inline bundle configuration.
        """
        # Look for fenced code blocks with yaml
        yaml_pattern = r"```(?:yaml|yml)?\s*\n(.*?)```"
        matches = re.findall(yaml_pattern, text, re.DOTALL)

        for match in matches:
            # Check if it looks like a bundle config
            if "bundle:" in match or "resources:" in match:
                return match.strip()

        return None

    def _print_tool_call(self, block: ToolUseBlock):
        """Print tool call in verbose mode."""
        if self._is_subagent_call(block):
            subagent, description = self._get_subagent_info(block)
            self.console.print(f"  [bold cyan]Subagent: {subagent}[/bold cyan]")
            if description:
                self.console.print(f"    [dim]Task: {description}[/dim]")
        else:
            tool_name = self._clean_tool_name(block.name)
            self.console.print(f"  [dim]→ {tool_name}[/dim]")

            if hasattr(block, "input") and block.input:
                # Show abbreviated input
                input_str = str(block.input)
                if len(input_str) > 80:
                    input_str = input_str[:80] + "..."
                self.console.print(f"    [dim]{input_str}[/dim]")

    def _print_result(self, msg: ResultMessage):
        """Print result message in verbose mode."""
        if hasattr(msg, "total_cost_usd") and msg.total_cost_usd:
            self.console.print(f"  [dim]Cost: ${msg.total_cost_usd:.4f}[/dim]")

    def print_yaml(self, yaml_content: str, title: str = "databricks.yml"):
        """Print YAML content with syntax highlighting."""
        syntax = Syntax(yaml_content, "yaml", theme="monokai", line_numbers=True)
        self.console.print(Panel(syntax, title=title, border_style="green"))

    def print_error(self, message: str):
        """Print error message."""
        self.console.print(f"[red]Error:[/red] {message}")

    def print_success(self, message: str):
        """Print success message."""
        self.console.print(f"[green]✓[/green] {message}")

    def print_warning(self, message: str):
        """Print warning message."""
        self.console.print(f"[yellow]⚠[/yellow] {message}")

    def print_info(self, message: str):
        """Print info message."""
        self.console.print(f"[blue]ℹ[/blue] {message}")


def create_welcome_panel() -> Panel:
    """Create welcome panel for chat mode."""
    content = Text()
    content.append("DABs Copilot", style="bold blue")
    content.append(" - Conversational AI for Databricks Asset Bundles\n\n")
    content.append("Commands:\n", style="bold")
    content.append("  /quit, /exit  - Exit the session\n")
    content.append("  /reset        - Start new conversation\n")
    content.append("  /tools        - List available tools\n")
    content.append("  /help         - Show this help\n")
    content.append("  /save PATH    - Save last generated YAML\n")

    return Panel(content, title="Welcome", border_style="blue")


def format_validation_result(result: dict, verbose: bool = False) -> str:
    """Format bundle validation result for display."""
    if result.get("validation_passed"):
        return "[green]✓ Bundle validation passed[/green]"
    else:
        output = "[red]✗ Bundle validation failed[/red]\n"
        if result.get("stderr"):
            output += f"\n{result['stderr']}"
        elif result.get("stdout"):
            output += f"\n{result['stdout']}"
        return output
