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
# Import shared utilities from tools.py
from tools import mcp, create_success_response, create_error_response, workspace_client as shared_workspace_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize services
analysis_service = NotebookAnalysisService()

# Use the shared workspace client from tools.py instead of creating a duplicate
workspace_client = shared_workspace_client


@mcp.tool()
async def analyze_notebook(
    notebook_path: str = types.Field(description="Path to notebook or file in Databricks workspace or local filesystem"),
    include_dependencies: bool = types.Field(default=True, description="Extract imports, libraries, and notebook dependencies"),
    include_data_sources: bool = types.Field(default=True, description="Extract table references and file paths"),
    detect_patterns: bool = types.Field(default=True, description="Identify workflow patterns (ETL/ML/reporting)")
) -> str:
    """
    Analyze a Databricks notebook or Python/SQL file to extract patterns, dependencies, 
    and generate DAB configuration recommendations. Supports .py files, .sql files, 
    and Databricks notebooks with magic commands.
    
    Returns detailed analysis including:
    - Databricks-specific features (widgets, spark operations, MLflow)
    - Dependencies (Python imports, notebook calls)
    - Data sources (Unity Catalog tables, DBFS paths)
    - Workflow patterns (ETL, ML, reporting)
    - DAB configuration recommendations
    """
    try:
        if not workspace_client:
            return create_error_response("Databricks client not initialized. Check connection settings.")
        
        logger.info(f"Analyzing notebook/file: {notebook_path}")
        
        # Determine if path is local or workspace
        is_local = os.path.exists(notebook_path)
        
        if is_local:
            # Read local file
            logger.info(f"Reading local file: {notebook_path}")
            with open(notebook_path, 'r') as f:
                content = f.read()
            file_path = notebook_path
        else:
            # Export from Databricks workspace
            logger.info(f"Exporting notebook from workspace: {notebook_path}")
            try:
                notebook_export = workspace_client.workspace.export(
                    path=notebook_path,
                    format=workspace.ExportFormat.SOURCE
                )
                
                if not notebook_export or not notebook_export.content:
                    return create_error_response(f"Notebook not found or empty: {notebook_path}")
                
                # Decode base64 content
                import base64
                content = base64.b64decode(notebook_export.content).decode('utf-8')
                file_path = notebook_path
                
            except Exception as e:
                logger.error(f"Failed to export notebook: {e}")
                return create_error_response(f"Could not export notebook: {str(e)}")
        
        # Analyze the content
        logger.info(f"Performing analysis with deps={include_dependencies}, data={include_data_sources}, patterns={detect_patterns}")
        
        analysis_result = analysis_service.analyze_file(
            file_path=file_path,
            content=content,
            file_type=None,  # Auto-detect
            include_dependencies=include_dependencies,
            include_data_sources=include_data_sources,
            detect_patterns=detect_patterns
        )
        
        # Format the response
        response = {
            "notebook_info": analysis_result.get("file_info", {}),
            "databricks_features": analysis_result.get("databricks_features", {}),
            "dependencies": analysis_result.get("dependencies", {}),
            "data_sources": analysis_result.get("data_sources", {}),
            "patterns": analysis_result.get("patterns", {}),
            "parameters": analysis_result.get("parameters", {}),
            "recommendations": analysis_result.get("recommendations", {}),
            "analysis_summary": _generate_analysis_summary(analysis_result)
        }
        
        logger.info(f"Analysis completed successfully for: {notebook_path}")
        return create_success_response(response)
        
    except Exception as e:
        logger.error(f"Error in analyze_notebook: {e}", exc_info=True)
        return create_error_response(f"Analysis failed: {str(e)}")


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


@mcp.tool()
async def generate_bundle(
    bundle_name: str = types.Field(description="Name for the Databricks Asset Bundle"),
    resources: list[str] = types.Field(description="List of notebook/job paths to include in bundle"),
    target_environment: str = types.Field(default="dev", description="Target environment (dev/staging/prod)"),
    include_tests: bool = types.Field(default=False, description="Generate test configurations"),
    output_path: Optional[str] = types.Field(default=None, description="Optional: Where to save bundle files locally")
) -> str:
    """
    Generate a complete Databricks Asset Bundle configuration from analyzed resources.
    Creates databricks.yml and resource definitions based on notebook analysis.
    
    This tool will:
    1. Analyze each resource if not already analyzed
    2. Generate appropriate job/pipeline configurations
    3. Create databricks.yml with targets and resources
    4. Optionally generate test configurations
    5. Return bundle configuration or save to specified path
    """
    try:
        # Placeholder for generate_bundle implementation
        # This will be implemented after analyze_notebook is tested
        return create_error_response("generate_bundle tool is not yet implemented. Coming in next iteration.")
        
    except Exception as e:
        logger.error(f"Error in generate_bundle: {e}")
        return create_error_response(f"Bundle generation failed: {str(e)}")


@mcp.tool()
async def validate_bundle(
    bundle_path: str = types.Field(description="Path to bundle root directory or databricks.yml file"),
    target: str = types.Field(default="dev", description="Target environment to validate"),
    check_best_practices: bool = types.Field(default=True, description="Apply best practice validation rules"),
    check_security: bool = types.Field(default=True, description="Perform security policy validation")
) -> str:
    """
    Validate a Databricks Asset Bundle configuration for correctness and best practices.
    
    Performs checks including:
    - YAML schema validation
    - Resource reference validation
    - Best practice compliance
    - Security policy checks
    - Target configuration validation
    """
    try:
        # Placeholder for validate_bundle implementation
        return create_error_response("validate_bundle tool is not yet implemented. Coming in next iteration.")
        
    except Exception as e:
        logger.error(f"Error in validate_bundle: {e}")
        return create_error_response(f"Bundle validation failed: {str(e)}")


@mcp.tool()
async def create_tests(
    resource_type: str = types.Field(description="Type of resource to test (notebook/job/pipeline)"),
    resource_path: str = types.Field(description="Path to the resource"),
    test_framework: str = types.Field(default="pytest", description="Testing framework (pytest/unittest)"),
    include_mocks: bool = types.Field(default=True, description="Generate mock configurations"),
    include_fixtures: bool = types.Field(default=False, description="Create test data fixtures")
) -> str:
    """
    Generate unit and integration test scaffolds for Databricks resources.
    
    Creates test files including:
    - Unit test templates
    - Mock Spark session and dbutils
    - Test fixtures and sample data
    - Integration test scenarios
    """
    try:
        # Placeholder for create_tests implementation
        return create_error_response("create_tests tool is not yet implemented. Coming in next iteration.")
        
    except Exception as e:
        logger.error(f"Error in create_tests: {e}")
        return create_error_response(f"Test creation failed: {str(e)}")


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