"""DABs Copilot CLI - Main entry point.

Conversational AI for Databricks Asset Bundles.

Usage:
    dabs-copilot --help
    dabs-copilot generate 12345 --name my-bundle
    dabs-copilot validate ./bundles/my-bundle/
    dabs-copilot deploy ./bundles/my-bundle/ -t dev
    dabs-copilot chat
"""

from typing import Optional

import typer
from dotenv import load_dotenv
from rich.console import Console

# Load .env file at CLI startup
load_dotenv()

from . import __version__
from .auth import AuthenticationError, resolve_llm_config, validate_databricks_auth
from .commands.chat import chat as chat_command
from .commands.deploy import deploy as deploy_command
from .commands.generate import generate as generate_command
from .commands.validate import validate as validate_command

# Create the main Typer app
app = typer.Typer(
    name="dabs-copilot",
    help="Conversational AI for Databricks Asset Bundles",
    rich_markup_mode="rich",
    no_args_is_help=True,
    add_completion=True,
)

# Shared console for all commands
console = Console()


def version_callback(value: bool):
    """Print version and exit."""
    if value:
        console.print(f"dabs-copilot version {__version__}")
        raise typer.Exit()


def check_auth_callback(value: bool):
    """Verify authentication and exit."""
    if value:
        console.print("[bold]Checking authentication...[/bold]\n")

        # Check Databricks auth
        db_success, db_msg = validate_databricks_auth()
        if db_success:
            console.print(f"[green]✓ Databricks:[/green] {db_msg}")
        else:
            console.print(f"[red]✗ Databricks:[/red] {db_msg}")

        # Check LLM auth
        try:
            llm_config = resolve_llm_config()
            if llm_config["backend"] == "litellm":
                console.print(f"[green]✓ LLM:[/green] LiteLLM proxy at {llm_config['api_base']}")
            elif llm_config['backend'] == 'databricks_fmapi':
                console.print(f"[green]✓ LLM:[/green] Databricks FMAPI at {llm_config['api_base']} (model: {llm_config['model']})")
            else:
                console.print("[green]✓ LLM:[/green] Anthropic API key configured")
        except AuthenticationError as e:
            console.print(f"[red]✗ LLM:[/red] {e}")

        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    profile: Optional[str] = typer.Option(
        None,
        "--profile",
        "-p",
        help="Databricks CLI profile name",
        envvar="DATABRICKS_CONFIG_PROFILE",
    ),
    host: Optional[str] = typer.Option(
        None,
        "--host",
        help="Databricks workspace URL",
        envvar="DATABRICKS_HOST",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output (show tool calls)",
    ),
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
    check_auth: bool = typer.Option(
        False,
        "--check-auth",
        callback=check_auth_callback,
        is_eager=True,
        help="Verify authentication and exit",
    ),
):
    """
    DABs Copilot - Conversational AI for Databricks Asset Bundles.

    Generate, validate, and deploy Databricks Asset Bundles using natural language.

    [bold]Quick Start:[/bold]

        # Generate a bundle from a job
        dabs-copilot generate 12345 --name my-etl

        # Generate from workspace notebooks
        dabs-copilot generate "/Workspace/Users/me/notebooks" -n my-pipeline

        # Interactive mode
        dabs-copilot chat

    [bold]Authentication:[/bold]

        Set DATABRICKS_CONFIG_PROFILE or use --profile flag for Databricks.
        Set ANTHROPIC_API_KEY for Claude, or LITELLM_API_BASE for LiteLLM proxy.
    """
    # Store global options in context for use by subcommands
    ctx.ensure_object(dict)
    ctx.obj["profile"] = profile
    ctx.obj["host"] = host
    ctx.obj["verbose"] = verbose
    ctx.obj["console"] = console


# Register commands
app.command(name="generate", help="Generate a bundle from job ID or workspace path")(
    generate_command
)
app.command(name="validate", help="Validate a Databricks Asset Bundle")(validate_command)
app.command(name="deploy", help="Deploy a bundle to target environment")(deploy_command)
app.command(name="chat", help="Interactive chat for bundle generation")(chat_command)


# Convenience entry point for running as module
def cli():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    cli()
