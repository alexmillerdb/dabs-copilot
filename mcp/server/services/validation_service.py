"""
Bundle Validation Service for Databricks Asset Bundles
Provides comprehensive validation including schema, best practices, and security checks
"""

import yaml
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class BundleValidationService:
    """Service for validating Databricks Asset Bundle configurations"""
    
    def __init__(self):
        """Initialize the validation service with rule engines"""
        self.best_practices_rules = self._load_best_practices_rules()
        self.security_rules = self._load_security_rules()
        self.schema_requirements = self._load_schema_requirements()
    
    async def validate_bundle(
        self,
        bundle_path: str,
        target: str = "dev",
        check_best_practices: bool = True,
        check_security: bool = True
    ) -> Dict[str, Any]:
        """
        Validate a Databricks Asset Bundle configuration
        
        Args:
            bundle_path: Path to bundle directory or databricks.yml file
            target: Target environment to validate
            check_best_practices: Apply best practice validation rules
            check_security: Perform security policy validation
            
        Returns:
            Validation results with errors, warnings, and recommendations
        """
        try:
            # Resolve bundle configuration file
            config_path = self._resolve_config_path(bundle_path)
            if not config_path.exists():
                return {
                    "validation_passed": False,
                    "errors": [f"Bundle configuration not found at {config_path}"],
                    "warnings": [],
                    "best_practices": {"score": 0, "suggestions": []},
                    "security_checks": {"passed": False, "issues": ["Configuration file not found"]}
                }
            
            # Load and parse YAML
            bundle_config = self._load_yaml_config(config_path)
            if "error" in bundle_config:
                return {
                    "validation_passed": False,
                    "errors": [bundle_config["error"]],
                    "warnings": [],
                    "best_practices": {"score": 0, "suggestions": []},
                    "security_checks": {"passed": False, "issues": ["Invalid YAML configuration"]}
                }
            
            # Perform validation checks
            errors = []
            warnings = []
            
            # 1. Schema validation
            schema_errors = self._validate_schema(bundle_config, target)
            errors.extend(schema_errors)
            
            # 2. Best practices validation
            best_practices_result = {"score": 100, "suggestions": []}
            if check_best_practices:
                best_practices_result = self._validate_best_practices(bundle_config, target)
                warnings.extend([f"Best Practice: {s}" for s in best_practices_result["suggestions"]])
            
            # 3. Security validation
            security_result = {"passed": True, "issues": []}
            if check_security:
                security_result = self._validate_security(bundle_config, target)
                if not security_result["passed"]:
                    errors.extend([f"Security: {issue}" for issue in security_result["issues"]])
            
            # 4. Target-specific validation
            target_warnings = self._validate_target(bundle_config, target)
            warnings.extend(target_warnings)
            
            validation_passed = len(errors) == 0
            
            logger.info(f"Bundle validation completed. Passed: {validation_passed}, Errors: {len(errors)}, Warnings: {len(warnings)}")
            
            return {
                "validation_passed": validation_passed,
                "errors": errors,
                "warnings": warnings,
                "best_practices": best_practices_result,
                "security_checks": security_result,
                "config_path": str(config_path),
                "target": target
            }
            
        except Exception as e:
            logger.error(f"Error during bundle validation: {e}", exc_info=True)
            return {
                "validation_passed": False,
                "errors": [f"Validation failed: {str(e)}"],
                "warnings": [],
                "best_practices": {"score": 0, "suggestions": []},
                "security_checks": {"passed": False, "issues": ["Validation process failed"]}
            }
    
    def _resolve_config_path(self, bundle_path: str) -> Path:
        """Resolve the path to the databricks.yml file"""
        path = Path(bundle_path)
        
        if path.is_file() and path.name in ['databricks.yml', 'bundle.yml']:
            return path
        elif path.is_dir():
            # Look for databricks.yml in the directory
            for config_name in ['databricks.yml', 'bundle.yml']:
                config_path = path / config_name
                if config_path.exists():
                    return config_path
        
        # Default to databricks.yml in the provided path
        return path / 'databricks.yml' if path.is_dir() else path
    
    def _load_yaml_config(self, config_path: Path) -> Dict[str, Any]:
        """Load and parse YAML configuration file"""
        try:
            with open(config_path, 'r') as f:
                content = f.read()
                
            # Basic variable substitution for validation
            # Replace common variable patterns with placeholders
            content = re.sub(r'\$\{[^}]+\}', 'PLACEHOLDER', content)
            
            config = yaml.safe_load(content)
            return config
            
        except yaml.YAMLError as e:
            return {"error": f"YAML parsing error: {str(e)}"}
        except Exception as e:
            return {"error": f"Failed to read configuration: {str(e)}"}
    
    def _validate_schema(self, config: Dict[str, Any], target: str) -> List[str]:
        """Validate bundle schema against requirements"""
        errors = []
        
        # Check required top-level sections
        if not config.get("bundle"):
            errors.append("Missing required 'bundle' section")
        else:
            bundle = config["bundle"]
            if not bundle.get("name"):
                errors.append("Bundle name is required")
        
        # Check resources section exists
        if not config.get("resources") and not config.get("targets", {}).get(target, {}).get("resources"):
            errors.append("No resources defined in bundle or target configuration")
        
        # Validate targets if present
        if config.get("targets"):
            targets = config["targets"]
            if target not in targets:
                errors.append(f"Target '{target}' not defined in bundle configuration")
        
        # Check for common configuration issues
        resources = config.get("resources", {})
        if isinstance(resources, dict):
            # Validate jobs
            jobs = resources.get("jobs", {})
            for job_key, job_config in jobs.items():
                if not isinstance(job_config, dict):
                    errors.append(f"Job '{job_key}' configuration must be an object")
                    continue
                    
                if not job_config.get("name"):
                    errors.append(f"Job '{job_key}' missing required 'name' field")
                    
                # Check tasks
                tasks = job_config.get("tasks", [])
                if not tasks:
                    errors.append(f"Job '{job_key}' has no tasks defined")
                else:
                    for i, task in enumerate(tasks):
                        if not task.get("task_key"):
                            errors.append(f"Job '{job_key}' task {i} missing required 'task_key'")
        
        return errors
    
    def _validate_best_practices(self, config: Dict[str, Any], target: str) -> Dict[str, Any]:
        """Validate configuration against best practices"""
        score = 100
        suggestions = []
        
        bundle = config.get("bundle", {})
        resources = config.get("resources", {})
        
        # Check bundle naming
        bundle_name = bundle.get("name", "")
        if not bundle_name or bundle_name in ["my-bundle", "test", "bundle"]:
            suggestions.append("Use descriptive bundle name that indicates purpose")
            score -= 10
        
        # Check variable usage
        if not config.get("variables"):
            suggestions.append("Consider using variables for environment-specific configuration")
            score -= 5
        
        # Check jobs configuration
        jobs = resources.get("jobs", {})
        for job_key, job_config in jobs.items():
            if not isinstance(job_config, dict):
                continue
                
            # Check for job clusters vs existing clusters
            if job_config.get("existing_cluster_id") and target == "prod":
                suggestions.append(f"Job '{job_key}' uses existing cluster in production - consider job clusters")
                score -= 15
            
            # Check notifications
            if not job_config.get("email_notifications"):
                suggestions.append(f"Job '{job_key}' missing email notifications")
                score -= 10
            
            # Check timeout settings
            if not job_config.get("timeout_seconds"):
                suggestions.append(f"Job '{job_key}' missing timeout configuration")
                score -= 5
            
            # Check retry configuration
            if not job_config.get("max_retries"):
                suggestions.append(f"Job '{job_key}' missing retry configuration")
                score -= 5
            
            # Check schedule appropriateness
            schedule = job_config.get("schedule", {})
            if target == "dev" and schedule and schedule.get("pause_status") != "PAUSED":
                suggestions.append(f"Job '{job_key}' should be paused in dev environment")
                score -= 5
        
        # Check cluster configurations
        targets = config.get("targets", {})
        if target in targets:
            target_config = targets[target]
            target_resources = target_config.get("resources", {})
            target_jobs = target_resources.get("jobs", {})
            
            for job_key, job_config in target_jobs.items():
                job_clusters = job_config.get("job_clusters", [])
                for cluster in job_clusters:
                    new_cluster = cluster.get("new_cluster", {})
                    
                    # Check autotermination
                    if not new_cluster.get("autotermination_minutes"):
                        suggestions.append(f"Cluster in job '{job_key}' missing autotermination configuration")
                        score -= 5
                    
                    # Check development optimizations
                    if target == "dev":
                        if not new_cluster.get("spot_bid_price_percent"):
                            suggestions.append(f"Development cluster in job '{job_key}' could use spot instances for cost savings")
                            score -= 3
        
        return {
            "score": max(0, score),
            "suggestions": suggestions
        }
    
    def _validate_security(self, config: Dict[str, Any], target: str) -> Dict[str, Any]:
        """Validate security best practices"""
        issues = []
        
        # Check for hardcoded secrets (basic patterns)
        config_str = json.dumps(config)
        
        # Common secret patterns
        secret_patterns = [
            r'password["\']?\s*:\s*["\'][^"\']{8,}',
            r'api[_-]?key["\']?\s*:\s*["\'][^"\']{20,}',
            r'token["\']?\s*:\s*["\'][^"\']{20,}',
            r'secret["\']?\s*:\s*["\'][^"\']{8,}'
        ]
        
        for pattern in secret_patterns:
            if re.search(pattern, config_str, re.IGNORECASE):
                issues.append("Potential hardcoded secrets detected - use ${secrets.scope.key} instead")
                break
        
        # Check permissions configuration
        resources = config.get("resources", {})
        jobs = resources.get("jobs", {})
        
        for job_key, job_config in jobs.items():
            if not isinstance(job_config, dict):
                continue
                
            # Check if permissions are defined for production
            if target == "prod" and not job_config.get("permissions"):
                issues.append(f"Job '{job_key}' missing permissions configuration for production")
        
        # Check service principal usage in production
        if target == "prod":
            permissions_found = False
            for job_key, job_config in jobs.items():
                if isinstance(job_config, dict) and job_config.get("permissions"):
                    permissions = job_config["permissions"]
                    for perm in permissions:
                        if perm.get("service_principal_name"):
                            permissions_found = True
                            break
            
            if jobs and not permissions_found:
                issues.append("Production bundles should use service principal permissions")
        
        passed = len(issues) == 0
        return {"passed": passed, "issues": issues}
    
    def _validate_target(self, config: Dict[str, Any], target: str) -> List[str]:
        """Validate target-specific configuration"""
        warnings = []
        
        targets = config.get("targets", {})
        if target not in targets:
            warnings.append(f"Target '{target}' not found in configuration")
            return warnings
        
        target_config = targets[target]
        
        # Check mode setting
        mode = target_config.get("mode")
        if target == "prod" and mode != "production":
            warnings.append(f"Production target should use mode: production")
        elif target == "dev" and mode not in ["development", None]:
            warnings.append(f"Development target should use mode: development")
        
        return warnings
    
    def _load_best_practices_rules(self) -> Dict[str, Any]:
        """Load best practices rules from context files"""
        return {
            "naming_conventions": {
                "bundle_name_patterns": [r"^[a-z][a-z0-9-]+[a-z0-9]$"],
                "avoid_names": ["my-bundle", "test", "bundle", "job"]
            },
            "cluster_requirements": {
                "use_job_clusters": True,
                "require_autotermination": True,
                "dev_optimizations": ["spot_instances", "smaller_nodes"]
            },
            "monitoring": {
                "require_notifications": True,
                "require_timeouts": True,
                "require_retries": True
            }
        }
    
    def _load_security_rules(self) -> Dict[str, Any]:
        """Load security validation rules"""
        return {
            "secret_patterns": [
                r'password["\']?\s*:\s*["\'][^"\']{8,}',
                r'api[_-]?key["\']?\s*:\s*["\'][^"\']{20,}',
                r'token["\']?\s*:\s*["\'][^"\']{20,}'
            ],
            "production_requirements": {
                "require_permissions": True,
                "require_service_principals": True,
                "require_production_mode": True
            }
        }
    
    def _load_schema_requirements(self) -> Dict[str, Any]:
        """Load schema validation requirements"""
        return {
            "required_sections": ["bundle"],
            "required_bundle_fields": ["name"],
            "required_job_fields": ["name", "tasks"],
            "required_task_fields": ["task_key"]
        }