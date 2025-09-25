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
    
    # All MCP tools available for natural language DAB generation
    allowed_tools: List[str] = [
        # Built-in file tools
        "Write",
        "Read",
        "Edit",
        
        # Databricks MCP tools - Phase 1 (basic operations)
        "mcp__databricks-mcp__health",
        "mcp__databricks-mcp__list_jobs",
        "mcp__databricks-mcp__get_job",
        "mcp__databricks-mcp__run_job",
        "mcp__databricks-mcp__list_notebooks",
        "mcp__databricks-mcp__export_notebook",
        "mcp__databricks-mcp__execute_dbsql",
        "mcp__databricks-mcp__list_warehouses",
        "mcp__databricks-mcp__list_dbfs_files",
        
        # Databricks MCP tools - Phase 2 (DAB generation)
        "mcp__databricks-mcp__analyze_notebook",
        "mcp__databricks-mcp__generate_bundle",
        "mcp__databricks-mcp__generate_bundle_from_job",
        "mcp__databricks-mcp__validate_bundle",
        "mcp__databricks-mcp__create_tests",
        "mcp__databricks-mcp__get_cluster",
        
        # Databricks MCP tools - Phase 3 (deployment)
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
        cwd=str(Path(__file__).parent),  # Directory containing CLAUDE.md context
        mcp_servers={
            "databricks-mcp": {
                "command": "python",
                "args": [str(mcp_server_path)],
                "env": mcp_env,
            }
        },
        allowed_tools=allowed_tools,
        max_turns=20,  # Extended for conversational workflows
        system_prompt=(
            "You are a Databricks Asset Bundle (DAB) generation expert. "
            "Use natural language to understand user requests and generate high-quality "
            "bundles using the available MCP tools. Read CLAUDE.md for context and best practices. "
            "Be conversational, show progress, and provide download links for generated files."
        ),
    )

async def create_chat_client() -> ClaudeSDKClient:
    """Create a new Claude SDK client for chat conversations"""
    options = build_chat_options()
    return ClaudeSDKClient(options=options)