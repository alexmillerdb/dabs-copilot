import os
from pathlib import Path
from typing import List
from claude_code_sdk import ClaudeCodeOptions, ClaudeSDKClient
from dotenv import load_dotenv

# Ensure environment variables are loaded
project_root = Path(__file__).parent.parent.parent
dotenv_path = project_root / ".env"
load_dotenv(dotenv_path)

def build_chat_options() -> ClaudeCodeOptions:
    """Build Claude options for chat-based DAB generation"""
    project_root = Path(__file__).parent.parent.parent
    mcp_server_path = project_root / "mcp" / "server" / "main.py"

    # Debug: Print paths to verify
    print(f"🐞 Project root: {project_root}")
    print(f"🐞 MCP server path: {mcp_server_path}")
    print(f"🐞 MCP server exists: {mcp_server_path.exists()}")
    print(f"🐞 Current working directory: {Path.cwd()}")
    
    # Pre-approve Databricks MCP tools so the agent can use them without extra prompting
    allowed_tools: List[str] = [
        # Core/health
        "mcp__databricks-mcp__health",

        # Jobs and workspace basics (mcp/server/tools.py)
        "mcp__databricks-mcp__list_jobs",
        "mcp__databricks-mcp__get_job",
        "mcp__databricks-mcp__run_job",
        "mcp__databricks-mcp__list_notebooks",
        "mcp__databricks-mcp__export_notebook",
        "mcp__databricks-mcp__execute_dbsql",
        "mcp__databricks-mcp__list_warehouses",
        "mcp__databricks-mcp__list_dbfs_files",
        "mcp__databricks-mcp__generate_bundle_from_job",
        "mcp__databricks-mcp__get_cluster",

        # DAB generation/validation (mcp/server/tools_dab.py)
        "mcp__databricks-mcp__analyze_notebook",
        "mcp__databricks-mcp__generate_bundle",
        "mcp__databricks-mcp__validate_bundle",
        "mcp__databricks-mcp__create_tests",

        # Workspace bundle ops (mcp/server/tools_workspace.py)
        "mcp__databricks-mcp__upload_bundle",
        "mcp__databricks-mcp__run_bundle_command",
        "mcp__databricks-mcp__sync_workspace_to_local",
    ]
    
    # Environment configuration for MCP server
    mcp_env = {
        "DATABRICKS_CONFIG_PROFILE": os.getenv("DATABRICKS_CONFIG_PROFILE", "DEFAULT"),
        "DATABRICKS_HOST": os.getenv("DATABRICKS_HOST", ""),
    }
    
    return ClaudeCodeOptions(
        model="claude-sonnet-4-20250514",
        cwd=str(project_root),  # Set to project root for MCP server
        mcp_servers={
            "databricks-mcp": {
                "command": "python",
                "args": [str(mcp_server_path)],
                "env": mcp_env,
                "cwd": str(project_root),  # Ensure MCP server runs from project root
            }
        },
        allowed_tools=allowed_tools,
        max_turns=10,  # Reduced to prevent loops
        system_prompt=(
            "You are a Databricks Asset Bundle (DAB) generation expert. "
            "ALWAYS use MCP Databricks tools (mcp__databricks-mcp__*) for Databricks operations - "
            "NEVER use bash, grep, or filesystem tools for Databricks workspace access. "
            "If you need more information, ask the user for the information you need."
            "Read CLAUDE.md for context and best practices. Be conversational and show progress."
        ),
    )

async def create_chat_client() -> ClaudeSDKClient:
    """Create a new Claude SDK client for chat conversations"""
    options = build_chat_options()
    return ClaudeSDKClient(options=options)