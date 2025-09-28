import os
import subprocess
from pathlib import Path
from typing import List, Optional
from claude_code_sdk import ClaudeCodeOptions, ClaudeSDKClient
from dotenv import load_dotenv

# Ensure environment variables are loaded
project_root = Path(__file__).parent.parent.parent
dotenv_path = project_root / ".env"
load_dotenv(dotenv_path)

def get_databricks_token(token: str = None) -> str:
    """Get OAuth token for MCP server authentication

    Args:
        token: Optional OAuth token from Databricks Apps. If not provided,
               falls back to profile-based authentication.
    """
    if token:
        print("🔐 Using provided OAuth token (Databricks Apps)")
        return token

    # Fall back to profile-based authentication for local development
    from databricks.sdk import WorkspaceClient
    profile = os.getenv("DATABRICKS_CONFIG_PROFILE", "DEFAULT")
    print(f"🔐 Using profile-based authentication: {profile}")
    workspace_client = WorkspaceClient(profile=profile)
    return workspace_client.config.token

def build_chat_options(oauth_token: str = None) -> ClaudeCodeOptions:
    """Build Claude options for chat-based DAB generation

    Args:
        oauth_token: Optional OAuth token from Databricks Apps
    """
    project_root = Path(__file__).parent.parent.parent

    mcp_server_url = os.getenv(
        "MCP_REMOTE_URL",
        "https://databricks-mcp-server-1444828305810485.aws.databricksapps.com",
    )

    print(f"🐞 Project root: {project_root}")
    print(f"🐞 MCP server URL: {mcp_server_url}")
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
    
    return ClaudeCodeOptions(
        model="claude-sonnet-4-20250514",
        cwd=str(project_root),
        mcp_servers={
            "databricks-mcp": {
                "command": "http_client",
                "url": f"{mcp_server_url}/mcp",
                "auth": {
                    "type": "bearer",
                    "token": get_databricks_token(oauth_token),
                },
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

def get_claude_cli_path() -> Optional[str]:
    """Get the path to Claude CLI binary

    Returns path in this order of precedence:
    1. From claude_cli_path.txt file (Databricks Apps)
    2. From CLAUDE_CLI_PATH environment variable
    3. Try to find it in common locations
    4. None if not found
    """
    current_dir = Path(__file__).parent

    # Check for path file (created by setup script in Apps)
    cli_path_file = current_dir / "claude_cli_path.txt"
    if cli_path_file.exists():
        cli_path = cli_path_file.read_text().strip()
        if Path(cli_path).exists():
            print(f"🔧 Using Claude CLI from path file: {cli_path}")
            return cli_path

    # Check environment variable
    env_path = os.getenv("CLAUDE_CLI_PATH")
    if env_path and Path(env_path).exists():
        print(f"🔧 Using Claude CLI from env: {env_path}")
        return env_path

    # Check local node_modules
    local_paths = [
        current_dir / "claude_cli" / "node_modules" / ".bin" / "claude",
        current_dir / "node_modules" / ".bin" / "claude",
        Path.home() / "node_modules" / ".bin" / "claude",
    ]

    for path in local_paths:
        if path.exists():
            print(f"🔧 Found Claude CLI at: {path}")
            return str(path)

    # Try to find it in PATH
    try:
        result = subprocess.run(["which", "claude"], capture_output=True, text=True)
        if result.returncode == 0:
            cli_path = result.stdout.strip()
            print(f"🔧 Found Claude CLI in PATH: {cli_path}")
            return cli_path
    except:
        pass

    print("⚠️ Claude CLI not found, will try default behavior")
    return None

async def create_chat_client(oauth_token: str = None) -> ClaudeSDKClient:
    """Create a new Claude SDK client for chat conversations

    Args:
        oauth_token: Optional OAuth token from Databricks Apps
    """
    options = build_chat_options(oauth_token)

    # Try to get explicit CLI path and set it in environment
    cli_path = get_claude_cli_path()

    if cli_path:
        # Set the PATH environment variable to include the CLI directory
        cli_dir = os.path.dirname(cli_path)
        current_path = os.environ.get('PATH', '')
        if cli_dir not in current_path:
            os.environ['PATH'] = f"{cli_dir}:{current_path}"
        print(f"🚀 Added CLI directory to PATH: {cli_dir}")

        # Also set explicit path for the SDK to use
        os.environ['CLAUDE_CLI_PATH'] = cli_path
        print(f"🚀 Set CLAUDE_CLI_PATH environment variable: {cli_path}")

    return ClaudeSDKClient(options=options)