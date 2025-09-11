"""
Simple Bundle Validation Service using Databricks CLI
Leverages 'databricks bundle validate' command for actual validation
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class BundleValidationService:
    """Service for validating Databricks Asset Bundles using CLI"""
    
    async def validate_bundle(
        self,
        bundle_path: str,
        target: str = "dev",
        check_best_practices: bool = True,
        check_security: bool = True
    ) -> Dict[str, Any]:
        """
        Validate a Databricks Asset Bundle using databricks bundle validate
        
        Args:
            bundle_path: Path to bundle directory or databricks.yml file
            target: Target environment to validate
            check_best_practices: Add basic best practice checks
            check_security: Add basic security checks
            
        Returns:
            Validation results from databricks CLI
        """
        try:
            # Resolve bundle directory
            bundle_dir = self._resolve_bundle_dir(bundle_path)
            if not bundle_dir.exists():
                return self._create_error_response(f"Bundle directory not found: {bundle_dir}")
            
            # Get the Databricks profile from environment
            profile = os.getenv("DATABRICKS_CONFIG_PROFILE", "")
            
            # Run databricks bundle validate
            cmd = ["databricks", "bundle", "validate", "--target", target]
            
            if profile:
                cmd.extend(["--profile", profile])
            
            logger.info(f"Running validation: {' '.join(cmd)} in {bundle_dir}")
            
            result = subprocess.run(
                cmd,
                cwd=str(bundle_dir),
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Parse the output
            validation_result = self._parse_validation_output(
                result.stdout,
                result.stderr,
                result.returncode
            )
            
            # Add bundle info
            validation_result["bundle_path"] = str(bundle_dir / "databricks.yml")
            validation_result["target_environment"] = target
            
            # If requested, add simple best practice and security checks
            if check_best_practices or check_security:
                config_path = bundle_dir / "databricks.yml"
                if config_path.exists():
                    extra_checks = self._run_additional_checks(
                        config_path,
                        target,
                        check_best_practices,
                        check_security
                    )
                    validation_result.update(extra_checks)
            
            # Generate recommendations based on results
            validation_result["recommendations"] = self._generate_recommendations(validation_result)
            
            logger.info(f"Validation completed. Passed: {validation_result['validation_passed']}")
            
            return validation_result
            
        except subprocess.TimeoutExpired:
            return self._create_error_response("Validation timeout - bundle validate took too long")
        except Exception as e:
            logger.error(f"Error during bundle validation: {e}", exc_info=True)
            return self._create_error_response(f"Validation failed: {str(e)}")
    
    def _resolve_bundle_dir(self, bundle_path: str) -> Path:
        """Resolve the bundle directory path"""
        path = Path(bundle_path)
        
        if path.is_file():
            # If it's a file, use its parent directory
            return path.parent
        else:
            # It's already a directory
            return path
    
    def _parse_validation_output(self, stdout: str, stderr: str, returncode: int) -> Dict[str, Any]:
        """Parse databricks bundle validate output"""
        
        errors = []
        warnings = []
        
        # Parse stderr for errors and warnings
        for line in stderr.split('\n'):
            line = line.strip()
            if line.startswith('Error:'):
                errors.append(line[6:].strip())
            elif line.startswith('Warning:'):
                warnings.append(line[8:].strip())
        
        # Check if validation passed (returncode 0 means success)
        validation_passed = (returncode == 0)
        
        # Extract bundle info from stdout if available
        bundle_info = {}
        if "Name:" in stdout:
            for line in stdout.split('\n'):
                if line.startswith("Name:"):
                    bundle_info["name"] = line.split(":", 1)[1].strip()
                elif line.startswith("Target:"):
                    bundle_info["target"] = line.split(":", 1)[1].strip()
                elif line.startswith("Host:"):
                    bundle_info["host"] = line.split(":", 1)[1].strip()
                elif line.startswith("User:"):
                    bundle_info["user"] = line.split(":", 1)[1].strip()
                elif line.startswith("Path:"):
                    bundle_info["path"] = line.split(":", 1)[1].strip()
        
        # If validation succeeded, check stdout for success message
        if "Validation OK!" in stdout:
            validation_passed = True
        
        return {
            "validation_passed": validation_passed,
            "validation_summary": {
                "total_errors": len(errors),
                "total_warnings": len(warnings),
                "cli_returncode": returncode
            },
            "errors": errors,
            "warnings": warnings,
            "bundle_info": bundle_info,
            "cli_output": {
                "stdout": stdout[-1000:] if len(stdout) > 1000 else stdout,  # Last 1000 chars
                "stderr": stderr[-1000:] if len(stderr) > 1000 else stderr
            }
        }
    
    def _run_additional_checks(
        self,
        config_path: Path,
        target: str,
        check_best_practices: bool,
        check_security: bool
    ) -> Dict[str, Any]:
        """Run simple additional checks on the configuration"""
        
        additional_results = {}
        
        try:
            with open(config_path, 'r') as f:
                content = f.read()
            
            if check_best_practices:
                # Very simple best practice checks
                suggestions = []
                score = 100
                
                # Check for basic issues
                if "autotermination_minutes" not in content:
                    suggestions.append("Consider adding autotermination_minutes to clusters")
                    score -= 10
                
                if target == "dev" and "spot" not in content.lower():
                    suggestions.append("Consider using spot instances in development")
                    score -= 5
                
                if "email_notifications" not in content:
                    suggestions.append("Consider adding email notifications for job status")
                    score -= 10
                
                additional_results["best_practices"] = {
                    "score": max(0, score),
                    "suggestions": suggestions
                }
            
            if check_security:
                # Very simple security checks
                issues = []
                
                # Check for obvious hardcoded secrets
                if "password:" in content.lower() and "${" not in content[content.lower().index("password:"):content.lower().index("password:")+50]:
                    issues.append("Potential hardcoded password detected")
                
                if "api_key:" in content.lower() and "${" not in content[content.lower().index("api_key:"):content.lower().index("api_key:")+50]:
                    issues.append("Potential hardcoded API key detected")
                
                additional_results["security_checks"] = {
                    "passed": len(issues) == 0,
                    "issues": issues
                }
        
        except Exception as e:
            logger.warning(f"Could not run additional checks: {e}")
        
        return additional_results
    
    def _generate_recommendations(self, validation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate recommendations based on validation results"""
        
        immediate_actions = []
        improvements = []
        next_steps = []
        
        # Check for errors
        if validation_result.get("errors"):
            immediate_actions.append("Fix validation errors before deployment")
            for error in validation_result["errors"][:3]:  # First 3 errors
                immediate_actions.append(f"- {error}")
        
        # Check for warnings
        if validation_result.get("warnings"):
            improvements.append("Review warnings for potential issues")
        
        # Check best practices if present
        if "best_practices" in validation_result:
            bp = validation_result["best_practices"]
            if bp.get("score", 100) < 80:
                improvements.append("Improve configuration based on best practices")
            for suggestion in bp.get("suggestions", [])[:3]:
                improvements.append(f"- {suggestion}")
        
        # Check security if present
        if "security_checks" in validation_result:
            sec = validation_result["security_checks"]
            if not sec.get("passed", True):
                immediate_actions.extend(sec.get("issues", []))
        
        # Next steps
        if validation_result.get("validation_passed"):
            next_steps.append("Bundle is ready for deployment")
            next_steps.append("Run 'databricks bundle deploy' to deploy")
        else:
            next_steps.append("Fix errors and re-validate")
            next_steps.append("Run 'databricks bundle validate' after fixes")
        
        return {
            "immediate_actions": immediate_actions,
            "improvements": improvements,
            "next_steps": next_steps
        }
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create a standardized error response"""
        return {
            "validation_passed": False,
            "validation_summary": {
                "total_errors": 1,
                "total_warnings": 0
            },
            "errors": [error_message],
            "warnings": [],
            "best_practices": {"score": 0, "suggestions": []},
            "security_checks": {"passed": False, "issues": [error_message]},
            "recommendations": {
                "immediate_actions": [error_message],
                "improvements": [],
                "next_steps": ["Fix the error and try again"]
            }
        }