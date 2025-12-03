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

# Import prompts (handle both package and standalone imports)
try:
    from .prompts import (
        SUBAGENT_ANALYST,
        SUBAGENT_BUILDER,
        SUBAGENT_DEPLOYER,
        DAB_ANALYST_PROMPT,
        DAB_BUILDER_PROMPT,
        DAB_DEPLOYER_PROMPT,
        DABS_SYSTEM_PROMPT,
    )
except ImportError:
    from prompts import (
        SUBAGENT_ANALYST,
        SUBAGENT_BUILDER,
        SUBAGENT_DEPLOYER,
        DAB_ANALYST_PROMPT,
        DAB_BUILDER_PROMPT,
        DAB_DEPLOYER_PROMPT,
        DABS_SYSTEM_PROMPT,
    )

# Custom tools server name (for in-process mode)
# Must match MCP server name for consistent tool naming across modes
CUSTOM_TOOLS_SERVER = "databricks-mcp"

# Base tool names (without MCP prefix)
_MCP_TOOL_NAMES = [
    "health",
    "list_jobs",
    "get_job",
    "run_job",
    "list_notebooks",
    "export_notebook",
    "execute_dbsql",
    "list_warehouses",
    "list_dbfs_files",
    "get_cluster",
    "analyze_notebook",
    "generate_bundle",
    "generate_bundle_from_job",
    "validate_bundle",
    "upload_bundle",
    "run_bundle_command",
    "sync_workspace_to_local",
]

# Destructive tool names (subset that requires confirmation)
_MCP_DESTRUCTIVE_NAMES = ["run_job", "upload_bundle", "run_bundle_command"]

# Generate MCP-formatted tool names
MCP_TOOLS = [f"mcp__{CUSTOM_TOOLS_SERVER}__{name}" for name in _MCP_TOOL_NAMES]
MCP_DESTRUCTIVE_TOOLS = [f"mcp__{CUSTOM_TOOLS_SERVER}__{name}" for name in _MCP_DESTRUCTIVE_NAMES]

# Base tools available to the agent (orchestration + file tools)
BASE_TOOLS = [
    "Skill",  # For loading DAB skill
    "Task",   # For spawning subagents
    "Read", "Write", "Edit", "Glob", "Grep",
]

# All tools available in MCP mode
ALLOWED_TOOLS = BASE_TOOLS + MCP_TOOLS

load_dotenv()

# Set env vars only if they exist (avoid TypeError from None assignment)
if _host := os.getenv("DATABRICKS_HOST"):
    os.environ['DATABRICKS_HOST'] = _host
if _profile := os.getenv("DATABRICKS_CONFIG_PROFILE"):
    os.environ['DATABRICKS_CONFIG_PROFILE'] = _profile

mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "databricks"))
mlflow.set_experiment(experiment_id=os.getenv("MLFLOW_EXPERIMENT_ID", "567797472279756"))
mlflow.anthropic.autolog()


def _get_tools_by_category(category: str | None) -> list:
    """Get SDK tool list for a category.

    Args:
        category: "core", "dab", "workspace", or None for all

    Returns:
        List of SDK tool definitions
    """
    match category:
        case "core":
            return SDK_CORE_TOOLS
        case "dab":
            return SDK_DAB_TOOLS
        case "workspace":
            return SDK_WORKSPACE_TOOLS
        case _:
            return SDK_ALL_TOOLS


def get_custom_tool_names(category: str | None = None) -> list[str]:
    """Get tool names for custom tools mode.

    Args:
        category: Filter by category - "core", "dab", "workspace", or None for all

    Returns:
        List of MCP-formatted tool names (mcp__databricks__tool_name)
    """
    return get_sdk_tool_names(_get_tools_by_category(category), CUSTOM_TOOLS_SERVER)


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
    SUBAGENT_ANALYST: AgentDefinition(
        description="Analyzes Databricks jobs and notebooks. EXECUTES get_job, list_notebooks, analyze_notebook tools.",
        prompt=DAB_ANALYST_PROMPT,
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
    SUBAGENT_BUILDER: AgentDefinition(
        description="Generates and validates DAB bundles. EXECUTES generate_bundle, validate_bundle tools.",
        prompt=DAB_BUILDER_PROMPT,
        tools=[
            "mcp__databricks-mcp__generate_bundle",
            "mcp__databricks-mcp__generate_bundle_from_job",
            "mcp__databricks-mcp__validate_bundle",
            "Write", "Edit", "Read", "Skill",
        ],
        model="inherit",
    ),
    SUBAGENT_DEPLOYER: AgentDefinition(
        description="Deploys bundles to Databricks workspace. EXECUTES upload_bundle, run_bundle_command tools.",
        prompt=DAB_DEPLOYER_PROMPT,
        tools=[
            "mcp__databricks-mcp__upload_bundle",
            "mcp__databricks-mcp__run_bundle_command",
            "mcp__databricks-mcp__sync_workspace_to_local",
        ],
        model="inherit",
    ),
}


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
        # Validate tool_mode parameter
        valid_tool_modes = {"auto", "mcp", "custom"}
        if tool_mode not in valid_tool_modes:
            raise ValueError(
                f"Invalid tool_mode '{tool_mode}'. Must be one of {valid_tool_modes}"
            )

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
        tools = _get_tools_by_category(self._tool_category)
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
        # Use LiteLLM proxy as ANTHROPIC_BASE_URL if configured
        # Claude Agent SDK reads ANTHROPIC_BASE_URL from environment
        if litellm_base := os.getenv("LITELLM_API_BASE"):
            os.environ["ANTHROPIC_BASE_URL"] = litellm_base

        # Build base options
        options_kwargs = {
            "allowed_tools": self._get_allowed_tools(),
            "system_prompt": {
                "type": "preset",
                "preset": "claude_code",
                "append": DABS_SYSTEM_PROMPT,
            },
            "permission_mode": "default",
            "cwd": get_project_root(),
            "setting_sources": ["project"],
            "agents": DABS_AGENTS,
            "model": os.getenv("DABS_MODEL", "databricks-claude-sonnet-4-5"),
        }

        # Add permission callback if destructive action confirmation is enabled
        if self._confirm_destructive:
            options_kwargs["can_use_tool"] = self._check_tool_permission

        # Add MCP servers (either external MCP or in-process SDK server)
        if mcp_servers := self._get_mcp_servers():
            options_kwargs["mcp_servers"] = mcp_servers

        options = ClaudeAgentOptions(**options_kwargs)

        self._client = ClaudeSDKClient(options=options)
        try:
            await self._client.connect()
        except Exception as e:
            # Cleanup on connection failure
            self._client = None
            raise RuntimeError(f"Failed to connect DABs agent: {e}") from e
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close the agent session."""
        if self._client:
            await self._client.disconnect()
            self._client = None

    async def _check_tool_permission(
        self, tool_name: str, tool_input: dict, _context: ToolPermissionContext
    ) -> PermissionResultAllow | PermissionResultDeny:
        """Permission callback - pause for confirmation on destructive actions."""
        # Allow non-destructive tools immediately
        if tool_name not in self._get_destructive_tools():
            return PermissionResultAllow(updated_input=tool_input)

        # No confirmation callback configured - auto-approve
        if not self._confirm_destructive:
            return PermissionResultAllow(updated_input=tool_input)

        # Ask for confirmation
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

        try:
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
        except Exception as e:
            yield {"type": "error", "error": str(e)}

    @property
    def session_id(self) -> str | None:
        """Current session ID for resumption."""
        return self._session_id