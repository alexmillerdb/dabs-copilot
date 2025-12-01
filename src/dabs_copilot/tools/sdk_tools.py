"""SDK-compatible custom tools using claude_agent_sdk decorators."""
import asyncio
import os
import re
import base64
import subprocess
from datetime import datetime
from typing import Any

from claude_agent_sdk import tool, create_sdk_mcp_server

# Databricks client
from databricks.sdk import WorkspaceClient
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()

@lru_cache(maxsize=1)
def _get_client() -> WorkspaceClient:
    """Get cached Databricks client."""
    profile = os.getenv("DATABRICKS_CONFIG_PROFILE")
    if profile:
        return WorkspaceClient(profile=profile)
    return WorkspaceClient()


# =============================================================================
# CORE TOOLS
# =============================================================================

@tool("health", "Check Databricks workspace connection. Returns workspace URL and authenticated user.", {})
async def health(args: dict[str, Any]) -> dict[str, Any]:
    try:
        client = _get_client()
        user = await asyncio.to_thread(client.current_user.me)
        return {"content": [{"type": "text", "text": f'{{"status": "healthy", "workspace_url": "{client.config.host}", "user": "{user.user_name}"}}'}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f'{{"error": "Connection failed: {e}"}}'}]}


@tool("list_jobs", "List jobs in Databricks workspace. Filter by name substring.", {"limit": int, "name_filter": str})
async def list_jobs(args: dict[str, Any]) -> dict[str, Any]:
    try:
        import json
        client = _get_client()
        limit = args.get("limit", 100)
        name_filter = (args.get("name_filter") or "").lower()

        def _list_jobs_sync():
            jobs = []
            for j in client.jobs.list():
                if len(jobs) >= limit:
                    break
                if not name_filter or name_filter in j.settings.name.lower():
                    jobs.append({"job_id": j.job_id, "name": j.settings.name, "creator": j.creator_user_name})
            return jobs

        jobs = await asyncio.to_thread(_list_jobs_sync)
        return {"content": [{"type": "text", "text": json.dumps({"jobs": jobs, "count": len(jobs)})}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f'{{"error": "Failed to list jobs: {e}"}}'}]}


@tool("get_job", "Get detailed job configuration including tasks, clusters, and schedule.", {"job_id": int})
async def get_job(args: dict[str, Any]) -> dict[str, Any]:
    try:
        import json
        client = _get_client()
        job = await asyncio.to_thread(client.jobs.get, job_id=args["job_id"])

        tasks = [{
            "task_key": t.task_key,
            "type": "notebook" if t.notebook_task else "python" if t.python_wheel_task else "other",
            "path": t.notebook_task.notebook_path if t.notebook_task else None,
            "depends_on": [d.task_key for d in (t.depends_on or [])]
        } for t in (job.settings.tasks or [])]

        result = {
            "job_id": job.job_id,
            "name": job.settings.name,
            "tasks": tasks,
            "max_concurrent_runs": job.settings.max_concurrent_runs
        }
        return {"content": [{"type": "text", "text": json.dumps(result)}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f'{{"error": "Failed to get job: {e}"}}'}]}


@tool("run_job", "Execute a job. WARNING: May incur compute costs.", {"job_id": int, "notebook_params": dict})
async def run_job(args: dict[str, Any]) -> dict[str, Any]:
    try:
        import json
        client = _get_client()
        job_id = args["job_id"]
        params = args.get("notebook_params")

        run = await asyncio.to_thread(client.jobs.run_now, job_id=job_id, notebook_params=params)
        return {"content": [{"type": "text", "text": json.dumps({"run_id": run.run_id, "job_id": job_id, "status": "TRIGGERED"})}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f'{{"error": "Failed to run job: {e}"}}'}]}


@tool("list_notebooks", "List notebooks in a workspace path. Optionally recursive.", {"path": str, "recursive": bool, "limit": int})
async def list_notebooks(args: dict[str, Any]) -> dict[str, Any]:
    try:
        import json
        from databricks.sdk.service import workspace as ws

        client = _get_client()
        path = args.get("path", "/")
        recursive = args.get("recursive", False)
        limit = args.get("limit", 100)

        def _list_notebooks_sync():
            notebooks = []

            def list_path(current_path: str, depth: int = 0):
                if len(notebooks) >= limit:
                    return
                if not recursive and depth > 0:
                    return
                try:
                    for obj in client.workspace.list(path=current_path):
                        if len(notebooks) >= limit:
                            return
                        if obj.object_type == ws.ObjectType.NOTEBOOK:
                            notebooks.append({
                                "path": obj.path,
                                "language": obj.language.value if obj.language else "UNKNOWN"
                            })
                        elif recursive and obj.object_type == ws.ObjectType.DIRECTORY:
                            list_path(obj.path, depth + 1)
                except Exception:
                    pass

            list_path(path)
            return notebooks

        notebooks = await asyncio.to_thread(_list_notebooks_sync)
        return {"content": [{"type": "text", "text": json.dumps({"notebooks": notebooks, "count": len(notebooks), "path": path})}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f'{{"error": "Failed to list notebooks: {e}"}}'}]}


@tool("export_notebook", "Export notebook content. Formats: SOURCE, HTML, JUPYTER, DBC.", {"path": str, "format": str})
async def export_notebook(args: dict[str, Any]) -> dict[str, Any]:
    try:
        import json
        from databricks.sdk.service import workspace as ws

        client = _get_client()
        path = args["path"]
        fmt = args.get("format", "SOURCE").upper()

        export_format = ws.ExportFormat[fmt]
        content = await asyncio.to_thread(client.workspace.export, path=path, format=export_format)

        if export_format == ws.ExportFormat.SOURCE:
            try:
                decoded = base64.b64decode(content.content).decode('utf-8')
            except Exception:
                decoded = content.content
        else:
            decoded = content.content

        return {"content": [{"type": "text", "text": json.dumps({"path": path, "format": fmt, "content": decoded})}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f'{{"error": "Failed to export notebook: {e}"}}'}]}


@tool("execute_dbsql", "Execute SQL on Databricks SQL warehouse. WARNING: Can run DDL/DML.", {"query": str, "warehouse_id": str})
async def execute_dbsql(args: dict[str, Any]) -> dict[str, Any]:
    try:
        import json
        client = _get_client()
        query = args["query"]
        warehouse_id = args.get("warehouse_id") or os.getenv("DATABRICKS_WAREHOUSE_ID", "auto")

        result = await asyncio.to_thread(
            client.statement_execution.execute_statement,
            warehouse_id=warehouse_id,
            statement=query,
            format="JSON_ARRAY"
        )

        rows = []
        if result.result and result.result.data_array:
            columns = [col.name for col in result.manifest.schema.columns]
            rows = [dict(zip(columns, row)) for row in result.result.data_array]

        return {"content": [{"type": "text", "text": json.dumps({"query": query, "rows": rows, "row_count": len(rows)})}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f'{{"error": "SQL execution failed: {e}"}}'}]}


@tool("list_warehouses", "List available SQL warehouses with status.", {"limit": int})
async def list_warehouses(args: dict[str, Any]) -> dict[str, Any]:
    try:
        import json
        client = _get_client()
        limit = args.get("limit", 100)

        def _list_warehouses_sync():
            warehouses = []
            for w in client.warehouses.list():
                if len(warehouses) >= limit:
                    break
                warehouses.append({
                    "id": w.id,
                    "name": w.name,
                    "size": w.cluster_size,
                    "state": w.state.value if w.state else "UNKNOWN"
                })
            return warehouses

        warehouses = await asyncio.to_thread(_list_warehouses_sync)
        return {"content": [{"type": "text", "text": json.dumps({"warehouses": warehouses, "count": len(warehouses)})}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f'{{"error": "Failed to list warehouses: {e}"}}'}]}


@tool("list_dbfs_files", "List files and directories in DBFS path.", {"path": str, "limit": int})
async def list_dbfs_files(args: dict[str, Any]) -> dict[str, Any]:
    try:
        import json
        client = _get_client()
        path = args.get("path", "/")
        limit = args.get("limit", 100)

        def _list_files_sync():
            files = []
            for f in client.dbfs.list(path=path):
                if len(files) >= limit:
                    break
                files.append({
                    "path": f.path,
                    "is_dir": f.is_dir,
                    "size": f.file_size
                })
            return files

        files = await asyncio.to_thread(_list_files_sync)
        return {"content": [{"type": "text", "text": json.dumps({"files": files, "count": len(files), "path": path})}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f'{{"error": "Failed to list DBFS: {e}"}}'}]}


@tool("get_cluster", "Get cluster configuration by ID for job cluster generation.", {"cluster_id": str})
async def get_cluster(args: dict[str, Any]) -> dict[str, Any]:
    try:
        import json
        client = _get_client()
        cluster = await asyncio.to_thread(client.clusters.get, cluster_id=args["cluster_id"])

        result = {
            "cluster_id": cluster.cluster_id,
            "name": cluster.cluster_name,
            "spark_version": cluster.spark_version,
            "node_type_id": cluster.node_type_id,
            "num_workers": cluster.num_workers,
            "state": cluster.state.value if cluster.state else None
        }
        return {"content": [{"type": "text", "text": json.dumps(result)}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f'{{"error": "Failed to get cluster: {e}"}}'}]}


# =============================================================================
# DAB TOOLS
# =============================================================================

@tool("analyze_notebook", "Analyze notebook to extract libraries, parameters, and workflow patterns.", {"notebook_path": str})
async def analyze_notebook(args: dict[str, Any]) -> dict[str, Any]:
    try:
        import json
        path = args["notebook_path"]

        # Get content
        if os.path.exists(path):
            with open(path) as f:
                content = f.read()
        else:
            from databricks.sdk.service import workspace as ws
            client = _get_client()
            export = await asyncio.to_thread(client.workspace.export, path=path, format=ws.ExportFormat.SOURCE)
            content = base64.b64decode(export.content).decode('utf-8') if export.content else ""

        # Analyze
        file_type = 'sql' if path.endswith('.sql') else 'python' if path.endswith('.py') else 'notebook'

        # Extract imports
        import_pattern = r'(?:from|import)\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        common_libs = {'pandas', 'numpy', 'sklearn', 'tensorflow', 'torch', 'mlflow', 'pyspark', 'databricks'}
        imports = set(re.findall(import_pattern, content))
        libraries = [lib for lib in imports if lib in common_libs]

        # Extract widgets
        widget_pattern = r'dbutils\.widgets\.\w+\(["\']([^"\']+)["\']'
        widgets = list(set(re.findall(widget_pattern, content)))

        # Detect workflow type
        content_lower = content.lower()
        if 'mlflow' in content_lower or 'model' in content_lower:
            workflow_type = 'ml'
        elif 'display(' in content or 'plot' in content_lower:
            workflow_type = 'reporting'
        elif '@dlt.' in content or 'import dlt' in content:
            workflow_type = 'dlt'
        else:
            workflow_type = 'etl'

        result = {
            "path": path,
            "file_type": file_type,
            "libraries": libraries,
            "widgets": widgets,
            "workflow_type": workflow_type,
            "uses_spark": "spark" in content_lower,
            "uses_mlflow": "mlflow" in content_lower,
            "uses_dlt": "@dlt." in content or "import dlt" in content
        }
        return {"content": [{"type": "text", "text": json.dumps(result)}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f'{{"error": "Analysis failed: {e}"}}'}]}


@tool("generate_bundle", "Generate DAB context from file analysis. Returns patterns and recommendations.", {"bundle_name": str, "file_paths": list, "output_path": str})
async def generate_bundle(args: dict[str, Any]) -> dict[str, Any]:
    try:
        import json
        bundle_name = args["bundle_name"]
        file_paths = args["file_paths"]
        output_path = args.get("output_path") or f"./{bundle_name}"

        os.makedirs(output_path, exist_ok=True)

        # Analyze each file (simplified)
        analyses = []
        for path in file_paths:
            try:
                result = await analyze_notebook({"notebook_path": path})
                text = result["content"][0]["text"]
                analyses.append(json.loads(text))
            except Exception as e:
                analyses.append({"path": path, "error": str(e)})

        # Determine dominant workflow
        workflow_types = [a.get("workflow_type") for a in analyses if "workflow_type" in a]
        dominant = max(set(workflow_types), key=workflow_types.count) if workflow_types else "etl"

        result = {
            "bundle_name": bundle_name,
            "output_path": output_path,
            "file_analyses": analyses,
            "dominant_workflow": dominant,
            "workspace_host": _get_client().config.host
        }
        return {"content": [{"type": "text", "text": json.dumps(result)}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f'{{"error": "Bundle generation failed: {e}"}}'}]}


@tool("generate_bundle_from_job", "Generate DAB from existing Databricks job using CLI.", {"job_id": int, "output_dir": str})
async def generate_bundle_from_job(args: dict[str, Any]) -> dict[str, Any]:
    try:
        import json
        import tempfile

        job_id = args["job_id"]
        output_dir = args.get("output_dir") or tempfile.mkdtemp(prefix=f"dab_{job_id}_")

        # Verify job exists
        client = _get_client()
        job = await asyncio.to_thread(client.jobs.get, job_id=job_id)

        os.makedirs(output_dir, exist_ok=True)

        # Run databricks bundle generate
        cmd = ["databricks", "bundle", "generate", "job", "--existing-job-id", str(job_id)]
        profile = os.getenv("DATABRICKS_CONFIG_PROFILE")
        if profile:
            cmd.extend(["--profile", profile])

        result = await asyncio.to_thread(
            subprocess.run, cmd, cwd=output_dir, capture_output=True, text=True, timeout=30
        )

        if result.returncode != 0:
            return {"content": [{"type": "text", "text": f'{{"error": "Bundle generation failed: {result.stderr or result.stdout}"}}'}]}

        # Read generated files
        generated_files = []
        for root, _, files in os.walk(output_dir):
            for f in files:
                generated_files.append(os.path.relpath(os.path.join(root, f), output_dir))

        # Read bundle content
        bundle_content = None
        for yml_name in ["databricks.yml", "bundle.yml"]:
            yml_path = os.path.join(output_dir, yml_name)
            if os.path.exists(yml_path):
                with open(yml_path) as f:
                    bundle_content = f.read()
                break

        result = {
            "job_id": job_id,
            "job_name": job.settings.name,
            "bundle_dir": output_dir,
            "generated_files": generated_files,
            "bundle_content": bundle_content
        }
        return {"content": [{"type": "text", "text": json.dumps(result)}]}
    except subprocess.TimeoutExpired:
        return {"content": [{"type": "text", "text": '{"error": "Bundle generation timed out after 30s"}'}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f'{{"error": "Failed to generate bundle: {e}"}}'}]}


@tool("validate_bundle", "Validate DAB configuration using Databricks CLI.", {"bundle_path": str, "target": str})
async def validate_bundle(args: dict[str, Any]) -> dict[str, Any]:
    try:
        import json
        bundle_path = args["bundle_path"]
        target = args.get("target", "dev")

        working_dir = bundle_path if os.path.isdir(bundle_path) else os.path.dirname(bundle_path)

        cmd = ["databricks", "bundle", "validate", "-t", target]
        profile = os.getenv("DATABRICKS_CONFIG_PROFILE")
        if profile:
            cmd.extend(["--profile", profile])

        result = await asyncio.to_thread(
            subprocess.run, cmd, cwd=working_dir, capture_output=True, text=True, timeout=60
        )

        output = {
            "valid": result.returncode == 0,
            "bundle_path": bundle_path,
            "target": target,
            "output": result.stdout.strip() if result.stdout else result.stderr.strip()
        }
        return {"content": [{"type": "text", "text": json.dumps(output)}]}
    except subprocess.TimeoutExpired:
        return {"content": [{"type": "text", "text": '{"error": "Validation timed out after 60s"}'}]}
    except FileNotFoundError:
        return {"content": [{"type": "text", "text": '{"error": "Databricks CLI not found. Install with: pip install databricks-cli"}'}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f'{{"error": "Validation failed: {e}"}}'}]}


# =============================================================================
# WORKSPACE TOOLS
# =============================================================================

@tool("upload_bundle", "Upload bundle YAML and README to Databricks workspace.", {"yaml_content": str, "bundle_name": str, "workspace_base": str})
async def upload_bundle(args: dict[str, Any]) -> dict[str, Any]:
    try:
        import json
        yaml_content = args["yaml_content"]
        bundle_name = args["bundle_name"]
        workspace_base = args.get("workspace_base")

        # Local mode check
        if os.getenv("USE_LOCAL_BUNDLE_STORAGE", "").lower() == "true":
            return {"content": [{"type": "text", "text": json.dumps({
                "mode": "local",
                "bundle_name": bundle_name,
                "suggested_path": f"generated_bundles/{bundle_name}"
            })}]}

        def _upload_sync():
            client = _get_client()
            user = client.current_user.me()

            base = workspace_base or f"/Workspace/Users/{user.user_name}/bundles"
            bundle_path = f"{base}/{bundle_name}"

            # Create directories
            for subdir in ["", "/resources", "/src"]:
                try:
                    client.workspace.mkdirs(f"{bundle_path}{subdir}")
                except Exception:
                    pass

            # Upload YAML
            yaml_encoded = base64.b64encode(yaml_content.encode()).decode()
            client.workspace.upload(
                path=f"{bundle_path}/databricks.yml",
                content=yaml_encoded,
                format="AUTO",
                overwrite=True
            )

            # Upload README
            readme = f"# {bundle_name}\n\nGenerated: {datetime.now().isoformat()}\n\n```bash\ndatabricks bundle validate\ndatabricks bundle deploy -t dev\n```"
            client.workspace.upload(
                path=f"{bundle_path}/README.md",
                content=base64.b64encode(readme.encode()).decode(),
                format="AUTO",
                overwrite=True
            )

            return bundle_path

        bundle_path = await asyncio.to_thread(_upload_sync)

        result = {
            "bundle_path": bundle_path,
            "files_uploaded": [f"{bundle_path}/databricks.yml", f"{bundle_path}/README.md"],
            "next_steps": {
                "validate": f"databricks bundle validate --chdir {bundle_path}",
                "deploy": f"databricks bundle deploy -t dev --chdir {bundle_path}"
            }
        }
        return {"content": [{"type": "text", "text": json.dumps(result)}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f'{{"error": "Failed to upload bundle: {e}"}}'}]}


@tool("run_bundle_command", "Run Databricks bundle CLI command. WARNING: deploy/run incur costs.", {"workspace_path": str, "command": str, "target": str, "profile": str})
async def run_bundle_command(args: dict[str, Any]) -> dict[str, Any]:
    try:
        import json
        workspace_path = args["workspace_path"]
        command = args.get("command", "validate")
        target = args.get("target", "dev")
        profile = args.get("profile") or os.getenv("DATABRICKS_CONFIG_PROFILE", "DEFAULT")

        allowed = ["validate", "deploy", "run", "destroy", "summary"]
        if command not in allowed:
            return {"content": [{"type": "text", "text": f'{{"error": "Invalid command. Allowed: {", ".join(allowed)}"}}'}]}

        instructions = [
            f"# Sync bundle to local first:",
            f"databricks workspace export-dir {workspace_path} ./temp_bundle --profile {profile}",
            f"cd ./temp_bundle",
            f"databricks bundle {command} --profile {profile}" + (f" -t {target}" if command in ["deploy", "run"] else "")
        ]

        result = {
            "command": command,
            "workspace_path": workspace_path,
            "target": target,
            "status": "guidance",
            "instructions": instructions,
            "note": "Bundle commands require local bundle access"
        }
        return {"content": [{"type": "text", "text": json.dumps(result)}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f'{{"error": "Failed to run bundle command: {e}"}}'}]}


@tool("sync_workspace_to_local", "Sync files from Databricks workspace to local filesystem.", {"workspace_path": str, "local_path": str, "profile": str})
async def sync_workspace_to_local(args: dict[str, Any]) -> dict[str, Any]:
    try:
        import json
        workspace_path = args["workspace_path"]
        local_path = args["local_path"]
        profile = args.get("profile") or os.getenv("DATABRICKS_CONFIG_PROFILE", "DEFAULT")

        os.makedirs(local_path, exist_ok=True)

        cmd = ["databricks", "workspace", "export-dir", "--profile", profile, workspace_path, local_path]
        result = await asyncio.to_thread(
            subprocess.run, cmd, capture_output=True, text=True, timeout=30
        )

        if result.returncode != 0:
            return {"content": [{"type": "text", "text": f'{{"error": "Sync failed: {result.stderr or "Unknown error"}"}}'}]}

        # List synced files
        synced = []
        for root, _, files in os.walk(local_path):
            for f in files:
                synced.append(os.path.relpath(os.path.join(root, f), local_path))

        output = {
            "workspace_path": workspace_path,
            "local_path": local_path,
            "files_synced": synced,
            "count": len(synced),
            "next_steps": {
                "validate": f"cd {local_path} && databricks bundle validate",
                "deploy": f"cd {local_path} && databricks bundle deploy -t dev"
            }
        }
        return {"content": [{"type": "text", "text": json.dumps(output)}]}
    except subprocess.TimeoutExpired:
        return {"content": [{"type": "text", "text": '{"error": "Sync timed out after 30s"}'}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f'{{"error": "Failed to sync: {e}"}}'}]}


# =============================================================================
# SDK MCP SERVER
# =============================================================================

# All tools list
ALL_TOOLS = [
    # Core
    health, list_jobs, get_job, run_job, list_notebooks, export_notebook,
    execute_dbsql, list_warehouses, list_dbfs_files, get_cluster,
    # DAB
    analyze_notebook, generate_bundle, generate_bundle_from_job, validate_bundle,
    # Workspace
    upload_bundle, run_bundle_command, sync_workspace_to_local,
]

# Tool categories for filtering
CORE_TOOLS = [health, list_jobs, get_job, run_job, list_notebooks, export_notebook,
              execute_dbsql, list_warehouses, list_dbfs_files, get_cluster]
DAB_TOOLS = [analyze_notebook, generate_bundle, generate_bundle_from_job, validate_bundle]
WORKSPACE_TOOLS = [upload_bundle, run_bundle_command, sync_workspace_to_local]

# Destructive tools that need confirmation
DESTRUCTIVE_TOOL_NAMES = ["run_job", "upload_bundle", "run_bundle_command", "execute_dbsql"]


def create_databricks_mcp_server(
    tools: list | None = None,
    server_name: str = "databricks",
    version: str = "1.0.0"
):
    """Create an SDK MCP server with Databricks tools.

    Args:
        tools: List of tool functions to include (default: all tools)
        server_name: Name for the MCP server
        version: Server version

    Returns:
        SDK MCP server instance
    """
    return create_sdk_mcp_server(
        name=server_name,
        version=version,
        tools=tools or ALL_TOOLS
    )


def get_tool_names(tools: list | None = None, server_name: str = "databricks") -> list[str]:
    """Get MCP-formatted tool names.

    Args:
        tools: List of SdkMcpTool objects (default: all tools)
        server_name: MCP server name

    Returns:
        List of tool names in format mcp__{server}__{name}
    """
    tool_list = tools or ALL_TOOLS
    names = []
    for t in tool_list:
        # SdkMcpTool objects have a 'name' attribute
        if hasattr(t, 'name'):
            names.append(f"mcp__{server_name}__{t.name}")
        elif hasattr(t, '__name__'):
            names.append(f"mcp__{server_name}__{t.__name__}")
    return names
