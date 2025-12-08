"""Output handlers for DABs Copilot CLI.

Provides rich console output with streaming support, progress display,
and YAML extraction from agent responses.
"""

import json
import re
from typing import Optional

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.table import Table
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
        self.last_analysis_result: Optional[dict] = None

    def _format_complexity_score(self, score: float) -> Text:
        """Format complexity score with color coding.

        Green: < 0.3 (simple)
        Yellow: 0.3 - 0.5 (moderate)
        Orange: 0.5 - 0.7 (complex)
        Red: >= 0.7 (very complex)
        """
        text = Text()
        if score < 0.3:
            text.append(f"{score:.2f}", style="bold green")
            text.append(" (simple)", style="dim green")
        elif score < 0.5:
            text.append(f"{score:.2f}", style="bold yellow")
            text.append(" (moderate)", style="dim yellow")
        elif score < 0.7:
            text.append(f"{score:.2f}", style="bold dark_orange")
            text.append(" (complex)", style="dim dark_orange")
        else:
            text.append(f"{score:.2f}", style="bold red")
            text.append(" (very complex)", style="dim red")
        return text

    def _format_dependencies_table(self, dependencies: dict) -> Table:
        """Create a Rich table for categorized dependencies."""
        table = Table(show_header=True, header_style="bold cyan", box=None)
        table.add_column("Category", style="bold")
        table.add_column("Packages")

        category_styles = {
            "databricks": "blue",
            "third_party": "magenta",
            "standard_library": "dim",
            "local": "yellow",
        }

        for category, packages in dependencies.items():
            if packages:
                style = category_styles.get(category, "white")
                display_name = category.replace("_", " ").title()
                table.add_row(display_name, ", ".join(sorted(packages)), style=style)

        return table

    def _format_data_sources(self, data_sources: dict) -> Panel:
        """Format data sources as a panel."""
        content = Text()

        input_tables = data_sources.get("input_tables", [])
        output_tables = data_sources.get("output_tables", [])
        file_paths = data_sources.get("file_paths", [])

        if input_tables:
            content.append("Input Tables: ", style="bold green")
            content.append(", ".join(input_tables) + "\n")

        if output_tables:
            content.append("Output Tables: ", style="bold red")
            content.append(", ".join(output_tables) + "\n")

        if file_paths:
            content.append("File Paths: ", style="bold yellow")
            content.append(", ".join(file_paths))

        return Panel(content, title="Data Sources", border_style="cyan")

    def print_analysis_result(self, analysis: dict, show_full: bool = False):
        """Print formatted analysis result.

        Args:
            analysis: Analysis result dict from analyze_notebook
            show_full: If True, show all details including databricks_features
        """
        path = analysis.get("path", "Unknown")
        workflow_type = analysis.get("workflow_type", "unknown")
        confidence = analysis.get("detection_confidence", 0.0)
        cached = analysis.get("cached", False)

        # Header
        header = Text()
        header.append("Analysis: ", style="bold")
        header.append(path, style="cyan")
        if cached:
            header.append(" (cached)", style="dim")
        self.console.print(header)
        self.console.print()

        # Complexity score
        complexity_score = analysis.get("complexity_score", 0.0)
        score_text = Text()
        score_text.append("Complexity Score: ")
        score_text.append_text(self._format_complexity_score(complexity_score))
        self.console.print(score_text)

        # Complexity factors
        factors = analysis.get("complexity_factors", [])
        if factors:
            self.console.print(f"[dim]Factors: {', '.join(factors)}[/dim]")

        self.console.print()

        # Workflow type and confidence
        workflow_text = Text()
        workflow_text.append("Workflow: ", style="bold")
        workflow_text.append(workflow_type.upper(), style="bold magenta")
        workflow_text.append(f" (confidence: {confidence:.0%})", style="dim")
        self.console.print(workflow_text)
        self.console.print()

        # Dependencies table
        dependencies = analysis.get("dependencies", {})
        if any(dependencies.values()):
            self.console.print(self._format_dependencies_table(dependencies))
            self.console.print()

        # Data sources panel
        data_sources = analysis.get("data_sources", {})
        if any(data_sources.values()):
            self.console.print(self._format_data_sources(data_sources))
            self.console.print()

        # Databricks features (verbose/full mode only)
        if show_full:
            features = analysis.get("databricks_features", {})
            if any(features.values()):
                self._print_databricks_features(features)

    def _print_databricks_features(self, features: dict):
        """Print Databricks-specific features."""
        content = Text()

        widgets = features.get("widgets", [])
        if widgets:
            content.append("Widgets: ", style="bold")
            widget_names = [w.get("name", "?") for w in widgets if isinstance(w, dict)]
            if widget_names:
                content.append(", ".join(widget_names) + "\n")

        notebook_calls = features.get("notebook_calls", [])
        if notebook_calls:
            content.append("Notebook Calls: ", style="bold")
            content.append(", ".join(notebook_calls) + "\n")

        cluster_configs = features.get("cluster_configs", [])
        if cluster_configs:
            content.append("Cluster Configs: ", style="bold")
            content.append(", ".join(cluster_configs))

        if str(content):
            self.console.print(
                Panel(content, title="Databricks Features", border_style="blue")
            )

    def _extract_analysis_result(self, text: str) -> Optional[dict]:
        """Extract analyze_notebook result from agent text response.

        Returns:
            Parsed analysis dict if found, None otherwise
        """
        # Look for JSON code blocks with analysis markers
        json_pattern = r"```(?:json)?\s*\n(\{[^`]+\})\s*```"
        matches = re.findall(json_pattern, text, re.DOTALL)

        for match in matches:
            try:
                data = json.loads(match)
                if "complexity_score" in data and "dependencies" in data:
                    return data
            except json.JSONDecodeError:
                continue

        return None

    async def stream_response(
        self,
        agent,
        message: str,
        session_id: str = "default",
        show_analysis: bool = True,
    ) -> Optional[str]:
        """
        Stream agent response and extract YAML content if present.

        Args:
            agent: DABsAgent instance
            message: User message to send
            session_id: Session ID for multi-turn conversations
            show_analysis: If True, display analysis results when detected

        Returns:
            Extracted YAML content if databricks.yml was generated, else None
        """
        self.last_yaml_content = None
        self.last_analysis_result = None
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

        # Extract and display analysis results if present
        if show_analysis and full_response:
            analysis = self._extract_analysis_result(full_response)
            if analysis:
                self.last_analysis_result = analysis
                self.console.print()
                self.print_analysis_result(analysis, show_full=self.verbose)

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
    content.append("  /analyze      - Show last analysis result\n")

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
