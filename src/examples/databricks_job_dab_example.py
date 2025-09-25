"""Databricks Job → DAB example using Claude Code SDK with local MCP server.

This example demonstrates how to:
- Fetch a Databricks job by ID
- Analyze referenced notebooks/files
- Generate a Databricks Asset Bundle (DAB)
- Write `databricks.yml` locally
- Validate the bundle with the Databricks CLI

Requirements:
- Databricks CLI configured or environment variables set for your workspace
- Local MCP server available at `mcp/server/main.py`

Run:
  python src/examples/databricks_job_dab_example.py

Environment (optional):
- DATABRICKS_CONFIG_PROFILE
- DATABRICKS_HOST
"""

import asyncio
import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

from claude_code_sdk import (
    AssistantMessage,
    ClaudeCodeOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
)

load_dotenv()
JOB_ID = 662067900958232
DEFAULT_OUTPUT_DIR = f"./job-{JOB_ID}-bundle"


def build_options() -> ClaudeCodeOptions:
    """Configure Claude Code to use the local Databricks MCP server and necessary tools."""
    # Get the absolute path to the MCP server
    project_root = Path(__file__).parent.parent.parent  # Navigate from src/examples/ to project root
    mcp_server_path = project_root / "mcp" / "server" / "main.py"
    
    # Allow MCP tools needed for this workflow and local file writes
    allowed_tools: List[str] = [
        # Built-in file tool to save the generated databricks.yml
        "Write",

        # Databricks MCP tools
        "mcp__databricks-mcp__health",
        "mcp__databricks-mcp__get_job",
        "mcp__databricks-mcp__export_notebook",
        "mcp__databricks-mcp__analyze_notebook",
        "mcp__databricks-mcp__generate_bundle",
        "mcp__databricks-mcp__validate_bundle",
        # Optional convenience command
        "mcp__databricks-mcp__generate_bundle_from_job",
    ]

    # Pass-through env for the MCP server if present
    mcp_env = {
        "DATABRICKS_CONFIG_PROFILE": os.getenv("DATABRICKS_CONFIG_PROFILE", "DEFAULT"),
        "DATABRICKS_HOST": os.getenv("DATABRICKS_HOST", ""),
    }

    return ClaudeCodeOptions(
        mcp_servers={
            "databricks-mcp": {
                "command": "python",
                "args": [str(mcp_server_path)],  # Use absolute path
                "env": mcp_env,
            }
        },
        allowed_tools=allowed_tools,
        # Give the agent enough turns to finish tool orchestration
        max_turns=12,
        system_prompt=(
            "You are a precise automation assistant. Use tools exactly as requested, "
            "return concise progress updates, and avoid speculation."
        ),
    )


def display_message(msg) -> None:
    """Pretty-print streaming messages with tool visibility."""
    if isinstance(msg, AssistantMessage):
        for block in msg.content:
            if isinstance(block, TextBlock):
                print(f"Claude: {block.text}")
            elif isinstance(block, ToolUseBlock):
                print(f"→ Using tool: {block.name} (id={block.id})")
                if block.input:
                    print(f"  input: {block.input}")
    elif isinstance(msg, ResultMessage):
        print("Result ended")


async def run_job_to_dab(job_id: int, output_dir: str) -> None:
    """Orchestrate get_job → analyze_notebook → generate_bundle → write → validate_bundle."""
    options = build_options()

    plan = f"""
Perform the following steps for job {job_id} and keep outputs concise:

1) Call get_job(job_id={job_id}). Extract notebook paths from tasks where type == "notebook".
   - If there are none, extract python file paths for spark_python tasks.

2) For each collected path, call analyze_notebook(notebook_path=PATH).
   - Pass workspace paths directly; the tool handles exporting as needed.

3) Call generate_bundle(
      bundle_name="job-{job_id}",
      file_paths=[ALL_COLLECTED_PATHS],
      output_path="{output_dir}"
   ).
   - Then create a file at "{output_dir}/databricks.yml" with your generated YAML content using the Write tool.

4) Finally, call validate_bundle(bundle_path="{output_dir}", target="dev").

At the end, print a short summary with:
- bundle_path
- number of files analyzed
- validate result (pass/fail) and return_code.
""".strip()

    async with ClaudeSDKClient(options=options) as client:
        await client.query(plan)

        analyzed_count = 0
        validation_summary = None

        async for message in client.receive_messages():
            # Display conversational text and tool invocations
            display_message(message)

            # Inspect tool results for quick summary stats
            if isinstance(message, AssistantMessage):
                continue

            # Tool results come back attached to UserMessage blocks as ToolResultBlock
            if hasattr(message, "content"):
                for block in message.content:
                    if isinstance(block, ToolResultBlock):
                        name = getattr(block, "name", "") or ""
                        if name.endswith("analyze_notebook"):
                            analyzed_count += 1
                        if name.endswith("validate_bundle") and block.content:
                            validation_summary = block.content[:400]

            if isinstance(message, ResultMessage):
                print("\n— Orchestration finished —")
                print(f"Analyzed files (observed): {analyzed_count}")
                if validation_summary:
                    print("Validation summary (truncated):")
                    print(validation_summary)
                break


async def main():
    output_dir = os.getenv("DAB_OUTPUT_DIR", DEFAULT_OUTPUT_DIR)
    print(f"Preparing DAB for job {JOB_ID} → output: {output_dir}")
    await run_job_to_dab(JOB_ID, output_dir)


if __name__ == "__main__":
    asyncio.run(main())


