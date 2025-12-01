"""Validate command - Validate a Databricks Asset Bundle.

Runs 'databricks bundle validate' on the specified bundle.
"""

import json
import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from ..output import format_validation_result
from ..utils import find_bundle_path


def validate(
    ctx: typer.Context,
    bundle_path: Path = typer.Argument(
        Path("."),
        help="Path to bundle directory or databricks.yml",
    ),
    target: str = typer.Option(
        "dev",
        "--target",
        "-t",
        help="Target environment to validate",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output results as JSON",
    ),
):
    """
    Validate a Databricks Asset Bundle configuration.

    Runs the Databricks CLI 'bundle validate' command to check
    the bundle configuration for errors.

    [bold]Examples:[/bold]

        # Validate bundle in current directory
        dabs-copilot validate

        # Validate specific bundle
        dabs-copilot validate ./bundles/my-bundle/

        # Validate for production target
        dabs-copilot validate -t prod

        # Get JSON output
        dabs-copilot validate --json
    """
    console: Console = ctx.obj.get("console", Console())
    verbose: bool = ctx.obj.get("verbose", False)
    profile: Optional[str] = ctx.obj.get("profile")

    # Find databricks.yml
    bundle_file = find_bundle_path(bundle_path.resolve())
    if bundle_file is None:
        console.print(f"[red]Error:[/red] No databricks.yml found in {bundle_path}")
        console.print("[dim]Tip: Run 'dabs-copilot generate' to create a bundle first[/dim]")
        raise typer.Exit(1)

    bundle_dir = bundle_file.parent
    console.print(f"[dim]Validating: {bundle_file}[/dim]")
    console.print(f"[dim]Target: {target}[/dim]")

    # Build the command
    cmd = ["databricks", "bundle", "validate", "-t", target]
    if profile:
        cmd.extend(["--profile", profile])

    if verbose:
        console.print(f"[dim]Command: {' '.join(cmd)}[/dim]")

    # Run validation
    try:
        result = subprocess.run(
            cmd,
            cwd=bundle_dir,
            capture_output=True,
            text=True,
            timeout=120,
        )

        validation_result = {
            "validation_passed": result.returncode == 0,
            "bundle_path": str(bundle_file),
            "target_environment": target,
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr if result.returncode != 0 else None,
        }

        if json_output:
            console.print(json.dumps(validation_result, indent=2))
        else:
            console.print()
            if validation_result["validation_passed"]:
                console.print("[bold green]✓ Bundle validation passed[/bold green]")
                if verbose and result.stdout:
                    console.print()
                    console.print(result.stdout)
            else:
                console.print("[bold red]✗ Bundle validation failed[/bold red]")
                console.print()
                if result.stderr:
                    console.print(result.stderr)
                elif result.stdout:
                    console.print(result.stdout)
                raise typer.Exit(1)

    except subprocess.TimeoutExpired:
        console.print("[red]Error:[/red] Validation timed out after 120 seconds")
        raise typer.Exit(1)

    except FileNotFoundError:
        console.print("[red]Error:[/red] Databricks CLI not found")
        console.print()
        console.print("[bold]Install Databricks CLI:[/bold]")
        console.print(
            "  curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh"
        )
        raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
