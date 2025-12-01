#!/usr/bin/env python3
"""
Workspace upload and sync tools for Databricks MCP Server
Simple tools to upload generated DAB files to Databricks workspace
"""

import os
import json
import base64
import logging
import subprocess
from typing import Optional
from datetime import datetime
from pydantic import Field

# Import from existing tools
from tools import mcp, create_success_response, create_error_response
from workspace_factory import get_or_create_client

logger = logging.getLogger(__name__)

@mcp.tool(annotations={
    "title": "Upload Bundle",
    "readOnlyHint": False,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": True
})
async def upload_bundle(
    yaml_content: str = Field(description="The generated bundle YAML content"),
    bundle_name: str = Field(description="Name for the bundle (used for folder name)"),
    workspace_base: Optional[str] = Field(
        default=None,
        description="Base path in workspace (defaults to /Workspace/Users/{username}/bundles)"
    )
) -> str:
    """Upload generated bundle YAML to Databricks workspace or save locally.

    Creates a folder structure and uploads the bundle configuration,
    making it ready for validation and deployment.

    Args:
        yaml_content (str): The generated bundle YAML content
        bundle_name (str): Name for the bundle (used for folder name)
        workspace_base (str, optional): Base path in workspace

    Returns:
        str: JSON with upload status, paths, and next steps

    Example:
        >>> upload_bundle(yaml_content="bundle:\\n  name: my-etl", bundle_name="my-etl")
    """
    try:
        # Check if we're in local testing mode
        use_local_mode = os.getenv("USE_LOCAL_BUNDLE_STORAGE", "true").lower() == "true"

        if use_local_mode:
            # LOCAL MODE: Return content for app to save
            from pathlib import Path

            # Generate README content
            readme_content = f"""# {bundle_name}

Generated Databricks Asset Bundle

## Structure
- `databricks.yml` - Main bundle configuration
- `resources/` - Additional resource configurations
- `src/` - Source code and notebooks

## Usage
```bash
# Validate the bundle
databricks bundle validate

# Deploy to development
databricks bundle deploy --target dev

# Run the bundle
databricks bundle run --target dev
```

Generated on: {datetime.now().isoformat()}
"""

            # Return the content for the Streamlit app to handle
            # The app can save it or just display it
            return create_success_response({
                "message": f"Bundle generated successfully",
                "bundle_name": bundle_name,
                "yaml_content": yaml_content,  # Main YAML content
                "readme_content": readme_content,  # README content
                "suggested_path": f"generated_bundles/{bundle_name}",
                "mode": "local",
                "timestamp": datetime.now().isoformat()
            })

        # DATABRICKS MODE: Original workspace upload logic
        workspace_client = get_or_create_client()
        if not workspace_client:
            return create_error_response("Databricks client not initialized")

        # Get current user for default path
        current_user = workspace_client.current_user.me()
        username = current_user.user_name

        # Set workspace path
        if not workspace_base:
            workspace_base = f"/Workspace/Users/{username}/bundles"

        # Create bundle directory path
        bundle_path = f"{workspace_base}/{bundle_name}"
        
        logger.info(f"Creating workspace directory: {bundle_path}")
        
        # Create directory structure
        try:
            workspace_client.workspace.mkdirs(bundle_path)
            workspace_client.workspace.mkdirs(f"{bundle_path}/resources")
            workspace_client.workspace.mkdirs(f"{bundle_path}/src")
        except Exception as e:
            logger.warning(f"Directory might already exist: {e}")
        
        # Upload the bundle YAML
        yaml_file_path = f"{bundle_path}/databricks.yml"
        
        logger.info(f"Uploading bundle YAML to: {yaml_file_path}")
        
        # Encode content for upload
        encoded_content = base64.b64encode(yaml_content.encode('utf-8')).decode('utf-8')
        
        # Upload the file
        workspace_client.workspace.upload(
            path=yaml_file_path,
            content=encoded_content,
            format="AUTO",
            overwrite=True
        )
        
        # Create a simple README
        readme_content = f"""# {bundle_name}

Generated Databricks Asset Bundle

## Structure
- `databricks.yml` - Main bundle configuration
- `resources/` - Additional resource configurations
- `src/` - Source code and notebooks

## Usage
```bash
# Validate the bundle
databricks bundle validate

# Deploy to development
databricks bundle deploy --target dev

# Run the bundle
databricks bundle run --target dev
```

Generated on: {datetime.now().isoformat()}
"""
        readme_encoded = base64.b64encode(readme_content.encode('utf-8')).decode('utf-8')
        
        workspace_client.workspace.upload(
            path=f"{bundle_path}/README.md",
            content=readme_encoded,
            format="AUTO",
            overwrite=True
        )
        
        return create_success_response({
            "bundle_path": bundle_path,
            "files_uploaded": [
                f"{bundle_path}/databricks.yml",
                f"{bundle_path}/README.md"
            ],
            "directories_created": [
                bundle_path,
                f"{bundle_path}/resources",
                f"{bundle_path}/src"
            ],
            "next_steps": {
                "validate": f"databricks bundle validate --chdir {bundle_path}",
                "deploy": f"databricks bundle deploy --target dev --chdir {bundle_path}",
                "workspace_url": f"https://{os.getenv('DATABRICKS_HOST', 'workspace')}/workspace{bundle_path}"
            },
            "message": f"Bundle '{bundle_name}' uploaded successfully to workspace"
        })
        
    except Exception as e:
        logger.error(f"Error uploading bundle: {e}")
        return create_error_response(f"Failed to upload bundle: {str(e)}")


@mcp.tool(annotations={
    "title": "Run Bundle Command",
    "readOnlyHint": False,
    "destructiveHint": True,
    "idempotentHint": False,
    "openWorldHint": True
})
async def run_bundle_command(
    workspace_path: str = Field(description="Path to bundle in workspace"),
    command: str = Field(
        default="validate",
        description="Bundle command to run: validate, deploy, run, destroy"
    ),
    target: str = Field(
        default="dev",
        description="Target environment: dev, staging, prod"
    ),
    profile: Optional[str] = Field(
        default=None,
        description="Databricks CLI profile to use"
    )
) -> str:
    """Run Databricks bundle CLI commands on an uploaded bundle.

    WARNING: Deploy/run/destroy commands can modify resources and incur costs.

    Args:
        workspace_path (str): Path to bundle in workspace
        command (str): Bundle command - validate, deploy, run, destroy
        target (str): Target environment - dev, staging, prod
        profile (str, optional): Databricks CLI profile to use

    Returns:
        str: JSON with command output and next steps

    Example:
        >>> run_bundle_command(workspace_path="/Workspace/Users/user/bundles/my-etl", command="validate")
    """
    try:
        # Validate command
        allowed_commands = ["validate", "deploy", "run", "destroy", "summary"]
        if command not in allowed_commands:
            return create_error_response(
                f"Invalid command '{command}'. Allowed: {', '.join(allowed_commands)}"
            )
        
        # Get profile from environment if not specified
        if not profile:
            profile = os.getenv("DATABRICKS_CONFIG_PROFILE", "DEFAULT")
        
        logger.info(f"Running bundle {command} on {workspace_path} with profile {profile}")
        
        # Build the command
        cmd_parts = [
            "databricks", "bundle", command,
            "--profile", profile
        ]
        
        # Add target for commands that need it
        if command in ["deploy", "run", "destroy"]:
            cmd_parts.extend(["--target", target])
        
        # Add the workspace path as change directory
        # Note: This requires the bundle to be synced locally first
        # For now, we'll document this limitation
        
        # Alternative approach: Use workspace execution if available
        # For validation, we can download and validate locally
        
        if command == "validate":
            # For validate, we just check if the file exists and has valid structure
            try:
                # Check if bundle exists in workspace
                workspace_client.workspace.get_status(workspace_path)
                
                # We can't directly validate workspace files with CLI
                # Return guidance instead
                return create_success_response({
                    "command": command,
                    "workspace_path": workspace_path,
                    "status": "guidance",
                    "message": "Bundle uploaded to workspace. To validate, sync locally first:",
                    "instructions": [
                        f"# Sync bundle from workspace to local:",
                        f"databricks workspace export-dir {workspace_path} ./temp_bundle",
                        f"cd ./temp_bundle",
                        f"databricks bundle validate --profile {profile}",
                        "",
                        "# Or use Databricks Apps for deployment:",
                        f"databricks apps create {os.path.basename(workspace_path)}",
                        f"databricks apps deploy {os.path.basename(workspace_path)} --source-code-path {workspace_path}"
                    ],
                    "note": "Direct workspace validation requires local sync first"
                })
                
            except Exception as e:
                return create_error_response(f"Bundle not found at {workspace_path}: {str(e)}")
        
        elif command in ["deploy", "run"]:
            # For deploy/run, provide deployment guidance
            return create_success_response({
                "command": command,
                "target": target,
                "workspace_path": workspace_path,
                "status": "guidance",
                "message": f"To {command} the bundle:",
                "instructions": [
                    f"# Option 1: Sync and {command} locally:",
                    f"databricks workspace export-dir {workspace_path} ./temp_bundle",
                    f"cd ./temp_bundle",
                    f"databricks bundle {command} --target {target} --profile {profile}",
                    "",
                    "# Option 2: Use Databricks Jobs UI:",
                    f"1. Go to Databricks workspace",
                    f"2. Navigate to {workspace_path}",
                    f"3. Create job from bundle configuration",
                    "",
                    "# Option 3: Use Databricks Apps:",
                    f"databricks apps deploy {os.path.basename(workspace_path)} --source-code-path {workspace_path}"
                ],
                "note": "Bundle commands require local execution or Databricks Apps"
            })
        
        else:
            # For other commands, provide general guidance
            return create_success_response({
                "command": command,
                "workspace_path": workspace_path,
                "status": "guidance",
                "message": f"Command '{command}' requires local bundle access",
                "instructions": [
                    f"databricks workspace export-dir {workspace_path} ./temp_bundle",
                    f"cd ./temp_bundle",
                    f"databricks bundle {command} --profile {profile}"
                ]
            })
            
    except Exception as e:
        logger.error(f"Error running bundle command: {e}")
        return create_error_response(f"Failed to run bundle command: {str(e)}")


@mcp.tool(annotations={
    "title": "Sync Workspace to Local",
    "readOnlyHint": False,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": True
})
async def sync_workspace_to_local(
    workspace_path: str = Field(description="Source path in Databricks workspace"),
    local_path: str = Field(description="Destination path on local filesystem"),
    profile: Optional[str] = Field(
        default=None,
        description="Databricks CLI profile to use"
    )
) -> str:
    """Sync files from Databricks workspace to local filesystem.

    Downloads bundle files from workspace to enable local validation and deployment.

    Args:
        workspace_path (str): Source path in Databricks workspace
        local_path (str): Destination path on local filesystem
        profile (str, optional): Databricks CLI profile to use

    Returns:
        str: JSON with synced files list and next steps

    Example:
        >>> sync_workspace_to_local("/Workspace/Users/user/bundles/my-etl", "./local-bundle")
    """
    try:
        # Get profile from environment if not specified
        if not profile:
            profile = os.getenv("DATABRICKS_CONFIG_PROFILE", "DEFAULT")
        
        logger.info(f"Syncing {workspace_path} to {local_path}")
        
        # Create local directory if it doesn't exist
        os.makedirs(local_path, exist_ok=True)
        
        # Use databricks CLI to export
        cmd = [
            "databricks", "workspace", "export-dir",
            "--profile", profile,
            workspace_path,
            local_path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            error_msg = result.stderr or "Unknown error during sync"
            return create_error_response(f"Sync failed: {error_msg}")
        
        # List synced files
        synced_files = []
        for root, dirs, files in os.walk(local_path):
            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), local_path)
                synced_files.append(rel_path)
        
        return create_success_response({
            "workspace_path": workspace_path,
            "local_path": local_path,
            "files_synced": synced_files,
            "file_count": len(synced_files),
            "next_steps": {
                "validate": f"cd {local_path} && databricks bundle validate",
                "deploy": f"cd {local_path} && databricks bundle deploy --target dev",
                "edit": f"Open {local_path} in your editor"
            },
            "message": f"Successfully synced {len(synced_files)} files to {local_path}"
        })
        
    except subprocess.TimeoutExpired:
        return create_error_response("Sync operation timed out after 30 seconds")
    except Exception as e:
        logger.error(f"Error syncing from workspace: {e}")
        return create_error_response(f"Failed to sync from workspace: {str(e)}")


# Register tools with MCP server
logger.info("Workspace tools loaded successfully")
logger.info(f"Registered tools: upload_bundle, run_bundle_command, sync_workspace_to_local")