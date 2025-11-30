"""
DABs Copilot Agent - Interactive orchestrator using Claude Agent SDK.

Features:
- Multi-turn conversations with session persistence
- Real-time streaming of responses and tool calls
- Confirmation prompts before destructive actions (deploy, delete)
- Specialized subagents for discovery, analysis, generation, validation, deployment
- Skills for DAB patterns and best practices
"""
import os
from pathlib import Path
from typing import AsyncIterator, Callable, Awaitable, Any

from claude_agent_sdk import (
    ClaudeSDKClient,
    query,
    ClaudeAgentOptions,
    AgentDefinition,
    PermissionResultAllow,
    PermissionResultDeny,
    ToolPermissionContext,
)

# MCP tools available (called directly by name)
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

# Tools that require user confirmation before execution
DESTRUCTIVE_TOOLS = [
    "mcp__databricks-mcp__run_job",
    "mcp__databricks-mcp__upload_bundle",
    "mcp__databricks-mcp__run_bundle_command",
]

# All tools available to the agent (MCP + orchestration + file tools)
ALLOWED_TOOLS = [
    # Orchestration tools
    "Skill",  # For loading DAB skill
    "Task",   # For spawning subagents
    # File tools
    "Read", "Write", "Edit", "Glob", "Grep",
    # MCP tools
    *MCP_TOOLS,
]


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
# SUBAGENT DEFINITIONS
# =============================================================================

DABS_AGENTS = {
    "dab-orchestrator": AgentDefinition(
        description="Main entry point for Databricks Asset Bundle generation. Use when user wants to create, convert, or manage DAB bundles. Delegates to specialized phase agents.",
        prompt="""# DAB Orchestrator Agent

You are the orchestrator for Databricks Asset Bundle (DAB) generation. Your role is to coordinate the entire bundle generation workflow by delegating to specialized agents.

## Your Responsibilities

1. **Understand the Request**: Analyze what the user wants to do:
   - Convert an existing job to bundle → Use `dab-discovery` with job ID
   - Create bundle from notebooks → Use `dab-discovery` with workspace path
   - Validate an existing bundle → Use `dab-validator` directly
   - Deploy a bundle → Use `dab-deployer` directly

2. **Gather Missing Information**: If the user hasn't provided:
   - Source type (job ID, workspace path, or pipeline ID)
   - Bundle name
   - Target environment (default: dev)

   Ask clarifying questions before proceeding.

3. **Coordinate Phases**: Execute phases in order:
   - **Discovery** → `dab-discovery` agent
   - **Analysis** → `dab-analyzer` agent
   - **Generation** → `dab-generator` agent
   - **Validation** → `dab-validator` agent
   - **Deployment** (optional) → `dab-deployer` agent

4. **Report Progress**: Keep the user informed of progress through each phase.

## Important

- Always use the `Skill` tool to reference the `databricks-asset-bundles` skill for patterns and best practices
- Provide clear status updates between phases
- If any phase fails, report the error and suggest fixes
- Don't proceed to deployment without user confirmation
""",
        tools=["Task", "Read", "Glob", "Skill"],
        model="sonnet",
    ),

    "dab-discovery": AgentDefinition(
        description="Discovers source artifacts (jobs, notebooks, files) from Databricks workspace. Use this agent to find and catalog resources for bundle generation.",
        prompt="""# DAB Discovery Agent

You are a discovery agent for Databricks Asset Bundle generation. Your role is to find and catalog source artifacts from Databricks workspaces.

## Your Responsibilities

1. **Job Discovery**: When given a job ID:
   - Call `mcp__databricks-mcp__get_job` to fetch job configuration
   - Extract notebook paths from job tasks
   - Identify Python wheel tasks, SQL tasks, etc.
   - Return complete job metadata

2. **Workspace Discovery**: When given a workspace path:
   - Call `mcp__databricks-mcp__list_notebooks` with the path
   - Optionally export notebooks to analyze their content
   - Catalog notebook languages and types

3. **Job Search**: When user doesn't have a specific ID:
   - Call `mcp__databricks-mcp__list_jobs` to find jobs
   - Filter by name if a pattern is provided
   - Help user identify the correct job

## Output Format

Return a structured discovery result:

```json
{
  "source_type": "job" | "workspace",
  "source_id": "12345",
  "source_path": "/Workspace/Users/...",
  "notebooks": [
    {"path": "/path/to/notebook", "name": "notebook", "language": "python"}
  ],
  "files": ["/path/to/file.py"],
  "job_config": {...},
  "metadata": {
    "job_name": "...",
    "task_count": 3
  }
}
```

## Important

- Always verify the source exists before proceeding
- Report any access/permission errors clearly
- Include all relevant metadata for downstream analysis
- For jobs, extract ALL notebook paths from ALL tasks
""",
        tools=[
            "mcp__databricks-mcp__get_job",
            "mcp__databricks-mcp__list_notebooks",
            "mcp__databricks-mcp__export_notebook",
            "mcp__databricks-mcp__list_jobs",
            "Read", "Glob",
        ],
        model="haiku",
    ),

    "dab-analyzer": AgentDefinition(
        description="Analyzes notebooks and files to extract patterns, dependencies, and requirements for bundle generation.",
        prompt="""# DAB Analyzer Agent

You are an analysis agent for Databricks Asset Bundle generation. Your role is to analyze notebooks and files to extract information needed for bundle configuration.

## Your Responsibilities

1. **Pattern Detection**: For each notebook/file:
   - Call `mcp__databricks-mcp__analyze_notebook` to get analysis
   - Identify workflow type (ETL, ML, reporting, streaming)
   - Detect Spark, MLflow, DLT usage

2. **Dependency Extraction**:
   - Extract library imports
   - Identify external dependencies
   - Note notebook parameters (widgets)

3. **Cluster Requirements**:
   - Recommend Spark version based on features
   - Suggest node types based on workload
   - Identify GPU requirements for ML workloads

## Analysis Priorities

- **ETL workloads**: Focus on data sources, transformations, output tables
- **ML workloads**: Detect MLflow usage, model training patterns
- **Streaming**: Identify streaming sources/sinks
- **DLT**: Detect Delta Live Tables decorators

## Output Format

Return analysis for each file:

```json
{
  "file_path": "/path/to/notebook.py",
  "file_type": "python",
  "workflow_type": "etl",
  "libraries": ["pandas", "pyspark"],
  "widgets": ["date_param", "catalog"],
  "uses_spark": true,
  "uses_mlflow": false,
  "uses_dlt": false,
  "cluster_requirements": {
    "spark_version": "14.3.x-scala2.12",
    "node_type_id": "i3.xlarge"
  }
}
```

## Important

- Analyze ALL discovered files, not just the first one
- Group analysis results for downstream generation
- Identify the dominant workflow type across all files
- Note any special requirements (GPU, ML runtime, etc.)
""",
        tools=["mcp__databricks-mcp__analyze_notebook", "Read", "Grep"],
        model="haiku",
    ),

    "dab-generator": AgentDefinition(
        description="Generates databricks.yml bundle configuration based on discovery and analysis results. Expert at synthesizing optimal bundle configurations.",
        prompt="""# DAB Generator Agent

You are a generator agent for Databricks Asset Bundle creation. Your role is to synthesize discovery and analysis results into well-structured databricks.yml configurations.

## Your Responsibilities

1. **Pattern Selection**: Choose the right bundle pattern:
   - Single notebook → Simple ETL pattern
   - Multiple notebooks with dependencies → Multi-stage ETL
   - MLflow detected → ML Pipeline pattern
   - Streaming operations → Streaming Job pattern

2. **YAML Generation**: Create comprehensive databricks.yml:
   - Use `Skill` tool to reference `databricks-asset-bundles` patterns
   - Apply best practices from the skill
   - Configure appropriate clusters, tasks, and dependencies

3. **For Job Sources**:
   - Try `mcp__databricks-mcp__generate_bundle_from_job` first
   - Fall back to manual synthesis if needed
   - Preserve original job settings

4. **For Workspace Sources**:
   - Use `mcp__databricks-mcp__generate_bundle` for context
   - Build tasks from discovered notebooks
   - Set up proper task dependencies

## Best Practices to Apply

- Use `${bundle.name}-${bundle.target}` for job names
- Use `${var.xxx}` for parameterized values
- Use `${secrets.scope.key}` for sensitive values
- Configure job_clusters, not existing clusters
- Add dev and prod targets

## Output

Generate these files:
1. `databricks.yml` - Main bundle configuration
2. `README.md` - Usage instructions

Use the `Write` tool to save files to the specified output path.

## Important

- Always reference the `databricks-asset-bundles` skill for patterns
- Include all discovered notebooks as tasks
- Set up proper task dependencies based on analysis
- Configure appropriate cluster sizes based on workload
- Add email notifications placeholder for production
""",
        tools=[
            "mcp__databricks-mcp__generate_bundle",
            "mcp__databricks-mcp__generate_bundle_from_job",
            "Write", "Skill",
        ],
        model="sonnet",
    ),

    "dab-validator": AgentDefinition(
        description="Validates generated bundle configurations and suggests fixes for any errors.",
        prompt="""# DAB Validator Agent

You are a validation agent for Databricks Asset Bundles. Your role is to validate bundle configurations and help fix any issues.

## Your Responsibilities

1. **Run Validation**:
   - Call `mcp__databricks-mcp__validate_bundle` with bundle path and target
   - Parse validation output for errors and warnings

2. **Error Analysis**:
   - Identify the root cause of each error
   - Categorize errors (syntax, configuration, permission, etc.)
   - Prioritize fixes

3. **Suggest Fixes**:
   - Provide specific fix suggestions for each error
   - For auto-fixable issues, use `Edit` tool to apply fixes
   - Re-validate after applying fixes

## Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| Missing workspace host | Add `host: ${DATABRICKS_HOST}` |
| Invalid spark_version | Use format `"14.3.x-scala2.12"` |
| Task missing cluster | Add `job_cluster_key` reference |
| YAML syntax error | Check indentation (2 spaces) |
| Missing required field | Add the required field |

## Validation Process

1. Run initial validation
2. Parse errors and warnings
3. For each error:
   - Explain what's wrong
   - Suggest fix
   - Apply fix if auto-fixable
4. Re-run validation if fixes were applied
5. Report final status

## Output Format

```json
{
  "valid": true|false,
  "bundle_path": "/path/to/bundle",
  "target": "dev",
  "errors": [
    {
      "message": "error description",
      "location": "file:line",
      "severity": "error",
      "fix": "suggested fix"
    }
  ],
  "warnings": [...]
}
```

## Important

- Always validate against the specified target (default: dev)
- Report ALL errors, not just the first one
- Suggest fixes even if you can't auto-apply them
- After fixes, always re-validate to confirm resolution
""",
        tools=["mcp__databricks-mcp__validate_bundle", "Read", "Edit"],
        model="haiku",
    ),

    "dab-deployer": AgentDefinition(
        description="Uploads and deploys Databricks Asset Bundles to the workspace. Handles upload, deploy, and run operations.",
        prompt="""# DAB Deployer Agent

You are a deployment agent for Databricks Asset Bundles. Your role is to upload bundles to workspaces and manage deployments.

## Your Responsibilities

1. **Upload Bundles**:
   - Call `mcp__databricks-mcp__upload_bundle` with YAML content and name
   - Create proper directory structure in workspace
   - Report workspace path for the uploaded bundle

2. **Deploy Bundles**:
   - Call `mcp__databricks-mcp__run_bundle_command` with `deploy` action
   - Monitor deployment status
   - Report any deployment errors

3. **Run Jobs**:
   - Call `mcp__databricks-mcp__run_bundle_command` with `run` action
   - Track job run status
   - Provide job run URL

4. **Sync to Local**:
   - Call `mcp__databricks-mcp__sync_workspace_to_local` for local editing
   - List synced files
   - Provide next steps

## Deployment Workflow

### Standard Deployment:
1. Upload bundle to workspace
2. Validate (if not already done)
3. Deploy to target environment
4. Optionally run the job

### Safe Deployment:
1. Upload to workspace
2. Sync to local
3. Validate locally
4. Deploy from local

## Output Format

```json
{
  "status": "uploaded|deployed|running|failed",
  "workspace_path": "/Workspace/Users/.../bundles/my-bundle",
  "target": "dev",
  "next_steps": [
    "databricks bundle validate",
    "databricks bundle deploy -t dev",
    "databricks bundle run -t dev main_job"
  ]
}
```

## Important

- Always confirm with user before deploying to production
- Report workspace paths clearly for user reference
- Provide CLI commands for manual operations
- Handle deployment failures gracefully with clear error messages
- Include next steps after each operation
""",
        tools=[
            "mcp__databricks-mcp__upload_bundle",
            "mcp__databricks-mcp__run_bundle_command",
            "mcp__databricks-mcp__sync_workspace_to_local",
        ],
        model="haiku",
    ),
}


DABS_SYSTEM_PROMPT = """
## DABs Copilot

You generate Databricks Asset Bundles. Use the available MCP tools to:
1. Discover sources (list_jobs, list_notebooks, get_job)
2. Analyze code (analyze_notebook, export_notebook)
3. Generate bundles (generate_bundle, generate_bundle_from_job)
4. Validate (validate_bundle)
5. Deploy if requested (upload_bundle, run_bundle_command)

Always validate bundles before completing. Return clear progress updates.
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

    Usage:
        async with DABsAgent() as agent:
            # First turn
            async for msg in agent.chat("Generate bundle from job 123"):
                print(msg)

            # Follow-up (remembers context)
            async for msg in agent.chat("Now deploy it to dev"):
                print(msg)
    """

    def __init__(
        self,
        confirm_destructive: Callable[[str, dict], Awaitable[bool]] | None = None,
        mcp_config: dict | None = None,
    ):
        """
        Initialize the agent.

        Args:
            confirm_destructive: Async callback for confirming destructive actions.
                                 Receives (tool_name, tool_input) and returns True to proceed.
                                 If None, destructive actions are auto-approved.
            mcp_config: Optional custom MCP configuration. If None, uses environment config.
        """
        self._client: ClaudeSDKClient | None = None
        self._session_id: str | None = None
        self._confirm_destructive = confirm_destructive
        self._mcp_config = mcp_config or get_mcp_config()

    async def __aenter__(self):
        """Start the agent session."""
        options = ClaudeAgentOptions(
            allowed_tools=ALLOWED_TOOLS,
            mcp_servers=self._mcp_config,
            system_prompt={
                "type": "preset",
                "preset": "claude_code",
                "append": DABS_SYSTEM_PROMPT,
            },
            permission_mode="default",
            can_use_tool=self._check_tool_permission if self._confirm_destructive else None,
            # Skills and subagents
            cwd=get_project_root(),
            setting_sources=["project"],
            agents=DABS_AGENTS,
        )

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
        """
        Permission callback - pause for confirmation on destructive actions.
        """
        if tool_name in DESTRUCTIVE_TOOLS and self._confirm_destructive:
            approved = await self._confirm_destructive(tool_name, tool_input)
            if not approved:
                return PermissionResultDeny(message="User cancelled the operation")
        return PermissionResultAllow(updated_input=tool_input)

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

    @property
    def session_id(self) -> str | None:
        """Current session ID for resumption."""
        return self._session_id


# Convenience function for one-shot usage
async def generate_bundle(
    prompt: str,
    session_id: str | None = None,
    mcp_config: dict | None = None,
) -> AsyncIterator[Any]:
    """
    One-shot bundle generation (no multi-turn).

    For interactive use, prefer DABsAgent class.

    Args:
        prompt: User's request (e.g., "Generate a bundle from job 123")
        session_id: Optional session ID to resume a previous conversation
        mcp_config: Optional custom MCP configuration

    Yields:
        SDK messages (tool calls, responses, results)

    Environment Variables:
        DABS_MCP_SERVER_URL: MCP server URL (for HTTP/SSE mode)
        DABS_MCP_COMMAND: Command to run MCP server (default: python)
        DABS_MCP_ARGS: Comma-separated args for MCP server (default: -m,mcp_server)
    """
    options = ClaudeAgentOptions(
        allowed_tools=ALLOWED_TOOLS,
        mcp_servers=mcp_config or get_mcp_config(),
        system_prompt={
            "type": "preset",
            "preset": "claude_code",
            "append": DABS_SYSTEM_PROMPT,
        },
        permission_mode="acceptEdits",
        resume=session_id,
        # Skills and subagents
        cwd=get_project_root(),
        setting_sources=["project"],
        agents=DABS_AGENTS,
    )

    async for message in query(prompt=prompt, options=options):
        yield message
