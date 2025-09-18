#!/usr/bin/env python3
"""
Databricks MCP Tools - Following reference implementation pattern
Simple tool definitions with standardized error handling
"""

import os
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from fastmcp import FastMCP
from databricks.sdk import WorkspaceClient
from databricks.sdk.service import jobs, workspace
from pydantic import Field
from dotenv import load_dotenv

# Import the new factory
from workspace_factory import get_or_create_client

# Load environment variables
load_dotenv()

# Setup logging
logger = logging.getLogger(__name__)

# Create MCP server instance - this will be imported by app.py
mcp = FastMCP("databricks-mcp-server")

# For backward compatibility - other modules import workspace_client from here
# This will be lazy-initialized on first use
def get_workspace_client():
    """Get workspace client (for backward compatibility)"""
    return get_or_create_client()

# Expose as workspace_client for modules that import it
workspace_client = None  # Will be set by modules when needed

def create_success_response(data: Any) -> str:
    """Create standardized success response"""
    return json.dumps({
        "success": True,
        "data": data,
        "timestamp": datetime.now().isoformat()
    }, indent=2)

def create_error_response(error: str) -> str:
    """Create standardized error response"""
    return json.dumps({
        "success": False,
        "error": error,
        "timestamp": datetime.now().isoformat()
    }, indent=2)

@mcp.tool()
async def health() -> str:
    """Check server and Databricks connection health"""
    try:
        workspace_client = get_or_create_client()
        if not workspace_client:
            return create_error_response("Databricks client not initialized")
        
        # Test connection by getting current user
        current_user = workspace_client.current_user.me()
        
        health_data = {
            "server_status": "healthy",
            "databricks_connection": "connected",
            "workspace_url": workspace_client.config.host,
            "user": current_user.user_name,
            "timestamp": datetime.now().isoformat()
        }
        
        return create_success_response(health_data)
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return create_error_response(f"Health check failed: {str(e)}")

@mcp.tool()
async def list_jobs(
    limit: int = Field(default=100, description="Maximum number of jobs to return"),
    name_filter: Optional[str] = Field(default=None, description="Filter jobs by name containing this string")
) -> str:
    """List all jobs in the Databricks workspace"""
    try:
        workspace_client = get_or_create_client()
        if not workspace_client:
            return create_error_response("Databricks client not initialized")
        
        jobs_list = []
        count = 0
        
        for job in workspace_client.jobs.list():
            if count >= limit:
                break
            
            # Apply name filter if provided
            if name_filter and name_filter.lower() not in job.settings.name.lower():
                continue
            
            jobs_list.append({
                "job_id": job.job_id,
                "name": job.settings.name,
                "created_time": job.created_time,
                "creator_user_name": job.creator_user_name,
            })
            count += 1
        
        return create_success_response({
            "jobs": jobs_list,
            "count": len(jobs_list),
            "filters_applied": {"name_filter": name_filter} if name_filter else {}
        })
        
    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        return create_error_response(f"Failed to list jobs: {str(e)}")

@mcp.tool()
async def get_job(job_id: int = Field(description="The ID of the job to retrieve")) -> str:
    """Get detailed configuration for a specific job"""
    try:
        workspace_client = get_or_create_client()
        if not workspace_client:
            return create_error_response("Databricks client not initialized")
        
        job = workspace_client.jobs.get(job_id=job_id)
        
        job_config = {
            "job_id": job.job_id,
            "name": job.settings.name,
            "created_time": job.created_time,
            "creator_user_name": job.creator_user_name,
            "max_concurrent_runs": job.settings.max_concurrent_runs,
            "timeout_seconds": job.settings.timeout_seconds,
            "tasks": []
        }
        
        # Extract task information
        if job.settings.tasks:
            for task in job.settings.tasks:
                task_info = {
                    "task_key": task.task_key,
                    "depends_on": [dep.task_key for dep in task.depends_on] if task.depends_on else [],
                }
                
                # Add task type specific info
                if task.notebook_task:
                    task_info["type"] = "notebook"
                    task_info["notebook_path"] = task.notebook_task.notebook_path
                elif task.python_wheel_task:
                    task_info["type"] = "python_wheel"
                    task_info["package_name"] = task.python_wheel_task.package_name
                elif task.spark_python_task:
                    task_info["type"] = "spark_python"
                    task_info["python_file"] = task.spark_python_task.python_file
                
                job_config["tasks"].append(task_info)
        
        return create_success_response(job_config)
        
    except Exception as e:
        logger.error(f"Error getting job {job_id}: {e}")
        return create_error_response(f"Failed to get job {job_id}: {str(e)}")

@mcp.tool()
async def run_job(
    job_id: int = Field(description="The ID of the job to run"),
    notebook_params: Optional[Dict[str, str]] = Field(default=None, description="Parameters to pass to the job")
) -> str:
    """Execute a job in the Databricks workspace"""
    try:
        workspace_client = get_or_create_client()
        if not workspace_client:
            return create_error_response("Databricks client not initialized")
        
        run = workspace_client.jobs.run_now(
            job_id=job_id,
            notebook_params=notebook_params
        )
        
        return create_success_response({
            "run_id": run.run_id,
            "job_id": job_id,
            "status": "TRIGGERED",
            "message": f"Job {job_id} triggered successfully with run_id {run.run_id}",
        })
        
    except Exception as e:
        logger.error(f"Error running job {job_id}: {e}")
        return create_error_response(f"Failed to run job {job_id}: {str(e)}")

@mcp.tool()
async def list_notebooks(
    path: str = Field(default="/", description="The workspace path to list notebooks from"),
    recursive: bool = Field(default=False, description="Whether to recursively list notebooks in subdirectories")
) -> str:
    """List notebooks in a Databricks workspace path"""
    try:
        workspace_client = get_or_create_client()
        if not workspace_client:
            return create_error_response("Databricks client not initialized")
        
        notebooks = []
        
        def list_path(current_path: str, depth: int = 0):
            if not recursive and depth > 0:
                return
            
            try:
                objects = workspace_client.workspace.list(path=current_path)
                for obj in objects:
                    if obj.object_type == workspace.ObjectType.NOTEBOOK:
                        notebooks.append({
                            "path": obj.path,
                            "language": obj.language.value if obj.language else "UNKNOWN",
                            "size": getattr(obj, 'size', None),
                            "modified_at": getattr(obj, 'modified_at', None)
                        })
                    elif recursive and obj.object_type == workspace.ObjectType.DIRECTORY:
                        list_path(obj.path, depth + 1)
            except Exception as e:
                logger.warning(f"Could not list path {current_path}: {e}")
        
        list_path(path)
        
        return create_success_response({
            "notebooks": notebooks,
            "count": len(notebooks),
            "path": path,
            "recursive": recursive
        })
        
    except Exception as e:
        logger.error(f"Error listing notebooks at {path}: {e}")
        return create_error_response(f"Failed to list notebooks at {path}: {str(e)}")

@mcp.tool()
async def export_notebook(
    path: str = Field(description="The workspace path of the notebook to export"),
    format: str = Field(default="SOURCE", description="Export format: SOURCE, HTML, JUPYTER, DBC")
) -> str:
    """Export a notebook from the Databricks workspace"""
    try:
        workspace_client = get_or_create_client()
        if not workspace_client:
            return create_error_response("Databricks client not initialized")
        
        # Validate format
        valid_formats = ["SOURCE", "HTML", "JUPYTER", "DBC"]
        if format.upper() not in valid_formats:
            return create_error_response(f"Invalid format. Must be one of: {valid_formats}")
        
        # Export the notebook
        export_format = workspace.ExportFormat[format.upper()]
        content = workspace_client.workspace.export(
            path=path,
            format=export_format
        )
        
        # Decode content if it's base64 encoded
        import base64
        if export_format == workspace.ExportFormat.SOURCE:
            try:
                decoded_content = base64.b64decode(content.content).decode('utf-8')
            except:
                decoded_content = content.content
        else:
            decoded_content = content.content
        
        return create_success_response({
            "path": path,
            "format": format,
            "content": decoded_content
        })
        
    except Exception as e:
        logger.error(f"Error exporting notebook {path}: {e}")
        return create_error_response(f"Failed to export notebook {path}: {str(e)}")

# New tools following reference implementation pattern

@mcp.tool()
async def execute_dbsql(
    query: str = Field(description="SQL query to execute"),
    warehouse_id: Optional[str] = Field(default=None, description="SQL warehouse ID")
) -> str:
    """Execute SQL query on Databricks SQL warehouse"""
    try:
        workspace_client = get_or_create_client()
        if not workspace_client:
            return create_error_response("Databricks client not initialized")
        
        # Use provided warehouse_id or get from environment, or use serverless
        wh_id = warehouse_id or os.getenv("DATABRICKS_WAREHOUSE_ID") or os.getenv("DATABRICKS_SERVERLESS_COMPUTE_ID", "auto")
        if not wh_id:
            return create_error_response("No warehouse ID provided")
        
        # Execute SQL query
        result = workspace_client.statement_execution.execute_statement(
            warehouse_id=wh_id,
            statement=query,
            format="JSON_ARRAY"
        )
        
        # Parse results
        if result.result and result.result.data_array:
            rows = [dict(zip([col.name for col in result.manifest.schema.columns], row))
                   for row in result.result.data_array]
        else:
            rows = []
        
        return create_success_response({
            "query": query,
            "rows": rows,
            "row_count": len(rows),
            "warehouse_id": wh_id
        })
        
    except Exception as e:
        logger.error(f"Error executing SQL: {e}")
        return create_error_response(f"Failed to execute SQL query: {str(e)}")

@mcp.tool()
async def list_warehouses() -> str:
    """List available SQL warehouses"""
    try:
        workspace_client = get_or_create_client()
        if not workspace_client:
            return create_error_response("Databricks client not initialized")
        
        warehouses = []
        for warehouse in workspace_client.warehouses.list():
            warehouses.append({
                "warehouse_id": warehouse.id,
                "name": warehouse.name,
                "size": warehouse.cluster_size,
                "state": warehouse.state.value if warehouse.state else "UNKNOWN",
                "auto_stop_mins": warehouse.auto_stop_mins
            })
        
        return create_success_response({
            "warehouses": warehouses,
            "count": len(warehouses)
        })
        
    except Exception as e:
        logger.error(f"Error listing warehouses: {e}")
        return create_error_response(f"Failed to list warehouses: {str(e)}")

@mcp.tool()
async def list_dbfs_files(
    path: str = Field(default="/", description="DBFS path to list")
) -> str:
    """List files in Databricks File System"""
    try:
        workspace_client = get_or_create_client()
        if not workspace_client:
            return create_error_response("Databricks client not initialized")
        
        files = []
        try:
            for file_info in workspace_client.dbfs.list(path=path):
                files.append({
                    "path": file_info.path,
                    "is_dir": file_info.is_dir,
                    "file_size": file_info.file_size,
                })
        except Exception as e:
            return create_error_response(f"Failed to list DBFS path {path}: {str(e)}")
        
        return create_success_response({
            "files": files,
            "count": len(files),
            "path": path
        })
        
    except Exception as e:
        logger.error(f"Error listing DBFS files at {path}: {e}")
        return create_error_response(f"Failed to list DBFS files: {str(e)}")

@mcp.tool()
async def generate_bundle_from_job(
    job_id: int = Field(description="The ID of the job to generate a bundle from"),
    output_dir: Optional[str] = Field(default=None, description="Output directory for the generated bundle (defaults to current directory)")
) -> str:
    """Generate a Databricks Asset Bundle from an existing job using the native Databricks CLI command"""
    import subprocess
    import tempfile
    import os
    
    try:
        workspace_client = get_or_create_client()
        if not workspace_client:
            return create_error_response("Databricks client not initialized")
        
        # First verify the job exists
        try:
            job = workspace_client.jobs.get(job_id=job_id)
            job_name = job.settings.name
        except Exception as e:
            return create_error_response(f"Job {job_id} not found: {str(e)}")
        
        # Determine output directory
        if output_dir:
            bundle_dir = os.path.abspath(output_dir)
        else:
            bundle_dir = tempfile.mkdtemp(prefix=f"dab_{job_id}_")
        
        # Ensure directory exists
        os.makedirs(bundle_dir, exist_ok=True)
        
        # Run the databricks bundle generate command
        cmd = [
            "databricks", "bundle", "generate", "job",
            "--existing-job-id", str(job_id)
        ]
        
        # Add profile if configured
        profile = os.getenv("DATABRICKS_CONFIG_PROFILE")
        if profile:
            cmd.extend(["--profile", profile])
        
        logger.info(f"Running command: {' '.join(cmd)} in directory {bundle_dir}")
        
        result = subprocess.run(
            cmd,
            cwd=bundle_dir,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Unknown error"
            return create_error_response(f"Failed to generate bundle: {error_msg}")
        
        # Read the generated bundle.yml file
        bundle_yml_path = os.path.join(bundle_dir, "databricks.yml")
        if not os.path.exists(bundle_yml_path):
            # Try alternative paths
            bundle_yml_path = os.path.join(bundle_dir, "bundle.yml")
        
        bundle_content = None
        if os.path.exists(bundle_yml_path):
            with open(bundle_yml_path, 'r') as f:
                bundle_content = f.read()
        
        # List generated files
        generated_files = []
        for root, dirs, files in os.walk(bundle_dir):
            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), bundle_dir)
                generated_files.append(rel_path)
        
        return create_success_response({
            "job_id": job_id,
            "job_name": job_name,
            "bundle_dir": bundle_dir,
            "generated_files": generated_files,
            "bundle_content": bundle_content,
            "command_output": result.stdout,
            "message": f"Successfully generated DAB from job {job_id} in {bundle_dir}"
        })
        
    except subprocess.TimeoutExpired:
        return create_error_response("Bundle generation timed out after 30 seconds")
    except Exception as e:
        logger.error(f"Error generating bundle from job {job_id}: {e}")
        return create_error_response(f"Failed to generate bundle: {str(e)}")

@mcp.tool()
async def get_cluster(cluster_id: str = Field(description="The cluster ID to fetch configuration for")) -> str:
    """Get cluster configuration by ID for use in job cluster generation"""
    try:
        workspace_client = get_or_create_client()
        if not workspace_client:
            return create_error_response("Databricks client not initialized")
        
        # Get cluster info
        cluster = workspace_client.clusters.get(cluster_id=cluster_id)
        
        # Extract key configuration for job cluster generation
        config = {
            "cluster_id": cluster_id,
            "cluster_name": cluster.cluster_name,
            "spark_version": cluster.spark_version,
            "node_type_id": cluster.node_type_id,
            "driver_node_type_id": cluster.driver_node_type_id,
            "num_workers": cluster.num_workers,
            "autotermination_minutes": cluster.autotermination_minutes,
            "spark_conf": dict(cluster.spark_conf) if cluster.spark_conf else {},
            "spark_env_vars": dict(cluster.spark_env_vars) if cluster.spark_env_vars else {},
            "enable_elastic_disk": cluster.enable_elastic_disk,
            "disk_spec": cluster.disk_spec.dict() if cluster.disk_spec else None,
            "cluster_log_conf": cluster.cluster_log_conf.dict() if cluster.cluster_log_conf else None,
            "init_scripts": [script.dict() for script in cluster.init_scripts] if cluster.init_scripts else [],
            "custom_tags": dict(cluster.custom_tags) if cluster.custom_tags else {},
            "cluster_source": cluster.cluster_source.value if cluster.cluster_source else None,
            "state": cluster.state.value if cluster.state else None
        }
        
        # Generate job cluster YAML snippet for easy copy-paste
        job_cluster_yaml = f"""job_clusters:
  - job_cluster_key: main_cluster
    new_cluster:
      spark_version: "{cluster.spark_version}"
      node_type_id: "{cluster.node_type_id}"
      num_workers: {cluster.num_workers or 0}"""
        
        if cluster.autotermination_minutes:
            job_cluster_yaml += f"\n      autotermination_minutes: {cluster.autotermination_minutes}"
        
        if cluster.spark_conf:
            job_cluster_yaml += "\n      spark_conf:"
            for key, value in cluster.spark_conf.items():
                job_cluster_yaml += f'\n        {key}: "{value}"'
        
        return create_success_response({
            "cluster_config": config,
            "job_cluster_yaml": job_cluster_yaml,
            "message": f"Retrieved configuration for cluster {cluster_id} ({cluster.cluster_name})"
        })
        
    except Exception as e:
        logger.error(f"Error getting cluster {cluster_id}: {e}")
        return create_error_response(f"Failed to get cluster {cluster_id}: {str(e)}")

logger.info(f"Databricks MCP tools loaded successfully")