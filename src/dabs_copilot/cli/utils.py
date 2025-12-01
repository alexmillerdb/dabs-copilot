"""Utility functions for DABs Copilot CLI.

Provides file operations, confirmation prompts, and async helpers.
"""

import asyncio
import re
from functools import wraps
from pathlib import Path
from typing import Callable, Optional, TypeVar

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.syntax import Syntax

# Type variable for async command decorator
F = TypeVar("F", bound=Callable)


def async_command(f: F) -> F:
    """
    Decorator to run async functions in Typer commands.

    Typer doesn't natively support async commands, so this wrapper
    uses asyncio.run() to execute async functions.

    Usage:
        @app.command()
        @async_command
        async def my_command(...):
            ...
    """

    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapper  # type: ignore


def write_bundle_with_confirmation(
    yaml_content: str,
    output_path: Path,
    force: bool = False,
    console: Optional[Console] = None,
) -> bool:
    """
    Write databricks.yml with user confirmation.

    Shows a preview of the YAML content and asks for confirmation
    before writing to disk.

    Args:
        yaml_content: The YAML content to write
        output_path: Directory to write databricks.yml to
        force: If True, skip confirmation prompts
        console: Rich console for output

    Returns:
        True if file was written, False if cancelled
    """
    console = console or Console()
    output_file = output_path / "databricks.yml"

    # Show preview with syntax highlighting
    syntax = Syntax(yaml_content, "yaml", theme="monokai", line_numbers=True)
    console.print(Panel(syntax, title="databricks.yml", border_style="green"))
    console.print()

    # Check if file exists
    if output_file.exists() and not force:
        if not Confirm.ask(f"[yellow]File exists:[/yellow] {output_file}\nOverwrite?"):
            console.print("[dim]Cancelled.[/dim]")
            return False

    # Confirm write
    if not force:
        if not Confirm.ask("Write this file?"):
            console.print("[dim]Cancelled.[/dim]")
            return False

    # Create directory if needed and write file
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(yaml_content)
    console.print(f"[green]✓ Written:[/green] {output_file}")
    return True


def detect_source_type(source: str) -> str:
    """
    Detect whether source is a job ID or workspace path.

    Args:
        source: User-provided source string

    Returns:
        "job" if source is a job ID, "workspace" if it's a path
    """
    # Job IDs are numeric
    if source.isdigit():
        return "job"

    # Workspace paths start with /Workspace or /Repos
    if source.startswith("/Workspace") or source.startswith("/Repos"):
        return "workspace"

    # Local paths
    if source.startswith("/") or source.startswith("./") or source.startswith(".."):
        return "local"

    # Default to trying as job ID if it looks numeric-ish
    try:
        int(source)
        return "job"
    except ValueError:
        pass

    # Otherwise assume workspace path
    return "workspace"


def generate_bundle_name(source: str, source_type: str) -> str:
    """
    Generate a bundle name from the source.

    Args:
        source: The source path or job ID
        source_type: "job", "workspace", or "local"

    Returns:
        A kebab-case bundle name
    """
    if source_type == "job":
        return f"job-{source}-bundle"

    # Extract last component of path
    path = Path(source)
    name = path.stem or path.name or "bundle"

    # Convert to kebab-case
    name = re.sub(r"[_\s]+", "-", name.lower())
    name = re.sub(r"[^a-z0-9-]", "", name)
    name = re.sub(r"-+", "-", name).strip("-")

    return name or "bundle"


def find_bundle_path(path: Path) -> Optional[Path]:
    """
    Find databricks.yml in the given path.

    Searches:
    1. Exact path if it's a file
    2. databricks.yml in the directory
    3. Parent directories up to 3 levels

    Args:
        path: Path to search from

    Returns:
        Path to databricks.yml if found, None otherwise
    """
    path = path.resolve()

    # If path is a file, check if it's databricks.yml
    if path.is_file():
        if path.name == "databricks.yml":
            return path
        # Check in same directory
        bundle_path = path.parent / "databricks.yml"
        if bundle_path.exists():
            return bundle_path

    # If path is a directory, check for databricks.yml
    if path.is_dir():
        bundle_path = path / "databricks.yml"
        if bundle_path.exists():
            return bundle_path

    # Search parent directories (up to 3 levels)
    current = path if path.is_dir() else path.parent
    for _ in range(3):
        bundle_path = current / "databricks.yml"
        if bundle_path.exists():
            return bundle_path
        current = current.parent

    return None


def validate_bundle_path(path: Path, console: Optional[Console] = None) -> Optional[Path]:
    """
    Validate that a bundle path exists and contains databricks.yml.

    Args:
        path: Path to validate
        console: Rich console for output

    Returns:
        Path to databricks.yml if valid, None otherwise
    """
    console = console or Console()

    bundle_path = find_bundle_path(path)
    if bundle_path is None:
        console.print(f"[red]Error:[/red] No databricks.yml found in {path}")
        console.print("[dim]Tip: Run 'dabs-copilot generate' to create a bundle first[/dim]")
        return None

    return bundle_path


async def confirm_destructive_action(tool_name: str, tool_input: dict) -> bool:
    """
    Prompt user before destructive actions.

    This is used as a callback for DABsAgent.confirm_destructive.

    Args:
        tool_name: Name of the tool being called
        tool_input: Input parameters for the tool

    Returns:
        True if user confirms, False otherwise
    """
    console = Console()

    # Clean up tool name for display
    display_name = tool_name
    if display_name.startswith("mcp__databricks__"):
        display_name = display_name.replace("mcp__databricks__", "")

    console.print(f"\n[yellow]⚠ Destructive action:[/yellow] {display_name}")

    # Show relevant input details
    if tool_input:
        for key, value in tool_input.items():
            if key in ("job_id", "bundle_path", "command", "target", "workspace_path"):
                console.print(f"  {key}: {value}")

    return Confirm.ask("Proceed?", default=False)


def format_job_id(source: str) -> Optional[int]:
    """
    Parse and validate a job ID.

    Args:
        source: String that should be a job ID

    Returns:
        Job ID as integer, or None if invalid
    """
    try:
        return int(source)
    except ValueError:
        return None


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text with ellipsis if too long."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."
