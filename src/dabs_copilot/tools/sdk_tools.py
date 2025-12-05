"""SDK-compatible custom tools using claude_agent_sdk decorators."""
import asyncio
import base64
import hashlib
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from claude_agent_sdk import tool, create_sdk_mcp_server

# Databricks client
from databricks.sdk import WorkspaceClient
from functools import lru_cache
from dotenv import load_dotenv

from .analysis import analyze_content, calculate_complexity_score

load_dotenv()

@lru_cache(maxsize=1)
def _get_client() -> WorkspaceClient:
    """Get cached Databricks client."""
    profile = os.getenv("DATABRICKS_CONFIG_PROFILE")
    if profile:
        return WorkspaceClient(profile=profile)
    return WorkspaceClient()


def _error_response(message: str) -> dict[str, Any]:
    """Create a standardized error response."""
    return {"content": [{"type": "text", "text": json.dumps({"error": message})}]}


def _success_response(data: dict[str, Any]) -> dict[str, Any]:
    """Create a standardized success response."""
    return {"content": [{"type": "text", "text": json.dumps(data)}]}


# =============================================================================
# ANALYSIS CACHE
# =============================================================================

CACHE_DIR = Path(".cache/analysis")


def _get_cache_key(file_path: str, content: str) -> str:
    """Generate cache key from file path and content hash."""
    try:
        mtime = int(os.path.getmtime(file_path))
    except OSError:
        mtime = 0  # Workspace paths don't have mtime
    content_hash = hashlib.sha256(content.encode()).hexdigest()[:12]
    name = Path(file_path).stem[:20]
    return f"{name}_{content_hash}_{mtime}"


def _load_from_cache(cache_key: str) -> dict | None:
    """Load cached analysis if exists."""
    cache_file = CACHE_DIR / f"{cache_key}.json"
    if cache_file.exists():
        try:
            return json.loads(cache_file.read_text())
        except (json.JSONDecodeError, IOError):
            return None
    return None


def _save_to_cache(cache_key: str, result: dict) -> None:
    """Save analysis to disk cache."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"{cache_key}.json"
    cache_file.write_text(json.dumps(result, indent=2))


# =============================================================================
# CORE TOOLS
# =============================================================================

@tool("health", "Check Databricks workspace connection. Returns workspace URL and authenticated user.", {})
async def health(args: dict[str, Any]) -> dict[str, Any]:
    _ = args  # unused but required by tool signature
    try:
        client = _get_client()
        user = await asyncio.to_thread(client.current_user.me)
        return _success_response({
            "status": "healthy",
            "workspace_url": client.config.host,
            "user": user.user_name
        })
    except Exception as e:
        return _error_response(f"Connection failed: {e}")


@tool("list_jobs", "List jobs in Databricks workspace. Filter by name substring.", {"limit": int, "name_filter": str})
async def list_jobs(args: dict[str, Any]) -> dict[str, Any]:
    try:
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
        return _success_response({"jobs": jobs, "count": len(jobs)})
    except Exception as e:
        return _error_response(f"Failed to list jobs: {e}")


@tool("get_job", "Get detailed job configuration including tasks, clusters, and schedule.", {"job_id": int})
async def get_job(args: dict[str, Any]) -> dict[str, Any]:
    job_id = args.get("job_id")
    if job_id is None:
        return _error_response("job_id is required")

    try:
        client = _get_client()
        job = await asyncio.to_thread(client.jobs.get, job_id=job_id)

        tasks = [{
            "task_key": t.task_key,
            "type": "notebook" if t.notebook_task else "python" if t.python_wheel_task else "other",
            "path": t.notebook_task.notebook_path if t.notebook_task else None,
            "depends_on": [d.task_key for d in (t.depends_on or [])]
        } for t in (job.settings.tasks or [])]

        return _success_response({
            "job_id": job.job_id,
            "name": job.settings.name,
            "tasks": tasks,
            "max_concurrent_runs": job.settings.max_concurrent_runs
        })
    except Exception as e:
        return _error_response(f"Failed to get job: {e}")


@tool("run_job", "Execute a job. WARNING: May incur compute costs.", {"job_id": int, "notebook_params": dict})
async def run_job(args: dict[str, Any]) -> dict[str, Any]:
    job_id = args.get("job_id")
    if job_id is None:
        return _error_response("job_id is required")

    try:
        client = _get_client()
        params = args.get("notebook_params")

        run = await asyncio.to_thread(client.jobs.run_now, job_id=job_id, notebook_params=params)
        return _success_response({"run_id": run.run_id, "job_id": job_id, "status": "TRIGGERED"})
    except Exception as e:
        return _error_response(f"Failed to run job: {e}")


@tool("list_notebooks", "List notebooks in a workspace path. Optionally recursive.", {"path": str, "recursive": bool, "limit": int})
async def list_notebooks(args: dict[str, Any]) -> dict[str, Any]:
    try:
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
                    pass  # Skip inaccessible paths

            list_path(path)
            return notebooks

        notebooks = await asyncio.to_thread(_list_notebooks_sync)
        return _success_response({"notebooks": notebooks, "count": len(notebooks), "path": path})
    except Exception as e:
        return _error_response(f"Failed to list notebooks: {e}")


@tool("export_notebook", "Export notebook content. Formats: SOURCE, HTML, JUPYTER, DBC.", {"path": str, "format": str})
async def export_notebook(args: dict[str, Any]) -> dict[str, Any]:
    path = args.get("path")
    if not path:
        return _error_response("path is required")

    try:
        from databricks.sdk.service import workspace as ws

        client = _get_client()
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

        return _success_response({"path": path, "format": fmt, "content": decoded})
    except Exception as e:
        return _error_response(f"Failed to export notebook: {e}")


@tool("execute_dbsql", "Execute SQL on Databricks SQL warehouse. WARNING: Can run DDL/DML.", {"query": str, "warehouse_id": str})
async def execute_dbsql(args: dict[str, Any]) -> dict[str, Any]:
    query = args.get("query")
    if not query:
        return _error_response("query is required")

    try:
        client = _get_client()
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

        return _success_response({"query": query, "rows": rows, "row_count": len(rows)})
    except Exception as e:
        return _error_response(f"SQL execution failed: {e}")


@tool("list_warehouses", "List available SQL warehouses with status.", {"limit": int})
async def list_warehouses(args: dict[str, Any]) -> dict[str, Any]:
    try:
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
        return _success_response({"warehouses": warehouses, "count": len(warehouses)})
    except Exception as e:
        return _error_response(f"Failed to list warehouses: {e}")


@tool("list_dbfs_files", "List files and directories in DBFS path.", {"path": str, "limit": int})
async def list_dbfs_files(args: dict[str, Any]) -> dict[str, Any]:
    try:
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
        return _success_response({"files": files, "count": len(files), "path": path})
    except Exception as e:
        return _error_response(f"Failed to list DBFS: {e}")


@tool("get_cluster", "Get cluster configuration by ID for job cluster generation.", {"cluster_id": str})
async def get_cluster(args: dict[str, Any]) -> dict[str, Any]:
    cluster_id = args.get("cluster_id")
    if not cluster_id:
        return _error_response("cluster_id is required")

    try:
        client = _get_client()
        cluster = await asyncio.to_thread(client.clusters.get, cluster_id=cluster_id)

        return _success_response({
            "cluster_id": cluster.cluster_id,
            "name": cluster.cluster_name,
            "spark_version": cluster.spark_version,
            "node_type_id": cluster.node_type_id,
            "num_workers": cluster.num_workers,
            "state": cluster.state.value if cluster.state else None
        })
    except Exception as e:
        return _error_response(f"Failed to get cluster: {e}")


# =============================================================================
# DAB TOOLS
# =============================================================================

def _detect_file_type(path: str, content: str = "") -> str:
    """Detect file type from path and content."""
    # Check extension first
    if path.endswith(".sql"):
        return "sql"
    elif path.endswith(".py"):
        # Check for Databricks notebook markers
        if "# Databricks notebook source" in content or "# MAGIC" in content:
            if "# MAGIC %sql" in content:
                return "mixed_notebook"
            return "python_notebook"
        return "python"

    # Default notebook check
    if "# Databricks notebook source" in content or "# MAGIC" in content:
        if "# MAGIC %sql" in content or "-- COMMAND" in content:
            return "mixed_notebook"
        return "python_notebook"

    return "notebook"


async def _analyze_notebook_impl(notebook_path: str, skip_cache: bool = False) -> dict[str, Any]:
    """Internal implementation of notebook analysis.

    This is a non-decorated function that can be called directly by other tools.
    Uses the enhanced analysis module for comprehensive extraction.

    Args:
        notebook_path: Path to notebook (local or workspace)
        skip_cache: If True, bypass cache and run fresh analysis
    """
    path = notebook_path

    # Get content
    if os.path.exists(path):
        with open(path) as f:
            content = f.read()
    else:
        from databricks.sdk.service import workspace as ws

        client = _get_client()
        export = await asyncio.to_thread(
            client.workspace.export, path=path, format=ws.ExportFormat.SOURCE
        )
        content = base64.b64decode(export.content).decode("utf-8") if export.content else ""

    # Generate cache key
    cache_key = _get_cache_key(path, content)

    # Check cache (unless skip_cache)
    if not skip_cache:
        cached = _load_from_cache(cache_key)
        if cached:
            cached["cached"] = True
            return cached

    # Detect file type
    file_type = _detect_file_type(path, content)

    # Run enhanced analysis
    analysis = analyze_content(content, file_type)

    # Calculate complexity score
    complexity_score, complexity_factors = calculate_complexity_score(analysis)

    # Build result with backward-compatible fields + new enhanced fields
    content_lower = content.lower()
    dependencies = analysis.get("dependencies", {})
    features = analysis.get("databricks_features", {})

    result = {
        # Backward-compatible fields
        "path": path,
        "file_type": file_type,
        "libraries": dependencies.get("third_party", []) + dependencies.get("databricks", []),
        "widgets": [w["name"] for w in features.get("widgets", [])],
        "workflow_type": analysis.get("workflow_type", "etl"),
        "uses_spark": "spark" in content_lower or "pyspark" in str(dependencies),
        "uses_mlflow": "mlflow" in content_lower or "mlflow" in str(dependencies),
        "uses_dlt": "@dlt." in content or "import dlt" in content,
        # NEW: Enhanced fields
        "dependencies": dependencies,
        "data_sources": analysis.get("data_sources", {}),
        "databricks_features": features,
        "detection_confidence": analysis.get("detection_confidence", 0.5),
        "complexity_score": complexity_score,
        "complexity_factors": complexity_factors,
        # Cache metadata
        "cached": False,
        "cache_key": cache_key,
    }

    # Save to cache
    _save_to_cache(cache_key, result)

    return result


@tool("analyze_notebook", "Analyze notebook to extract libraries, parameters, and workflow patterns.", {"notebook_path": str, "skip_cache": bool})
async def analyze_notebook(args: dict[str, Any]) -> dict[str, Any]:
    notebook_path = args.get("notebook_path")
    if not notebook_path:
        return _error_response("notebook_path is required")

    skip_cache = args.get("skip_cache", False)

    try:
        result = await _analyze_notebook_impl(notebook_path, skip_cache=skip_cache)
        return _success_response(result)
    except Exception as e:
        return _error_response(f"Analysis failed: {e}")


@tool("generate_bundle", "Generate DAB context from file analysis. Returns patterns and recommendations.", {"bundle_name": str, "file_paths": list, "output_path": str})
async def generate_bundle(args: dict[str, Any]) -> dict[str, Any]:
    bundle_name = args.get("bundle_name")
    file_paths = args.get("file_paths")
    if not bundle_name:
        return _error_response("bundle_name is required")
    if not file_paths:
        return _error_response("file_paths is required")

    try:
        output_path = args.get("output_path") or f"./{bundle_name}"

        # Ensure file_paths is a list (handle string input)
        if isinstance(file_paths, str):
            file_paths = [file_paths]

        os.makedirs(output_path, exist_ok=True)

        # Analyze each file using internal implementation
        analyses = []
        for path in file_paths:
            try:
                result = await _analyze_notebook_impl(path)
                analyses.append(result)
            except Exception as e:
                analyses.append({"path": path, "error": str(e)})

        # Determine dominant workflow
        workflow_types = [a.get("workflow_type") for a in analyses if "workflow_type" in a]
        dominant = max(set(workflow_types), key=workflow_types.count) if workflow_types else "etl"

        return _success_response({
            "bundle_name": bundle_name,
            "output_path": output_path,
            "file_analyses": analyses,
            "dominant_workflow": dominant,
            "workspace_host": _get_client().config.host
        })
    except Exception as e:
        return _error_response(f"Bundle generation failed: {e}")


@tool("generate_bundle_from_job", "Generate DAB from existing Databricks job using CLI.", {"job_id": int, "output_dir": str})
async def generate_bundle_from_job(args: dict[str, Any]) -> dict[str, Any]:
    import tempfile

    job_id = args.get("job_id")
    if job_id is None:
        return _error_response("job_id is required")

    try:
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
            return _error_response(f"Bundle generation failed: {result.stderr or result.stdout}")

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

        return _success_response({
            "job_id": job_id,
            "job_name": job.settings.name,
            "bundle_dir": output_dir,
            "generated_files": generated_files,
            "bundle_content": bundle_content
        })
    except subprocess.TimeoutExpired:
        return _error_response("Bundle generation timed out after 30s")
    except Exception as e:
        return _error_response(f"Failed to generate bundle: {e}")


@tool("validate_bundle", "Validate DAB configuration using Databricks CLI.", {"bundle_path": str, "target": str})
async def validate_bundle(args: dict[str, Any]) -> dict[str, Any]:
    bundle_path = args.get("bundle_path")
    if not bundle_path:
        return _error_response("bundle_path is required")

    try:
        target = args.get("target", "dev")

        working_dir = bundle_path if os.path.isdir(bundle_path) else os.path.dirname(bundle_path)

        cmd = ["databricks", "bundle", "validate", "-t", target]
        profile = os.getenv("DATABRICKS_CONFIG_PROFILE")
        if profile:
            cmd.extend(["--profile", profile])

        result = await asyncio.to_thread(
            subprocess.run, cmd, cwd=working_dir, capture_output=True, text=True, timeout=60
        )

        return _success_response({
            "valid": result.returncode == 0,
            "bundle_path": bundle_path,
            "target": target,
            "output": result.stdout.strip() if result.stdout else result.stderr.strip()
        })
    except subprocess.TimeoutExpired:
        return _error_response("Validation timed out after 60s")
    except FileNotFoundError:
        return _error_response("Databricks CLI not found. Install with: pip install databricks-cli")
    except Exception as e:
        return _error_response(f"Validation failed: {e}")


# =============================================================================
# WORKSPACE TOOLS
# =============================================================================

@tool("upload_bundle", "Upload bundle YAML and README to Databricks workspace.", {"yaml_content": str, "bundle_name": str, "workspace_base": str})
async def upload_bundle(args: dict[str, Any]) -> dict[str, Any]:
    yaml_content = args.get("yaml_content")
    bundle_name = args.get("bundle_name")
    if not yaml_content:
        return _error_response("yaml_content is required")
    if not bundle_name:
        return _error_response("bundle_name is required")

    try:
        workspace_base = args.get("workspace_base")

        # Local mode check
        if os.getenv("USE_LOCAL_BUNDLE_STORAGE", "").lower() == "true":
            return _success_response({
                "mode": "local",
                "bundle_name": bundle_name,
                "suggested_path": f"generated_bundles/{bundle_name}"
            })

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
                    pass  # Skip if directory exists

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

        return _success_response({
            "bundle_path": bundle_path,
            "files_uploaded": [f"{bundle_path}/databricks.yml", f"{bundle_path}/README.md"],
            "next_steps": {
                "validate": f"databricks bundle validate --chdir {bundle_path}",
                "deploy": f"databricks bundle deploy -t dev --chdir {bundle_path}"
            }
        })
    except Exception as e:
        return _error_response(f"Failed to upload bundle: {e}")


@tool("run_bundle_command", "Run Databricks bundle CLI command. WARNING: deploy/run incur costs.", {"workspace_path": str, "command": str, "target": str, "profile": str})
async def run_bundle_command(args: dict[str, Any]) -> dict[str, Any]:
    workspace_path = args.get("workspace_path")
    if not workspace_path:
        return _error_response("workspace_path is required")

    try:
        command = args.get("command", "validate")
        target = args.get("target", "dev")
        profile = args.get("profile") or os.getenv("DATABRICKS_CONFIG_PROFILE", "DEFAULT")

        allowed = ["validate", "deploy", "run", "destroy", "summary"]
        if command not in allowed:
            return _error_response(f"Invalid command. Allowed: {', '.join(allowed)}")

        instructions = [
            f"# Sync bundle to local first:",
            f"databricks workspace export-dir {workspace_path} ./temp_bundle --profile {profile}",
            f"cd ./temp_bundle",
            f"databricks bundle {command} --profile {profile}" + (f" -t {target}" if command in ["deploy", "run"] else "")
        ]

        return _success_response({
            "command": command,
            "workspace_path": workspace_path,
            "target": target,
            "status": "guidance",
            "instructions": instructions,
            "note": "Bundle commands require local bundle access"
        })
    except Exception as e:
        return _error_response(f"Failed to run bundle command: {e}")


@tool("sync_workspace_to_local", "Sync files from Databricks workspace to local filesystem.", {"workspace_path": str, "local_path": str, "profile": str})
async def sync_workspace_to_local(args: dict[str, Any]) -> dict[str, Any]:
    workspace_path = args.get("workspace_path")
    local_path = args.get("local_path")
    if not workspace_path:
        return _error_response("workspace_path is required")
    if not local_path:
        return _error_response("local_path is required")

    try:
        profile = args.get("profile") or os.getenv("DATABRICKS_CONFIG_PROFILE", "DEFAULT")

        os.makedirs(local_path, exist_ok=True)

        cmd = ["databricks", "workspace", "export-dir", "--profile", profile, workspace_path, local_path]
        result = await asyncio.to_thread(
            subprocess.run, cmd, capture_output=True, text=True, timeout=30
        )

        if result.returncode != 0:
            return _error_response(f"Sync failed: {result.stderr or 'Unknown error'}")

        # List synced files
        synced = []
        for root, _, files in os.walk(local_path):
            for f in files:
                synced.append(os.path.relpath(os.path.join(root, f), local_path))

        return _success_response({
            "workspace_path": workspace_path,
            "local_path": local_path,
            "files_synced": synced,
            "count": len(synced),
            "next_steps": {
                "validate": f"cd {local_path} && databricks bundle validate",
                "deploy": f"cd {local_path} && databricks bundle deploy -t dev"
            }
        })
    except subprocess.TimeoutExpired:
        return _error_response("Sync timed out after 30s")
    except Exception as e:
        return _error_response(f"Failed to sync: {e}")


# =============================================================================
# APPS TOOLS
# =============================================================================

@tool("list_apps", "List Databricks Apps in workspace with status and URLs.", {"limit": int})
async def list_apps(args: dict[str, Any]) -> dict[str, Any]:
    """List all Databricks Apps in the workspace.

    Maps to: client.apps.list()
    """
    try:
        client = _get_client()
        limit = args.get("limit", 100)

        def _list_apps_sync():
            apps = []
            for app in client.apps.list():
                if len(apps) >= limit:
                    break
                apps.append({
                    "name": app.name,
                    "description": app.description,
                    "create_time": str(app.create_time) if app.create_time else None,
                    "creator": app.creator,
                    "url": app.url,
                    "pending_deployment": app.pending_deployment.deployment_id if app.pending_deployment else None,
                    "active_deployment": app.active_deployment.deployment_id if app.active_deployment else None,
                })
            return apps

        apps = await asyncio.to_thread(_list_apps_sync)
        return _success_response({"apps": apps, "count": len(apps)})
    except Exception as e:
        return _error_response(f"Failed to list apps: {e}")


@tool("get_app", "Get Databricks App details including config and bindings.", {"name": str})
async def get_app(args: dict[str, Any]) -> dict[str, Any]:
    """Get detailed information about a specific Databricks App.

    Maps to: client.apps.get(name="my-app")
    """
    name = args.get("name")
    if not name:
        return _error_response("name is required")

    try:
        client = _get_client()
        app = await asyncio.to_thread(client.apps.get, name=name)

        # Extract resource bindings if present
        resources = []
        if app.resources:
            for resource in app.resources:
                resources.append({
                    "name": resource.name,
                    "description": resource.description,
                    "job": {"id": resource.job.id, "permission": resource.job.permission} if resource.job else None,
                    "secret": {"key": resource.secret.key, "scope": resource.secret.scope, "permission": resource.secret.permission} if resource.secret else None,
                    "sql_warehouse": {"id": resource.sql_warehouse.id, "permission": resource.sql_warehouse.permission} if resource.sql_warehouse else None,
                    "serving_endpoint": {"name": resource.serving_endpoint.name, "permission": resource.serving_endpoint.permission} if resource.serving_endpoint else None,
                })

        return _success_response({
            "name": app.name,
            "description": app.description,
            "url": app.url,
            "creator": app.creator,
            "create_time": str(app.create_time) if app.create_time else None,
            "update_time": str(app.update_time) if app.update_time else None,
            "compute_status": app.compute_status.state.value if app.compute_status and app.compute_status.state else None,
            "resources": resources,
            "default_source_code_path": app.default_source_code_path,
            "active_deployment_id": app.active_deployment.deployment_id if app.active_deployment else None,
        })
    except Exception as e:
        return _error_response(f"Failed to get app: {e}")


@tool("get_app_deployment", "Get active deployment details for an app.", {"app_name": str, "deployment_id": str})
async def get_app_deployment(args: dict[str, Any]) -> dict[str, Any]:
    """Get deployment information for a Databricks App.

    Maps to: client.apps.get_deployment(app_name="my-app", deployment_id="...")
    """
    app_name = args.get("app_name")
    if not app_name:
        return _error_response("app_name is required")

    deployment_id = args.get("deployment_id")
    if not deployment_id:
        return _error_response("deployment_id is required")

    try:
        client = _get_client()
        deployment = await asyncio.to_thread(
            client.apps.get_deployment,
            app_name=app_name,
            deployment_id=deployment_id
        )

        return _success_response({
            "deployment_id": deployment.deployment_id,
            "source_code_path": deployment.source_code_path,
            "status": deployment.status.state.value if deployment.status and deployment.status.state else None,
            "status_message": deployment.status.message if deployment.status else None,
            "create_time": str(deployment.create_time) if deployment.create_time else None,
            "update_time": str(deployment.update_time) if deployment.update_time else None,
            "mode": deployment.mode.value if deployment.mode else None,
            "deployment_artifacts": {
                "source_code_path": deployment.deployment_artifacts.source_code_path if deployment.deployment_artifacts else None,
            } if deployment.deployment_artifacts else None,
        })
    except Exception as e:
        return _error_response(f"Failed to get app deployment: {e}")


@tool("get_app_environment", "Get app runtime environment config.", {"name": str})
async def get_app_environment(args: dict[str, Any]) -> dict[str, Any]:
    """Get runtime environment configuration for a Databricks App.

    Maps to: client.apps.get_environment(name="my-app")
    """
    name = args.get("name")
    if not name:
        return _error_response("name is required")

    try:
        client = _get_client()
        env = await asyncio.to_thread(client.apps.get_environment, name=name)

        # Extract environment variables (not secret values)
        env_vars = []
        if env.env:
            for e in env.env:
                env_vars.append({
                    "name": e.name,
                    "value": e.value,
                    "value_from": e.value_from.value if e.value_from else None,
                })

        return _success_response({
            "name": name,
            "env": env_vars,
        })
    except Exception as e:
        return _error_response(f"Failed to get app environment: {e}")


@tool("get_app_permissions", "Get app permissions and access control.", {"app_name": str})
async def get_app_permissions(args: dict[str, Any]) -> dict[str, Any]:
    """Get permission levels for a Databricks App.

    Maps to: client.apps.get_permission_levels(app_name="my-app")
    """
    app_name = args.get("app_name")
    if not app_name:
        return _error_response("app_name is required")

    try:
        client = _get_client()
        perms = await asyncio.to_thread(client.apps.get_permission_levels, app_name=app_name)

        permission_levels = []
        if perms.permission_levels:
            for level in perms.permission_levels:
                permission_levels.append({
                    "permission_level": level.permission_level.value if level.permission_level else None,
                    "description": level.description,
                })

        return _success_response({
            "app_name": app_name,
            "permission_levels": permission_levels,
        })
    except Exception as e:
        return _error_response(f"Failed to get app permissions: {e}")


# =============================================================================
# PIPELINE TOOLS
# =============================================================================

@tool("list_pipelines", "List DLT pipelines in workspace with status.", {"limit": int, "name_filter": str})
async def list_pipelines(args: dict[str, Any]) -> dict[str, Any]:
    """List all DLT (Delta Live Tables) pipelines in the workspace.

    Maps to: client.pipelines.list_pipelines()
    """
    try:
        client = _get_client()
        limit = args.get("limit", 100)
        name_filter = (args.get("name_filter") or "").lower()

        def _list_pipelines_sync():
            pipelines = []
            for p in client.pipelines.list_pipelines():
                if len(pipelines) >= limit:
                    break
                name = p.name or ""
                if not name_filter or name_filter in name.lower():
                    pipelines.append({
                        "pipeline_id": p.pipeline_id,
                        "name": name,
                        "state": p.state.value if p.state else None,
                        "creator_user_name": p.creator_user_name,
                        "cluster_id": p.cluster_id,
                    })
            return pipelines

        pipelines = await asyncio.to_thread(_list_pipelines_sync)
        return _success_response({"pipelines": pipelines, "count": len(pipelines)})
    except Exception as e:
        return _error_response(f"Failed to list pipelines: {e}")


@tool("get_pipeline", "Get DLT pipeline details including config and clusters.", {"pipeline_id": str})
async def get_pipeline(args: dict[str, Any]) -> dict[str, Any]:
    """Get detailed information about a specific DLT pipeline.

    Maps to: client.pipelines.get(pipeline_id="...")
    """
    pipeline_id = args.get("pipeline_id")
    if not pipeline_id:
        return _error_response("pipeline_id is required")

    try:
        client = _get_client()
        pipeline = await asyncio.to_thread(client.pipelines.get, pipeline_id=pipeline_id)

        # Extract libraries
        libraries = []
        if pipeline.spec and pipeline.spec.libraries:
            for lib in pipeline.spec.libraries:
                if lib.notebook:
                    libraries.append({"notebook": {"path": lib.notebook.path}})
                elif lib.file:
                    libraries.append({"file": {"path": lib.file.path}})
                elif lib.jar:
                    libraries.append({"jar": lib.jar})

        # Extract clusters
        clusters = []
        if pipeline.spec and pipeline.spec.clusters:
            for c in pipeline.spec.clusters:
                clusters.append({
                    "label": c.label,
                    "num_workers": c.num_workers,
                    "node_type_id": c.node_type_id,
                    "autoscale": {"min_workers": c.autoscale.min_workers, "max_workers": c.autoscale.max_workers} if c.autoscale else None,
                })

        return _success_response({
            "pipeline_id": pipeline.pipeline_id,
            "name": pipeline.name,
            "state": pipeline.state.value if pipeline.state else None,
            "creator_user_name": pipeline.creator_user_name,
            "target": pipeline.spec.target if pipeline.spec else None,
            "storage": pipeline.spec.storage if pipeline.spec else None,
            "catalog": pipeline.spec.catalog if pipeline.spec else None,
            "libraries": libraries,
            "clusters": clusters,
            "continuous": pipeline.spec.continuous if pipeline.spec else None,
            "development": pipeline.spec.development if pipeline.spec else None,
            "channel": pipeline.spec.channel if pipeline.spec else None,
        })
    except Exception as e:
        return _error_response(f"Failed to get pipeline: {e}")


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
    # Apps
    list_apps, get_app, get_app_deployment, get_app_environment, get_app_permissions,
    # Pipelines
    list_pipelines, get_pipeline,
]

# Tool categories for filtering
CORE_TOOLS = [health, list_jobs, get_job, run_job, list_notebooks, export_notebook,
              execute_dbsql, list_warehouses, list_dbfs_files, get_cluster]
DAB_TOOLS = [analyze_notebook, generate_bundle, generate_bundle_from_job, validate_bundle]
WORKSPACE_TOOLS = [upload_bundle, run_bundle_command, sync_workspace_to_local]
APP_TOOLS = [list_apps, get_app, get_app_deployment, get_app_environment, get_app_permissions]
PIPELINE_TOOLS = [list_pipelines, get_pipeline]

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
