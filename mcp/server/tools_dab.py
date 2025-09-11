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
from tools import mcp, create_success_response, create_error_response, workspace_client as shared_workspace_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize services
analysis_service = NotebookAnalysisService()
validation_service = BundleValidationService()

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
        
        # Load all context files for Claude
        logger.info("Loading DAB context files for generation")
        context_content = _load_all_context_files()
        
        # If analysis_results not provided, analyze the notebooks
        # Handle case where analysis_results might be a FieldInfo object
        if analysis_results is None or hasattr(analysis_results, 'default'):
            combined_analysis = {}
        elif isinstance(analysis_results, dict):
            combined_analysis = analysis_results
        else:
            combined_analysis = {}
        
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
            
            # Include full context content for Claude (loaded from files)
            "dab_patterns_content": context_content.get("dab_patterns", ""),
            "cluster_configs_content": context_content.get("cluster_configs", ""),
            "best_practices_content": context_content.get("best_practices", ""),
            
            # Generation instructions for Claude with complete context
            "generation_instructions": f"""
Generate a complete Databricks Asset Bundle YAML configuration based on the notebook analysis and the comprehensive context provided.

COMPLETE CONTEXT PROVIDED:
- DAB patterns, cluster configurations, and best practices are included in this response
- Use the dab_patterns_content, cluster_configs_content, and best_practices_content fields
- All context is loaded directly from the documentation files

GENERATION PROCESS:

1. PATTERN SELECTION: Review the DAB patterns content and select the most appropriate pattern based on:
   - Workflow type from analysis: {combined_analysis.get('patterns', {}).get('workflow_type', 'unknown')}
   - Dependency complexity and data sources
   - Detected Databricks features (MLflow, streaming, widgets)

2. CLUSTER CONFIGURATION: Use cluster configs content to determine:
   - Node types appropriate for the workload size and complexity
   - Spark configurations optimized for the detected workflow
   - Environment-specific sizing ({target_environment} environment)

3. BEST PRACTICES: Apply all best practices from the content including:
   - Proper naming conventions for all resources
   - Security and permissions configuration
   - Environment-specific settings and variables
   - Monitoring, error handling, and retry policies

4. CUSTOMIZATION: Adapt based on analysis findings:
   - Include dependencies: {list(combined_analysis.get('dependencies', {}).keys()) if combined_analysis else 'None provided'}
   - Configure data sources: {list(combined_analysis.get('data_sources', {}).keys()) if combined_analysis else 'None provided'}
   - Add detected parameters and widgets
   - Set appropriate scheduling based on workflow type

OUTPUT REQUIREMENTS:
- Complete, valid databricks.yml that can be deployed immediately
- Production-ready configuration following all best practices
- Properly structured with bundle, variables, resources, and targets sections
- Environment-appropriate configurations for: {target_environment}

Bundle Name: {bundle_name}
Target Environment: {target_environment}
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
            "generation_instructions": generation_context["generation_instructions"],
            "status": generation_context["status"],
            "next_steps": generation_context["next_steps"],
            "analysis_summary": str(combined_analysis)[:1000] + "..." if combined_analysis else "No analysis provided",
            
            # Include full context content for Claude
            "dab_patterns_content": generation_context["dab_patterns_content"],
            "cluster_configs_content": generation_context["cluster_configs_content"], 
            "best_practices_content": generation_context["best_practices_content"]
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
    
    Performs comprehensive validation including:
    - YAML schema validation against DAB requirements
    - Resource reference validation (jobs, clusters, notebooks)
    - Best practice compliance using established guidelines
    - Security policy checks for production readiness
    - Target-specific configuration validation
    - Naming convention validation
    
    Returns detailed validation results with errors, warnings, and actionable suggestions
    for improving the bundle configuration.
    """
    try:
        logger.info(f"Validating bundle at: {bundle_path} for target: {target}")
        
        # Use validation service to perform comprehensive checks
        validation_result = await validation_service.validate_bundle(
            bundle_path=bundle_path,
            target=target,
            check_best_practices=check_best_practices,
            check_security=check_security
        )
        
        # Enhanced response formatting
        response = {
            "validation_passed": validation_result["validation_passed"],
            "bundle_path": validation_result.get("config_path", bundle_path),
            "target_environment": validation_result.get("target", target),
            "validation_summary": {
                "total_errors": len(validation_result.get("errors", [])),
                "total_warnings": len(validation_result.get("warnings", [])),
                "best_practices_score": validation_result.get("best_practices", {}).get("score", 0),
                "security_passed": validation_result.get("security_checks", {}).get("passed", False)
            },
            "errors": validation_result.get("errors", []),
            "warnings": validation_result.get("warnings", []),
            "best_practices": validation_result.get("best_practices", {}),
            "security_checks": validation_result.get("security_checks", {}),
            "recommendations": _generate_validation_recommendations(validation_result)
        }
        
        if response["validation_passed"]:
            logger.info(f"Bundle validation passed for {bundle_path}")
        else:
            logger.warning(f"Bundle validation failed with {len(response['errors'])} errors")
        
        return create_success_response(response)
        
    except Exception as e:
        logger.error(f"Error in validate_bundle: {e}", exc_info=True)
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