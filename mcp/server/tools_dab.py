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
    analysis_results: Optional[dict] = types.Field(default=None, description="Results from analyze_notebook tool (JSON object)"),
    notebook_paths: Optional[list[str]] = types.Field(default=None, description="List of notebook paths to analyze and include"),
    target_environment: str = types.Field(default="dev", description="Target environment (dev/staging/prod)"),
    output_path: Optional[str] = types.Field(default=None, description="Where to save bundle files (defaults to temp directory)")
) -> str:
    """
    Generate a Databricks Asset Bundle using Claude's intelligence and DAB patterns.
    
    This tool leverages Claude Code's understanding of DAB patterns from context files to generate
    appropriate configurations. It uses notebook analysis results to determine the best pattern
    and configuration for the specific workflow.
    
    Context files referenced:
    - /context/DAB_PATTERNS.md - Common bundle patterns and selection guidelines
    - /context/CLUSTER_CONFIGS.md - Cluster sizing and configuration guidelines  
    - /context/BEST_PRACTICES.md - DAB best practices and security guidelines
    
    The tool prepares comprehensive context for Claude to generate the optimal YAML configuration.
    """
    try:
        if not workspace_client:
            return create_error_response("Databricks client not initialized")
        
        # If analysis_results not provided, analyze the notebooks
        combined_analysis = analysis_results or {}
        
        if notebook_paths and not analysis_results:
            logger.info(f"Analysis not provided, analyzing {len(notebook_paths)} notebooks")
            combined_analysis = {
                "analyzed_notebooks": [],
                "combined_patterns": {},
                "combined_dependencies": {},
                "combined_data_sources": {}
            }
            
            # Analyze each notebook
            for notebook_path in notebook_paths:
                try:
                    # Call analyze_notebook for each path
                    analysis_result = analysis_service.analyze_file(
                        file_path=notebook_path,
                        content=None,  # Will be fetched by the service
                        file_type=None,
                        include_dependencies=True,
                        include_data_sources=True,
                        detect_patterns=True
                    )
                    combined_analysis["analyzed_notebooks"].append({
                        "path": notebook_path,
                        "analysis": analysis_result
                    })
                except Exception as e:
                    logger.warning(f"Failed to analyze {notebook_path}: {e}")
        
        # Determine output directory - ensure we have a string value
        if output_path is not None:
            bundle_dir = str(output_path)
        else:
            bundle_dir = f"/tmp/generated_bundles/{str(bundle_name).replace(' ', '_').lower()}"
        
        os.makedirs(bundle_dir, exist_ok=True)
        
        # Prepare comprehensive context for Claude Code generation
        generation_context = {
            "bundle_name": bundle_name,
            "target_environment": target_environment,
            "bundle_directory": bundle_dir,
            "analysis_data": combined_analysis,
            "request_type": "databricks_asset_bundle_generation",
            
            # Pattern selection guidance
            "pattern_selection_guidance": {
                "simple_etl": "Use for single notebook or simple pipelines with basic dependencies",
                "multi_stage_etl": "Use for multiple notebooks with clear ETL stages and dependencies",
                "ml_pipeline": "Use when MLflow imports detected or model training workflow identified",
                "streaming_job": "Use for real-time processing or streaming operations detected",
                "complex_multi_resource": "Use for multiple resource types or complex dependencies"
            },
            
            # Context file references
            "context_files": {
                "patterns": "/mcp/context/DAB_PATTERNS.md",
                "cluster_configs": "/mcp/context/CLUSTER_CONFIGS.md", 
                "best_practices": "/mcp/context/BEST_PRACTICES.md"
            },
            
            # Generation instructions for Claude
            "generation_instructions": f"""
Generate a complete Databricks Asset Bundle YAML configuration based on the notebook analysis.

CONTEXT: Use the patterns and guidelines from the context files to create an appropriate bundle:

1. PATTERN SELECTION: Based on the analysis results, select and adapt the most appropriate pattern from DAB_PATTERNS.md:
   - Check workflow_type from analysis (ETL/ML/streaming/reporting)
   - Consider dependency complexity and data sources
   - Look for Databricks-specific features (MLflow, streaming, widgets)

2. CLUSTER CONFIGURATION: Use CLUSTER_CONFIGS.md guidelines to determine:
   - Node types based on workload type and data size
   - Spark configurations for the detected workflow
   - Environment-appropriate sizing (dev vs prod)

3. BEST PRACTICES: Apply BEST_PRACTICES.md guidelines for:
   - Proper naming conventions
   - Security and permissions setup
   - Environment-specific configurations
   - Error handling and monitoring

4. CUSTOMIZATION: Adapt the selected pattern based on analysis findings:
   - Include actual dependencies found in notebooks
   - Set up Unity Catalog resources for detected tables
   - Add appropriate parameters from widget analysis
   - Configure schedules based on workflow type

5. STRUCTURE: Create a complete bundle with:
   - bundle metadata with descriptive name
   - variables section with environment-specific settings
   - resources section with job definitions
   - targets section for dev/staging/prod environments
   - proper task dependencies and cluster configurations

OUTPUT: Generate a complete, valid databricks.yml file that can be deployed immediately.
The configuration should be production-ready and follow all best practices.

Bundle Name: {bundle_name}
Target Environment: {target_environment}
Analysis Summary: {str(combined_analysis)[:500]}...
""",
            
            # Ready status
            "status": "ready_for_generation",
            "next_steps": [
                "Claude will analyze the notebook results and context files",
                "Select the most appropriate DAB pattern", 
                "Generate customized databricks.yml configuration",
                "Save the generated bundle to the specified directory",
                "Validate the configuration if Databricks CLI is available"
            ]
        }
        
        logger.info(f"Prepared generation context for bundle '{bundle_name}' in {bundle_dir}")
        
        # Convert the generation context to ensure JSON serialization
        serializable_context = {
            "bundle_name": generation_context["bundle_name"],
            "target_environment": generation_context["target_environment"], 
            "bundle_directory": generation_context["bundle_directory"],
            "request_type": generation_context["request_type"],
            "pattern_selection_guidance": generation_context["pattern_selection_guidance"],
            "context_files": generation_context["context_files"],
            "generation_instructions": generation_context["generation_instructions"],
            "status": generation_context["status"],
            "next_steps": generation_context["next_steps"],
            "analysis_summary": str(combined_analysis)[:1000] + "..." if combined_analysis else "No analysis provided"
        }
        
        return create_success_response({
            "bundle_generation_context": serializable_context,
            "message": f"Context prepared for Claude Code to generate DAB. The analysis data and patterns are ready for intelligent YAML generation.",
            "instructions_for_claude": "Please generate a complete Databricks Asset Bundle YAML based on the analysis results and context patterns provided. Use the pattern selection guidance and best practices to create an optimal configuration."
        })
        
    except Exception as e:
        logger.error(f"Error in generate_bundle: {e}", exc_info=True)
        return create_error_response(f"Bundle generation preparation failed: {str(e)}")


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