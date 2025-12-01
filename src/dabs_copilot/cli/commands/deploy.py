"""Deploy command - Deploy a Databricks Asset Bundle.

Runs 'databricks bundle deploy' to deploy the bundle to a workspace.
"""

import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.prompt import Confirm

from ..utils import find_bundle_path


def deploy(
    ctx: typer.Context,
    bundle_path: Path = typer.Argument(
        Path("."),
        help="Path to bundle directory or databricks.yml",
    ),
    target: str = typer.Option(
        "dev",
        "--target",
        "-t",
        help="Target environment to deploy to",
    ),
    run: bool = typer.Option(
        False,
        "--run",
        help="Run the job after successful deployment",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompts",
    ),
):
    """
    Deploy a Databricks Asset Bundle to the workspace.

    This command validates and deploys the bundle using the
    Databricks CLI 'bundle deploy' command.

    [bold]Examples:[/bold]

        # Deploy bundle in current directory
        dabs-copilot deploy

        # Deploy specific bundle to dev
        dabs-copilot deploy ./bundles/my-bundle/ -t dev

        # Deploy to production (with confirmation)
        dabs-copilot deploy -t prod

        # Deploy and run the job
        dabs-copilot deploy --run

        # Deploy without confirmation
        dabs-copilot deploy -y
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
    console.print(f"[dim]Bundle: {bundle_file}[/dim]")
    console.print(f"[dim]Target: {target}[/dim]")

    # Confirmation for production deployments
    if target in ("prod", "production") and not yes:
        console.print()
        console.print("[yellow]⚠ You are about to deploy to PRODUCTION[/yellow]")
        if not Confirm.ask("Are you sure you want to continue?", default=False):
            console.print("[dim]Deployment cancelled.[/dim]")
            raise typer.Exit(0)

    # General confirmation if not skipped
    if not yes and target not in ("prod", "production"):
        if not Confirm.ask(f"Deploy to {target}?", default=True):
            console.print("[dim]Deployment cancelled.[/dim]")
            raise typer.Exit(0)

    # Step 1: Validate first
    console.print()
    console.print("[bold]Step 1: Validating bundle...[/bold]")

    validate_cmd = ["databricks", "bundle", "validate", "-t", target]
    if profile:
        validate_cmd.extend(["--profile", profile])

    try:
        validate_result = subprocess.run(
            validate_cmd,
            cwd=bundle_dir,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if validate_result.returncode != 0:
            console.print("[red]✗ Validation failed[/red]")
            if validate_result.stderr:
                console.print(validate_result.stderr)
            elif validate_result.stdout:
                console.print(validate_result.stdout)
            raise typer.Exit(1)

        console.print("[green]✓ Validation passed[/green]")

    except subprocess.TimeoutExpired:
        console.print("[red]Error:[/red] Validation timed out")
        raise typer.Exit(1)

    except FileNotFoundError:
        console.print("[red]Error:[/red] Databricks CLI not found")
        console.print()
        console.print("[bold]Install Databricks CLI:[/bold]")
        console.print(
            "  curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh"
        )
        raise typer.Exit(1)

    # Step 2: Deploy
    console.print()
    console.print("[bold]Step 2: Deploying bundle...[/bold]")

    deploy_cmd = ["databricks", "bundle", "deploy", "-t", target]
    if profile:
        deploy_cmd.extend(["--profile", profile])

    if verbose:
        console.print(f"[dim]Command: {' '.join(deploy_cmd)}[/dim]")

    try:
        # Run deploy with live output
        deploy_result = subprocess.run(
            deploy_cmd,
            cwd=bundle_dir,
            capture_output=True,
            text=True,
            timeout=300,
        )

        if deploy_result.returncode != 0:
            console.print("[red]✗ Deployment failed[/red]")
            if deploy_result.stderr:
                console.print(deploy_result.stderr)
            elif deploy_result.stdout:
                console.print(deploy_result.stdout)
            raise typer.Exit(1)

        console.print("[green]✓ Deployment successful[/green]")

        if verbose and deploy_result.stdout:
            console.print()
            console.print(deploy_result.stdout)

    except subprocess.TimeoutExpired:
        console.print("[red]Error:[/red] Deployment timed out after 5 minutes")
        raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    # Step 3: Run (optional)
    if run:
        console.print()
        console.print("[bold]Step 3: Running job...[/bold]")

        run_cmd = ["databricks", "bundle", "run", "-t", target]
        if profile:
            run_cmd.extend(["--profile", profile])

        if verbose:
            console.print(f"[dim]Command: {' '.join(run_cmd)}[/dim]")

        try:
            run_result = subprocess.run(
                run_cmd,
                cwd=bundle_dir,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if run_result.returncode != 0:
                console.print("[yellow]⚠ Job run may have issues[/yellow]")
                if run_result.stderr:
                    console.print(run_result.stderr)
            else:
                console.print("[green]✓ Job run initiated[/green]")
                if run_result.stdout:
                    console.print()
                    console.print(run_result.stdout)

        except subprocess.TimeoutExpired:
            console.print("[yellow]⚠ Job run command timed out (job may still be running)[/yellow]")

        except Exception as e:
            console.print(f"[yellow]⚠ Could not run job:[/yellow] {e}")

    # Success summary
    console.print()
    console.print("[bold green]Deployment complete![/bold green]")
    console.print()
    console.print("[bold]Next steps:[/bold]")
    console.print(f"  • View in workspace: Check the Databricks UI for your deployed resources")
    console.print(f"  • Run manually: [cyan]databricks bundle run -t {target}[/cyan]")
    console.print(f"  • Destroy: [cyan]databricks bundle destroy -t {target}[/cyan]")
