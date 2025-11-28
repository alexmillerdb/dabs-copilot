"""
DAB Generation Tools for MCP Server
Phase 2 implementation of Databricks Asset Bundle generation capabilities
"""

import json
import os
from typing import Optional
from datetime import datetime
import logging
from pathlib import Path

import mcp.types as types

from databricks.sdk import WorkspaceClient
from databricks.sdk.service import workspace

from services.analysis_service import NotebookAnalysisService
from services.validation_service import BundleValidationService
# Import shared utilities from tools.py
from tools import mcp, create_success_response, create_error_response
from workspace_factory import get_or_create_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize services
analysis_service = NotebookAnalysisService()
validation_service = BundleValidationService()


@mcp.tool(annotations={
    "title": "Analyze Notebook",
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": True
})
async def analyze_notebook(
    notebook_path: str = types.Field(description="Path to notebook or file in Databricks workspace or local filesystem")
) -> str:
    """
    Analyze a notebook/Python/SQL file to extract basic info needed for DAB generation.

    Args:
        notebook_path (str): Path to notebook in Databricks workspace or local filesystem

    Returns:
        str: JSON with schema:
        {
            "success": bool,
            "data": {
                "file_path": str,
                "file_type": "python" | "sql" | "notebook",
                "libraries": list[str],
                "workflow_type": "etl" | "ml" | "reporting",
                "widgets": list[str],
                "uses_spark": bool,
                "uses_mlflow": bool
            }
        }

    Example:
        >>> analyze_notebook("/Workspace/Users/user@example.com/etl/main.py")
    """
    try:
        logger.info(f"Analyzing file: {notebook_path}")
        
        # Get file content
        if os.path.exists(notebook_path):
            with open(notebook_path, 'r') as f:
                content = f.read()
        else:
            # Export from workspace
            workspace_client = get_or_create_client()
            if not workspace_client:
                return create_error_response("Databricks client not initialized")
            
            notebook_export = workspace_client.workspace.export(
                path=notebook_path,
                format=workspace.ExportFormat.SOURCE
            )
            
            if not notebook_export or not notebook_export.content:
                return create_error_response(f"File not found: {notebook_path}")
            
            import base64
            content = base64.b64decode(notebook_export.content).decode('utf-8')
        
        # Simple analysis - extract key info
        analysis = _simple_analyze(content, notebook_path)
        
        logger.info(f"Analysis completed for: {notebook_path}")
        return create_success_response(analysis)
        
    except Exception as e:
        logger.error(f"Error analyzing {notebook_path}: {e}")
        return create_error_response(f"Analysis failed: {str(e)}")


def _simple_analyze(content: str, file_path: str) -> dict:
    """Simple analysis to extract basics for DAB generation"""
    import re
    
    # Determine file type
    if file_path.endswith('.sql'):
        file_type = 'sql'
    elif file_path.endswith('.py') or 'python' in content.lower():
        file_type = 'python'
    else:
        file_type = 'notebook'
    
    # Extract Python imports/libraries
    libraries = []
    import_pattern = r'(?:from|import)\s+([a-zA-Z_][a-zA-Z0-9_]*)'
    imports = re.findall(import_pattern, content)
    
    # Filter to common data/ML libraries
    common_libs = ['pandas', 'numpy', 'sklearn', 'tensorflow', 'torch', 'mlflow', 
                   'pyspark', 'databricks', 'matplotlib', 'seaborn', 'scipy']
    
    for imp in imports:
        if imp in common_libs or any(lib in imp for lib in common_libs):
            if imp not in libraries:
                libraries.append(imp)
    
    # Detect workflow type (simple heuristics)
    workflow_type = 'etl'  # default
    if 'mlflow' in content.lower() or 'model' in content.lower():
        workflow_type = 'ml'
    elif 'display(' in content or 'plot' in content.lower():
        workflow_type = 'reporting'
    
    # Find widgets/parameters
    widgets = []
    widget_pattern = r'dbutils\.widgets\.\w+\(["\']([^"\']+)["\']'
    widget_matches = re.findall(widget_pattern, content)
    widgets.extend(widget_matches)
    
    return {
        "file_path": file_path,
        "file_type": file_type,
        "libraries": libraries,
        "workflow_type": workflow_type,
        "widgets": widgets,
        "uses_spark": 'spark' in content.lower(),
        "uses_mlflow": 'mlflow' in content.lower()
    }


def _generate_analysis_summary(analysis: dict) -> dict:
    """Generate a human-readable summary of the analysis"""
    summary = {
        "file_type": analysis.get("file_info", {}).get("type", "unknown"),
        "lines_of_code": len(analysis.get("file_info", {}).get("content", "").splitlines()) if "content" in analysis.get("file_info", {}) else "N/A",
        "workflow_type": analysis.get("patterns", {}).get("workflow_type", "unknown"),
        "uses_unity_catalog": bool(analysis.get("data_sources", {}).get("input_tables") or 
                                  analysis.get("data_sources", {}).get("output_tables")),
        "uses_mlflow": "mlflow" in str(analysis.get("databricks_features", {})),
        "has_parameters": bool(analysis.get("databricks_features", {}).get("widget_params")),
        "calls_other_notebooks": bool(analysis.get("databricks_features", {}).get("notebook_dependencies")),
        "recommended_job_type": analysis.get("recommendations", {}).get("job_type", "batch"),
        "recommended_cluster": analysis.get("recommendations", {}).get("cluster_config", {}).get("node_type_id", "i3.xlarge")
    }
    
    # Add dependency count
    deps = analysis.get("dependencies", {})
    total_deps = sum(len(v) if isinstance(v, list) else 0 for v in deps.values())
    summary["total_dependencies"] = total_deps
    
    # Add data source count
    sources = analysis.get("data_sources", {})
    total_sources = sum(len(v) if isinstance(v, list) else 0 for v in sources.values())
    summary["total_data_sources"] = total_sources
    
    return summary


def _load_context_file(file_path: Path) -> str:
    """Load a DAB context file and return its content"""
    try:
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            logger.debug(f"Loaded context file: {file_path} ({len(content)} chars)")
            return content
        else:
            logger.warning(f"Context file not found: {file_path}")
            return f"# Context file not found: {file_path}\nContext content not available."
    except Exception as e:
        logger.error(f"Error loading context file {file_path}: {e}")
        return f"# Error loading context file: {file_path}\nError: {str(e)}"


def _load_all_context_files() -> dict:
    """Load all DAB generation context files"""
    # Get context directory relative to this file
    context_dir = Path(__file__).parent.parent / "context"
    
    context_files = {
        "dab_patterns": "DAB_PATTERNS.md",
        "cluster_configs": "CLUSTER_CONFIGS.md",
        "best_practices": "BEST_PRACTICES.md"
    }
    
    context = {}
    for key, filename in context_files.items():
        file_path = context_dir / filename
        content = _load_context_file(file_path)
        context[key] = content
        
    logger.info(f"Loaded {len(context)} context files from {context_dir}")
    return context


def _generate_validation_recommendations(validation_result: dict) -> dict:
    """Generate actionable recommendations based on validation results"""
    recommendations = {
        "immediate_actions": [],
        "improvements": [],
        "next_steps": []
    }
    
    errors = validation_result.get("errors", [])
    warnings = validation_result.get("warnings", [])
    best_practices = validation_result.get("best_practices", {})
    security_checks = validation_result.get("security_checks", {})
    
    # Immediate actions for errors
    if errors:
        recommendations["immediate_actions"].extend([
            "Fix configuration errors before deployment",
            "Validate YAML syntax and required fields"
        ])
    
    # Improvements based on best practices score
    score = best_practices.get("score", 0)
    if score < 80:
        recommendations["improvements"].extend([
            "Review best practices suggestions to improve configuration quality",
            "Add missing monitoring and error handling configurations"
        ])
    
    if score < 60:
        recommendations["improvements"].append(
            "Consider significant refactoring to align with DAB best practices"
        )
    
    # Security improvements
    if not security_checks.get("passed", False):
        recommendations["immediate_actions"].extend([
            "Address security issues before deploying to production",
            "Review secret management and access control configurations"
        ])
    
    # Next steps based on validation state
    if validation_result.get("validation_passed", False):
        recommendations["next_steps"].extend([
            "Bundle is ready for deployment",
            "Run 'databricks bundle validate' to confirm with Databricks CLI",
            "Consider testing in development environment first"
        ])
    else:
        recommendations["next_steps"].extend([
            "Fix all errors listed in validation results", 
            "Re-run validation after making corrections",
            "Test bundle configuration with 'databricks bundle validate'"
        ])
    
    # Add warning-based recommendations
    if warnings:
        recommendations["improvements"].append(
            "Review warnings for potential optimizations and improvements"
        )
    
    return recommendations


@mcp.tool(annotations={
    "title": "Generate Bundle",
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": False
})
async def generate_bundle(
    bundle_name: str = types.Field(description="Name for the Databricks Asset Bundle"),
    file_paths: list[str] = types.Field(description="List of notebook/Python/SQL file paths to include"),
    output_path: Optional[str] = types.Field(default=None, description="Where to save bundle files (defaults to current directory)")
) -> str:
    """
    Prepare context for Claude Code to generate a Databricks Asset Bundle.

    This tool analyzes the provided files and loads DAB patterns from /mcp/context/
    to give Claude Code everything needed to intelligently generate a databricks.yml.

    Args:
        bundle_name (str): Name for the bundle (used in configuration)
        file_paths (list[str]): List of notebook/Python/SQL file paths to include
        output_path (str, optional): Where to save bundle files

    Returns:
        str: JSON with schema:
        {
            "success": bool,
            "data": {
                "bundle_name": str,
                "output_path": str,
                "file_analyses": list[dict],
                "context_files": dict,
                "workspace_host": str,
                "instructions": str
            }
        }

    Example:
        >>> generate_bundle("my-etl", ["/Workspace/Users/user/etl.py"])
    """
    try:
        logger.info(f"Preparing bundle generation context for '{bundle_name}' with {len(file_paths)} files")
        
        # Set output directory
        if output_path is None:
            output_path = f"./{bundle_name}"
        
        os.makedirs(output_path, exist_ok=True)
        
        # Analyze each file
        file_analyses = []
        for file_path in file_paths:
            try:
                analysis_result = await analyze_notebook(file_path)
                import json
                analysis = json.loads(analysis_result)
                
                if analysis.get("success"):
                    file_analyses.append({
                        "path": file_path,
                        "analysis": analysis["data"]
                    })
                else:
                    file_analyses.append({
                        "path": file_path,
                        "analysis": {"error": "Could not analyze file"}
                    })
            except Exception as e:
                logger.warning(f"Could not analyze {file_path}: {e}")
                file_analyses.append({
                    "path": file_path,
                    "analysis": {"error": str(e)}
                })
        
        # Load context files for Claude
        context_content = _load_all_context_files()
        
        # Prepare the response with everything Claude needs
        response = {
            "bundle_name": bundle_name,
            "output_path": output_path,
            "file_analyses": file_analyses,
            "context_files": {
                "dab_patterns": context_content.get("dab_patterns", ""),
                "cluster_configs": context_content.get("cluster_configs", ""),
                "best_practices": context_content.get("best_practices", "")
            },
            "workspace_host": get_or_create_client().config.host if get_or_create_client() else "https://your-workspace.cloud.databricks.com",
            "instructions": f"""
Please generate a complete databricks.yml file for the bundle '{bundle_name}' using the analysis and context provided.

ANALYSIS DATA:
{len(file_analyses)} files analyzed with dependencies, workflow types, and features detected.

CONTEXT PROVIDED:
- DAB patterns and templates from /mcp/context/DAB_PATTERNS.md
- Cluster configuration guidance from /mcp/context/CLUSTER_CONFIGS.md  
- Best practices from /mcp/context/BEST_PRACTICES.md

INSTRUCTIONS:
1. Use the file analyses to determine workflow type and dependencies
2. Select appropriate DAB pattern from the context
3. Configure cluster based on detected libraries and workflow
4. Create a complete, valid databricks.yml file
5. Save it to {output_path}/databricks.yml

The generated bundle should be production-ready and follow all best practices from the context files.
            """
        }
        
        logger.info(f"Context prepared for Claude Code generation of bundle '{bundle_name}'")
        return create_success_response(response)
        
    except Exception as e:
        logger.error(f"Error preparing bundle context: {e}", exc_info=True)
        return create_error_response(f"Bundle context preparation failed: {str(e)}")


@mcp.tool(annotations={
    "title": "Validate Bundle",
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": True
})
async def validate_bundle(
    bundle_path: str = types.Field(description="Path to bundle root directory or databricks.yml file"),
    target: str = types.Field(default="dev", description="Target environment to validate")
) -> str:
    """
    Validate a Databricks Asset Bundle using the native Databricks CLI.

    Runs 'databricks bundle validate' to check if the bundle configuration is valid.

    Args:
        bundle_path (str): Path to bundle root directory or databricks.yml file
        target (str): Target environment to validate (default: "dev")

    Returns:
        str: JSON with schema:
        {
            "success": bool,
            "data": {
                "validation_passed": bool,
                "bundle_path": str,
                "target_environment": str,
                "command": str,
                "stdout": str,
                "stderr": str | null,
                "return_code": int
            }
        }

    Example:
        >>> validate_bundle("./my-bundle", target="dev")
    """
    try:
        import subprocess
        import os
        
        logger.info(f"Validating bundle at: {bundle_path} for target: {target}")
        
        # Change to bundle directory if it's a directory, otherwise use parent directory
        if os.path.isdir(bundle_path):
            working_dir = bundle_path
        else:
            working_dir = os.path.dirname(bundle_path)
        
        # Run databricks bundle validate
        cmd = ["databricks", "bundle", "validate", "-t", target]
        
        # Get the configured profile from environment (no hardcoded default per MCP best practices)
        profile = os.getenv("DATABRICKS_CONFIG_PROFILE")
        if profile:
            cmd.extend(["--profile", profile])
        
        logger.info(f"Running command: {' '.join(cmd)} in {working_dir}")
        
        result = subprocess.run(
            cmd,
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Parse the result
        validation_passed = result.returncode == 0
        
        response = {
            "validation_passed": validation_passed,
            "bundle_path": bundle_path,
            "target_environment": target,
            "command": " ".join(cmd),
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip() if result.stderr else None,
            "return_code": result.returncode
        }
        
        if validation_passed:
            logger.info(f"Bundle validation passed for {bundle_path}")
        else:
            logger.warning(f"Bundle validation failed with return code {result.returncode}")
        
        return create_success_response(response)
        
    except subprocess.TimeoutExpired:
        return create_error_response("Bundle validation timed out after 60 seconds")
    except FileNotFoundError:
        return create_error_response("Databricks CLI not found. Please install databricks CLI.")
    except Exception as e:
        logger.error(f"Error in validate_bundle: {e}", exc_info=True)
        return create_error_response(f"Bundle validation failed: {str(e)}")


# Note: create_tests tool removed as it was not implemented
# Will be added back when fully functional per MCP Builder best practices


if __name__ == "__main__":
    # For testing the DAB tools independently
    import asyncio
    
    async def test_analyze():
        """Test the analyze_notebook tool"""
        result = await analyze_notebook(
            notebook_path="/Users/alex.miller/test_notebook.py",
            include_dependencies=True,
            include_data_sources=True,
            detect_patterns=True
        )
        print(json.dumps(json.loads(result), indent=2))
    
    # Run test if executed directly
    # asyncio.run(test_analyze())