"""
DABs Copilot Agent - Interactive orchestrator using Claude Agent SDK.

Features:
- Multi-turn conversations with session persistence
- Real-time streaming of responses and tool calls
- Confirmation prompts before destructive actions (deploy, delete)
- Specialized subagents for discovery, analysis, generation, validation, deployment
- Skills for DAB patterns and best practices
- Dual-mode tools: MCP server (external) or custom tools (in-process)
"""
import os
from pathlib import Path
from typing import AsyncIterator, Callable, Awaitable, Any
from dotenv import load_dotenv

import anthropic
import mlflow.anthropic

from claude_agent_sdk import (
    ClaudeSDKClient,
    query,
    ClaudeAgentOptions,
    AgentDefinition,
    PermissionResultAllow,
    PermissionResultDeny,
    ToolPermissionContext,
    ResultMessage,
)

# Import SDK tools for custom (in-process) mode
# Handle both package and standalone imports
try:
    from .tools.sdk_tools import (
        create_databricks_mcp_server,
        get_tool_names as get_sdk_tool_names,
        ALL_TOOLS as SDK_ALL_TOOLS,
        CORE_TOOLS as SDK_CORE_TOOLS,
        DAB_TOOLS as SDK_DAB_TOOLS,
        WORKSPACE_TOOLS as SDK_WORKSPACE_TOOLS,
        DESTRUCTIVE_TOOL_NAMES as SDK_DESTRUCTIVE_TOOL_NAMES,
    )
except ImportError:
    from tools.sdk_tools import (
        create_databricks_mcp_server,
        get_tool_names as get_sdk_tool_names,
        ALL_TOOLS as SDK_ALL_TOOLS,
        CORE_TOOLS as SDK_CORE_TOOLS,
        DAB_TOOLS as SDK_DAB_TOOLS,
        WORKSPACE_TOOLS as SDK_WORKSPACE_TOOLS,
        DESTRUCTIVE_TOOL_NAMES as SDK_DESTRUCTIVE_TOOL_NAMES,
    )

# Custom tools server name (for in-process mode)
# Must match MCP server name for consistent tool naming across modes
CUSTOM_TOOLS_SERVER = "databricks-mcp"

# MCP tools available when using external MCP server
MCP_TOOLS = [
    "mcp__databricks-mcp__health",
    "mcp__databricks-mcp__list_jobs",
    "mcp__databricks-mcp__get_job",
    "mcp__databricks-mcp__run_job",
    "mcp__databricks-mcp__list_notebooks",
    "mcp__databricks-mcp__export_notebook",
    "mcp__databricks-mcp__execute_dbsql",
    "mcp__databricks-mcp__list_warehouses",
    "mcp__databricks-mcp__list_dbfs_files",
    "mcp__databricks-mcp__get_cluster",
    "mcp__databricks-mcp__analyze_notebook",
    "mcp__databricks-mcp__generate_bundle",
    "mcp__databricks-mcp__generate_bundle_from_job",
    "mcp__databricks-mcp__validate_bundle",
    "mcp__databricks-mcp__upload_bundle",
    "mcp__databricks-mcp__run_bundle_command",
    "mcp__databricks-mcp__sync_workspace_to_local",
]

# Destructive tools for external MCP mode
MCP_DESTRUCTIVE_TOOLS = [
    "mcp__databricks-mcp__run_job",
    "mcp__databricks-mcp__upload_bundle",
    "mcp__databricks-mcp__run_bundle_command",
]

# Base tools available to the agent (orchestration + file tools)
BASE_TOOLS = [
    "Skill",  # For loading DAB skill
    "Task",   # For spawning subagents
    "Read", "Write", "Edit", "Glob", "Grep",
]

# All tools available in MCP mode
ALLOWED_TOOLS = BASE_TOOLS + MCP_TOOLS

load_dotenv()

os.environ['DATABRICKS_HOST'] = os.getenv("DATABRICKS_HOST")
os.environ['DATABRICKS_CONFIG_PROFILE'] = os.getenv("DATABRICKS_CONFIG_PROFILE")
mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "databricks"))
mlflow.set_experiment(experiment_id=os.getenv("MLFLOW_EXPERIMENT_ID", "567797472279756"))
mlflow.anthropic.autolog()


def get_custom_tool_names(category: str | None = None) -> list[str]:
    """Get tool names for custom tools mode.

    Args:
        category: Filter by category - "core", "dab", "workspace", or None for all

    Returns:
        List of MCP-formatted tool names (mcp__databricks__tool_name)
    """
    if category == "core":
        tools = SDK_CORE_TOOLS
    elif category == "dab":
        tools = SDK_DAB_TOOLS
    elif category == "workspace":
        tools = SDK_WORKSPACE_TOOLS
    else:
        tools = SDK_ALL_TOOLS
    return get_sdk_tool_names(tools, CUSTOM_TOOLS_SERVER)


def get_custom_tools_allowed(category: str | None = None) -> list[str]:
    """Get allowed tools list for custom tools mode."""
    return BASE_TOOLS + get_custom_tool_names(category)


def get_project_root() -> str:
    """Get project root directory for skill/agent loading.

    Searches upward from this file's location for a directory containing
    `.claude/` which indicates the project root.
    """
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / ".claude").is_dir():
            return str(current)
        current = current.parent
    # Fallback to cwd
    return os.getcwd()


# =============================================================================
# SUBAGENT DEFINITIONS (Simplified: 3 agents aligned with tool categories)
# =============================================================================

DABS_AGENTS = {
    "dab-analyst": AgentDefinition(
        description="Analyzes Databricks jobs and notebooks. EXECUTES get_job, list_notebooks, analyze_notebook tools.",
        prompt="""## CRITICAL: You MUST Execute Tools

You are an EXECUTING agent. Call MCP tools and return REAL data.
DO NOT provide guidance or frameworks. CALL THE TOOLS.

## Your Capabilities
- Discover jobs: get_job, list_jobs
- Discover notebooks: list_notebooks, export_notebook
- Analyze code: analyze_notebook
- Get cluster info: get_cluster

## Task Execution

**For job analysis:**
1. CALL mcp__databricks-mcp__get_job(job_id=<id>)
2. Extract notebook paths from the tasks array in the response
3. CALL mcp__databricks-mcp__analyze_notebook for each notebook path
4. Return compiled results with ACTUAL data from the tool calls

**For workspace analysis:**
1. CALL mcp__databricks-mcp__list_notebooks(path=<path>, recursive=true)
2. CALL mcp__databricks-mcp__analyze_notebook for each notebook found
3. Return compiled results

**For job search:**
1. CALL mcp__databricks-mcp__list_jobs(name_filter=<pattern>) if searching
2. Return the list of matching jobs

## Response Requirements

Your response MUST contain data from tool calls, not guesses or frameworks.
If you haven't called a tool, you haven't completed your task.
""",
        tools=[
            "mcp__databricks-mcp__get_job",
            "mcp__databricks-mcp__list_jobs",
            "mcp__databricks-mcp__list_notebooks",
            "mcp__databricks-mcp__export_notebook",
            "mcp__databricks-mcp__analyze_notebook",
            "mcp__databricks-mcp__get_cluster",
            "Read", "Grep", "Glob",
        ],
        model="inherit",
    ),

    "dab-builder": AgentDefinition(
        description="Generates and validates DAB bundles. EXECUTES generate_bundle, validate_bundle tools.",
        prompt="""## CRITICAL: You MUST Execute Tools

You are an EXECUTING agent. Generate bundle YAML and validate it.
DO NOT describe what a bundle would look like. CREATE IT.

## Your Capabilities
- Generate from job: generate_bundle_from_job
- Generate from files: generate_bundle
- Validate: validate_bundle
- Write files: Write, Edit

## Task Execution

**For job-based bundle:**
1. CALL mcp__databricks-mcp__generate_bundle_from_job(job_id=<id>)
2. Review the generated YAML in the response
3. CALL mcp__databricks-mcp__validate_bundle(bundle_path=<path>)
4. If validation fails, fix errors and re-validate
5. Return the final databricks.yml content

**For file-based bundle:**
1. CALL mcp__databricks-mcp__generate_bundle(bundle_name=<name>, file_paths=[...])
2. Use Write tool to save databricks.yml to the output path
3. CALL mcp__databricks-mcp__validate_bundle(bundle_path=<path>)
4. Return the bundle path and content

## Response Requirements

Your response MUST include actual generated YAML, not templates or placeholders.
If validation fails, include the errors and your fixes.
""",
        tools=[
            "mcp__databricks-mcp__generate_bundle",
            "mcp__databricks-mcp__generate_bundle_from_job",
            "mcp__databricks-mcp__validate_bundle",
            "Write", "Edit", "Read", "Skill",
        ],
        model="inherit",
    ),

    "dab-deployer": AgentDefinition(
        description="Deploys bundles to Databricks workspace. EXECUTES upload_bundle, run_bundle_command tools.",
        prompt="""## CRITICAL: You MUST Execute Tools

You are an EXECUTING agent. Upload and deploy bundles.
DO NOT describe deployment steps. EXECUTE THEM.

## Your Capabilities
- Upload: upload_bundle
- Run commands: run_bundle_command (validate, deploy, run)
- Sync: sync_workspace_to_local

## Task Execution

**For deployment:**
1. CALL mcp__databricks-mcp__upload_bundle(yaml_content=<yaml>, bundle_name=<name>)
2. Note the workspace_path from the response
3. CALL mcp__databricks-mcp__run_bundle_command(workspace_path=<path>, command="deploy", target="dev")
4. Return workspace path and deployment status

**For workspace validation:**
1. CALL mcp__databricks-mcp__run_bundle_command(workspace_path=<path>, command="validate")
2. Return validation results

**For syncing to local:**
1. CALL mcp__databricks-mcp__sync_workspace_to_local(workspace_path=<path>, local_path=<local>)
2. Return list of synced files

## Response Requirements

Your response MUST include actual deployment results, not instructions.
Include the workspace path and any CLI commands for follow-up actions.
""",
        tools=[
            "mcp__databricks-mcp__upload_bundle",
            "mcp__databricks-mcp__run_bundle_command",
            "mcp__databricks-mcp__sync_workspace_to_local",
        ],
        model="inherit",
    ),
}


DABS_SYSTEM_PROMPT = """
## DABs Copilot

You orchestrate Databricks Asset Bundle operations.

## When to Use Subagents (Task tool)

| subagent_type | Use When | Returns |
|---------------|----------|---------|
| dab-analyst | Analyzing jobs, notebooks, workspace paths | Job config, notebook analysis, dependencies |
| dab-builder | Creating or validating bundles | Generated databricks.yml, validation results |
| dab-deployer | Uploading or deploying bundles | Workspace paths, deployment status |

## Workflow Example

1. User: "Create bundle from job 12345"
2. You → dab-analyst: "Analyze job 12345" → Returns job structure + notebook analysis
3. You → dab-builder: "Generate bundle from job 12345 with analysis: [results]" → Returns databricks.yml
4. Ask user: "Ready to deploy?"
5. You → dab-deployer: "Deploy bundle [name] with yaml: [content]" → Returns workspace path

## Direct Tool Use

For simple queries, use MCP tools directly (no subagent needed):
- "List my jobs" → Call list_jobs directly
- "Check connection" → Call health directly
- "Get job 123" → Call get_job directly

## Important

- Subagents EXECUTE tools and return REAL data
- Pass specific IDs/paths to subagents in your prompt
- Expect actual results back, not guidance or frameworks
- Provide progress updates between subagent calls
"""


def get_mcp_config() -> dict:
    """Build MCP server configuration from environment."""
    mcp_url = os.getenv("DABS_MCP_SERVER_URL")
    if mcp_url:
        return {"databricks-mcp": {"type": "sse", "url": mcp_url}}

    # Local mode: run MCP server as subprocess
    mcp_command = os.getenv("DABS_MCP_COMMAND", "python")

    # Default to the local MCP server in this project
    default_mcp_path = str(Path(get_project_root()) / "mcp" / "server" / "main.py")
    mcp_args = os.getenv("DABS_MCP_ARGS", default_mcp_path).split(",")

    return {"databricks-mcp": {"type": "stdio", "command": mcp_command, "args": mcp_args}}


class DABsAgent:
    """
    Interactive DABs Copilot agent with multi-turn conversation support.

    Supports two tool modes:
    - "mcp": Use external MCP server (stdio or HTTP) - default for production
    - "custom": Use in-process custom tools via SDK MCP server - ideal for local development

    Usage:
        # Auto-detect mode (uses MCP if DABS_MCP_SERVER_URL set)
        async with DABsAgent() as agent:
            async for msg in agent.chat("Generate bundle from job 123"):
                print(msg)

        # Explicit custom tools mode (in-process, no external server)
        async with DABsAgent(tool_mode="custom") as agent:
            async for msg in agent.chat("List my jobs"):
                print(msg)

        # Custom tools with category filtering
        async with DABsAgent(tool_mode="custom", tool_category="dab") as agent:
            async for msg in agent.chat("Analyze notebook"):
                print(msg)
    """

    def __init__(
        self,
        tool_mode: str = "auto",
        tool_category: str | None = None,
        confirm_destructive: Callable[[str, dict], Awaitable[bool]] | None = None,
        mcp_config: dict | None = None,
    ):
        """
        Initialize the agent.

        Args:
            tool_mode: "auto" | "mcp" | "custom"
                - auto: Use MCP if DABS_MCP_SERVER_URL set, else custom tools
                - mcp: Use external MCP server (stdio or HTTP)
                - custom: Use in-process SDK MCP server (no external server)
            tool_category: Filter tools by category in custom mode:
                - "core": health, jobs, notebooks, SQL, DBFS, clusters
                - "dab": analyze, generate, validate bundles
                - "workspace": upload, sync, run bundle commands
                - None: all tools (default)
            confirm_destructive: Async callback for confirming destructive actions.
                                 Receives (tool_name, tool_input) and returns True to proceed.
                                 If None, destructive actions are auto-approved.
            mcp_config: Optional custom MCP configuration (only used in mcp mode).
        """
        self._client: ClaudeSDKClient | None = None
        self._session_id: str | None = None
        self._confirm_destructive = confirm_destructive
        self._tool_category = tool_category

        # Resolve tool mode
        if tool_mode == "auto":
            self._tool_mode = "mcp" if os.getenv("DABS_MCP_SERVER_URL") else "custom"
        else:
            self._tool_mode = tool_mode

        # Configure MCP servers based on mode
        if self._tool_mode == "mcp":
            self._mcp_config = mcp_config or get_mcp_config()
            self._sdk_mcp_server = None
        else:
            self._mcp_config = None
            # Create in-process SDK MCP server with the appropriate tools
            self._sdk_mcp_server = self._create_sdk_mcp_server()

    def _create_sdk_mcp_server(self):
        """Create SDK MCP server with filtered tools."""
        if self._tool_category == "core":
            tools = SDK_CORE_TOOLS
        elif self._tool_category == "dab":
            tools = SDK_DAB_TOOLS
        elif self._tool_category == "workspace":
            tools = SDK_WORKSPACE_TOOLS
        else:
            tools = SDK_ALL_TOOLS
        return create_databricks_mcp_server(tools=tools, server_name=CUSTOM_TOOLS_SERVER)

    def _get_mcp_servers(self) -> dict | None:
        """Get MCP server configuration based on tool mode."""
        if self._tool_mode == "mcp":
            return self._mcp_config
        # Custom mode - return SDK MCP server as dict
        if self._sdk_mcp_server:
            return {CUSTOM_TOOLS_SERVER: self._sdk_mcp_server}
        return None

    def _get_allowed_tools(self) -> list[str]:
        """Get allowed tools list based on tool mode."""
        if self._tool_mode == "mcp":
            return ALLOWED_TOOLS
        return get_custom_tools_allowed(self._tool_category)

    def _get_destructive_tools(self) -> list[str]:
        """Get destructive tool names based on tool mode."""
        if self._tool_mode == "mcp":
            return MCP_DESTRUCTIVE_TOOLS
        # Map to custom tool names
        return [f"mcp__{CUSTOM_TOOLS_SERVER}__{name}" for name in SDK_DESTRUCTIVE_TOOL_NAMES]

    async def __aenter__(self):
        """Start the agent session."""
        mcp_servers = self._get_mcp_servers()

        # Ensure LLM proxy environment variables are set
        # Claude Agent SDK reads ANTHROPIC_BASE_URL from environment
        anthropic_base = os.getenv("ANTHROPIC_BASE_URL")
        litellm_base = os.getenv("LITELLM_API_BASE")

        if litellm_base:
            # Use LiteLLM proxy as ANTHROPIC_BASE_URL
            os.environ["ANTHROPIC_BASE_URL"] = litellm_base

        # Build options based on tool mode
        options_kwargs = {
            "allowed_tools": self._get_allowed_tools(),
            "system_prompt": {
                "type": "preset",
                "preset": "claude_code",
                "append": DABS_SYSTEM_PROMPT,
            },
            "permission_mode": "default",
            "can_use_tool": self._check_tool_permission if self._confirm_destructive else None,
            "cwd": get_project_root(),
            "setting_sources": ["project"],
            "agents": DABS_AGENTS,
            # Model for main agent (env var allows override for Databricks FMAPI via LiteLLM)
            "model": os.getenv("DABS_MODEL", "databricks-claude-sonnet-4-5"),
        }

        # Add mcp_servers (either external MCP or in-process SDK server)
        if mcp_servers:
            options_kwargs["mcp_servers"] = mcp_servers

        options = ClaudeAgentOptions(**options_kwargs)

        self._client = ClaudeSDKClient(options=options)
        await self._client.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close the agent session."""
        if self._client:
            await self._client.disconnect()
            self._client = None

    async def _check_tool_permission(
        self, tool_name: str, tool_input: dict, context: ToolPermissionContext
    ) -> PermissionResultAllow | PermissionResultDeny:
        """Permission callback - pause for confirmation on destructive actions."""
        destructive = self._get_destructive_tools()
        if tool_name in destructive and self._confirm_destructive:
            approved = await self._confirm_destructive(tool_name, tool_input)
            if not approved:
                return PermissionResultDeny(message="User cancelled the operation")
        return PermissionResultAllow(updated_input=tool_input)

    @property
    def tool_mode(self) -> str:
        """Current tool mode (mcp or custom)."""
        return self._tool_mode

    async def chat(self, message: str, session_id: str = "default") -> AsyncIterator[Any]:
        """
        Send a message and stream the response.

        Args:
            message: User's message or instruction
            session_id: Session ID for the conversation (default: "default")

        Yields:
            SDK messages (text, tool_use, tool_result, etc.)
        """
        if not self._client:
            raise RuntimeError(
                "Agent not started. Use 'async with DABsAgent() as agent:'"
            )

        await self._client.query(message, session_id=session_id)

        async for msg in self._client.receive_messages():
            # Capture session ID from init message
            if hasattr(msg, "type") and msg.type == "system":
                if hasattr(msg, "subtype") and msg.subtype == "init":
                    if hasattr(msg, "session_id"):
                        self._session_id = msg.session_id
            yield msg
            # Break on ResultMessage - indicates turn is complete
            if isinstance(msg, ResultMessage):
                break

    @property
    def session_id(self) -> str | None:
        """Current session ID for resumption."""
        return self._session_id