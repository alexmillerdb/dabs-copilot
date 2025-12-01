"""Generate command - One-shot bundle generation.

Generate a Databricks Asset Bundle from a job ID or workspace path.
"""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from ..auth import AuthenticationError, resolve_llm_config
from ..output import StreamingOutputHandler
from ..utils import (
    async_command,
    confirm_destructive_action,
    detect_source_type,
    generate_bundle_name,
    write_bundle_with_confirmation,
)

# Import agent - handle both package and standalone imports
try:
    from ...agent import DABsAgent
except ImportError:
    from dabs_copilot.agent import DABsAgent


@async_command
async def generate(
    ctx: typer.Context,
    source: str = typer.Argument(
        ...,
        help="Job ID (e.g., '12345') or workspace path (e.g., '/Workspace/Users/...')",
    ),
    output: Path = typer.Option(
        Path("."),
        "--output",
        "-o",
        help="Output directory for the bundle",
    ),
    name: Optional[str] = typer.Option(
        None,
        "--name",
        "-n",
        help="Bundle name (auto-generated if not provided)",
    ),
    target: str = typer.Option(
        "dev",
        "--target",
        "-t",
        help="Target environment for the bundle",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompts",
    ),
):
    """
    Generate a Databricks Asset Bundle from a job or workspace path.

    This command analyzes the source (job or notebooks) and generates
    a complete databricks.yml configuration.

    [bold]Examples:[/bold]

        # Generate from a job ID
        dabs-copilot generate 12345 --name my-etl-bundle

        # Generate from workspace notebooks
        dabs-copilot generate "/Workspace/Users/me/notebooks" -n my-pipeline

        # Generate with custom output directory
        dabs-copilot generate 12345 -o ./bundles/my-bundle -y

    [bold]Source Types:[/bold]

        - Job ID: Numeric ID of an existing Databricks job
        - Workspace path: Path starting with /Workspace or /Repos
        - Local path: Local directory containing notebooks/code
    """
    console: Console = ctx.obj.get("console", Console())
    verbose: bool = ctx.obj.get("verbose", False)
    profile: Optional[str] = ctx.obj.get("profile")

    # Validate LLM auth first
    try:
        resolve_llm_config()
    except AuthenticationError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    # Detect source type
    source_type = detect_source_type(source)
    console.print(f"[dim]Source type: {source_type}[/dim]")

    # Generate bundle name if not provided
    bundle_name = name or generate_bundle_name(source, source_type)
    console.print(f"[dim]Bundle name: {bundle_name}[/dim]")

    # Resolve output path
    output_path = output.resolve()
    if output_path.name != bundle_name and not output_path.exists():
        # Create bundle directory with bundle name
        output_path = output_path / bundle_name
    console.print(f"[dim]Output: {output_path}[/dim]")
    console.print()

    # Build the prompt based on source type
    if source_type == "job":
        prompt = (
            f"Generate a Databricks Asset Bundle from job ID {source}. "
            f"Name the bundle '{bundle_name}' and configure it for the '{target}' target. "
            f"Analyze the job configuration to understand the tasks, clusters, and dependencies. "
            f"Generate a complete databricks.yml with appropriate settings."
        )
    elif source_type == "workspace":
        prompt = (
            f"Generate a Databricks Asset Bundle from the workspace path '{source}'. "
            f"Name the bundle '{bundle_name}' and configure it for the '{target}' target. "
            f"List and analyze the notebooks in this path to understand the workflow. "
            f"Generate a complete databricks.yml with appropriate job and task configurations."
        )
    else:  # local
        prompt = (
            f"Generate a Databricks Asset Bundle for the local path '{source}'. "
            f"Name the bundle '{bundle_name}' and configure it for the '{target}' target. "
            f"Generate a complete databricks.yml based on the files in this directory."
        )

    # Add profile context if provided
    if profile:
        prompt += f" Use the Databricks profile '{profile}' for workspace configuration."

    # Initialize output handler
    output_handler = StreamingOutputHandler(console=console, verbose=verbose)

    # Run the agent
    agent = None
    try:
        agent = DABsAgent(
            tool_mode="custom",
            confirm_destructive=confirm_destructive_action if not yes else None,
        )
        await agent.__aenter__()

        console.print("[bold]Generating bundle...[/bold]")
        console.print()

        # Add instruction for agent to write bundle to output path
        prompt += f" Write the generated databricks.yml to '{output_path}'."

        yaml_content = await output_handler.stream_response(agent, prompt)

        # Check if bundle was written directly by agent (via Write tool)
        bundle_file = output_path / "databricks.yml"
        bundle_written_by_agent = bundle_file.exists()

        if bundle_written_by_agent:
            # Bundle was written directly by agent - success!
            console.print()
            console.print(f"[green]✓ Written:[/green] {bundle_file}")
            console.print()
            console.print("[bold green]Bundle generated successfully![/bold green]")
            console.print()
            console.print("[bold]Next steps:[/bold]")
            console.print(f"  1. Review: [cyan]{bundle_file}[/cyan]")
            console.print(f"  2. Validate: [cyan]dabs-copilot validate {output_path}[/cyan]")
            console.print(f"  3. Deploy: [cyan]dabs-copilot deploy {output_path} -t {target}[/cyan]")
        elif yaml_content:
            # YAML extracted from response - write it
            console.print()
            written = write_bundle_with_confirmation(
                yaml_content,
                output_path,
                force=yes,
                console=console,
            )
            if written:
                console.print()
                console.print("[bold green]Bundle generated successfully![/bold green]")
                console.print()
                console.print("[bold]Next steps:[/bold]")
                console.print(f"  1. Review: [cyan]{output_path / 'databricks.yml'}[/cyan]")
                console.print(f"  2. Validate: [cyan]dabs-copilot validate {output_path}[/cyan]")
                console.print(f"  3. Deploy: [cyan]dabs-copilot deploy {output_path} -t {target}[/cyan]")
        else:
            # Neither file exists nor YAML extracted
            console.print("[yellow]No bundle YAML was generated.[/yellow]")
            console.print("[dim]Try running 'dabs-copilot chat' for interactive generation.[/dim]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    finally:
        if agent:
            await agent.__aexit__(None, None, None)
