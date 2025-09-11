"""
Test suite for validate_bundle tool
Comprehensive tests for bundle validation functionality
"""

import pytest
import tempfile
import os
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# Import the validation service and tool
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server'))

from services.validation_service import BundleValidationService
from tools_dab import validate_bundle


class TestBundleValidationService:
    """Test the BundleValidationService class"""
    
    @pytest.fixture
    def validation_service(self):
        """Create validation service instance"""
        return BundleValidationService()
    
    @pytest.fixture
    def temp_bundle_dir(self):
        """Create temporary bundle directory for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def valid_bundle_config(self):
        """Sample valid bundle configuration"""
        return {
            "bundle": {
                "name": "customer-analytics-pipeline",
                "description": "Customer analytics ETL pipeline"
            },
            "variables": {
                "catalog": {
                    "description": "Unity Catalog catalog name",
                    "default": "${bundle.target}_catalog"
                },
                "warehouse_id": {
                    "description": "SQL warehouse ID",
                }
            },
            "resources": {
                "jobs": {
                    "etl_job": {
                        "name": "customer-etl-${bundle.target}",
                        "email_notifications": {
                            "on_failure": ["admin@company.com"]
                        },
                        "timeout_seconds": 3600,
                        "max_retries": 2,
                        "tasks": [
                            {
                                "task_key": "extract_data",
                                "notebook_task": {
                                    "notebook_path": "./notebooks/extract.py"
                                }
                            }
                        ]
                    }
                }
            },
            "targets": {
                "dev": {
                    "mode": "development",
                    "variables": {
                        "catalog": "dev_analytics"
                    }
                },
                "prod": {
                    "mode": "production",
                    "variables": {
                        "catalog": "main"
                    }
                }
            }
        }
    
    @pytest.fixture
    def invalid_bundle_config(self):
        """Sample invalid bundle configuration"""
        return {
            "bundle": {
                # Missing required name field
                "description": "Test bundle"
            },
            "resources": {
                "jobs": {
                    "bad_job": {
                        # Missing required name field
                        "tasks": []  # Empty tasks
                    }
                }
            }
        }
    
    def create_bundle_file(self, temp_dir: Path, config: dict, filename: str = "databricks.yml"):
        """Helper to create bundle configuration file"""
        import yaml
        bundle_file = temp_dir / filename
        with open(bundle_file, 'w') as f:
            yaml.dump(config, f)
        return bundle_file
    
    @pytest.mark.asyncio
    async def test_validate_valid_bundle(self, validation_service, temp_bundle_dir, valid_bundle_config):
        """Test validation of a valid bundle configuration"""
        bundle_file = self.create_bundle_file(temp_bundle_dir, valid_bundle_config)
        
        result = await validation_service.validate_bundle(
            bundle_path=str(bundle_file),
            target="dev",
            check_best_practices=True,
            check_security=True
        )
        
        assert result["validation_passed"] == True
        assert len(result["errors"]) == 0
        assert result["security_checks"]["passed"] == True
        assert result["best_practices"]["score"] > 70
    
    @pytest.mark.asyncio
    async def test_validate_invalid_bundle(self, validation_service, temp_bundle_dir, invalid_bundle_config):
        """Test validation of an invalid bundle configuration"""
        bundle_file = self.create_bundle_file(temp_bundle_dir, invalid_bundle_config)
        
        result = await validation_service.validate_bundle(
            bundle_path=str(bundle_file),
            target="dev"
        )
        
        assert result["validation_passed"] == False
        assert len(result["errors"]) > 0
        assert "Bundle name is required" in str(result["errors"])
    
    @pytest.mark.asyncio
    async def test_validate_missing_file(self, validation_service):
        """Test validation when bundle file doesn't exist"""
        result = await validation_service.validate_bundle(
            bundle_path="/nonexistent/path/databricks.yml",
            target="dev"
        )
        
        assert result["validation_passed"] == False
        assert len(result["errors"]) > 0
        assert "not found" in str(result["errors"]).lower()
    
    @pytest.mark.asyncio
    async def test_validate_directory_path(self, validation_service, temp_bundle_dir, valid_bundle_config):
        """Test validation when providing directory path instead of file path"""
        self.create_bundle_file(temp_bundle_dir, valid_bundle_config)
        
        result = await validation_service.validate_bundle(
            bundle_path=str(temp_bundle_dir),
            target="dev"
        )
        
        assert result["validation_passed"] == True
        assert result["config_path"] == str(temp_bundle_dir / "databricks.yml")
    
    @pytest.mark.asyncio
    async def test_best_practices_validation(self, validation_service, temp_bundle_dir):
        """Test best practices validation rules"""
        poor_config = {
            "bundle": {
                "name": "my-bundle"  # Poor naming
            },
            "resources": {
                "jobs": {
                    "job1": {
                        "name": "test-job",
                        "existing_cluster_id": "cluster-123",  # Should use job clusters
                        "tasks": [
                            {
                                "task_key": "task1",
                                "notebook_task": {
                                    "notebook_path": "./notebook.py"
                                }
                            }
                        ]
                        # Missing email_notifications, timeout_seconds, max_retries
                    }
                }
            }
        }
        
        bundle_file = self.create_bundle_file(temp_bundle_dir, poor_config)
        
        result = await validation_service.validate_bundle(
            bundle_path=str(bundle_file),
            target="prod",  # Production should flag existing cluster usage
            check_best_practices=True
        )
        
        assert result["best_practices"]["score"] < 80
        suggestions = result["best_practices"]["suggestions"]
        assert any("descriptive bundle name" in s for s in suggestions)
        assert any("email notifications" in s for s in suggestions)
    
    @pytest.mark.asyncio
    async def test_security_validation(self, validation_service, temp_bundle_dir):
        """Test security validation rules"""
        insecure_config = {
            "bundle": {
                "name": "secure-test"
            },
            "resources": {
                "jobs": {
                    "job1": {
                        "name": "job",
                        "tasks": [
                            {
                                "task_key": "task1",
                                "notebook_task": {
                                    "notebook_path": "./notebook.py",
                                    "base_parameters": {
                                        "api_key": "sk-1234567890abcdef1234567890",  # Hardcoded secret
                                        "password": "secretpassword123"
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        }
        
        bundle_file = self.create_bundle_file(temp_bundle_dir, insecure_config)
        
        result = await validation_service.validate_bundle(
            bundle_path=str(bundle_file),
            target="prod",
            check_security=True
        )
        
        assert result["security_checks"]["passed"] == False
        issues = result["security_checks"]["issues"]
        assert any("hardcoded secrets" in issue.lower() for issue in issues)
    
    @pytest.mark.asyncio
    async def test_target_specific_validation(self, validation_service, temp_bundle_dir, valid_bundle_config):
        """Test target-specific validation rules"""
        # Test production target requirements
        result = await validation_service.validate_bundle(
            bundle_path=str(self.create_bundle_file(temp_bundle_dir, valid_bundle_config)),
            target="prod",
            check_security=True
        )
        
        # Should warn about production mode if not set correctly
        target_config = valid_bundle_config.get("targets", {}).get("prod", {})
        if target_config.get("mode") != "production":
            assert any("production" in w.lower() for w in result.get("warnings", []))
    
    @pytest.mark.asyncio
    async def test_yaml_parsing_error(self, validation_service, temp_bundle_dir):
        """Test handling of invalid YAML syntax"""
        invalid_yaml_file = temp_bundle_dir / "databricks.yml"
        with open(invalid_yaml_file, 'w') as f:
            f.write("bundle:\n  name: test\n    invalid: indentation")  # Invalid YAML
        
        result = await validation_service.validate_bundle(
            bundle_path=str(invalid_yaml_file),
            target="dev"
        )
        
        assert result["validation_passed"] == False
        assert any("YAML" in error or "parsing" in error for error in result["errors"])


class TestValidateBundleTool:
    """Test the validate_bundle MCP tool"""
    
    @pytest.fixture
    def temp_bundle_dir(self):
        """Create temporary bundle directory for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def sample_bundle(self, temp_bundle_dir):
        """Create a sample bundle for testing"""
        import yaml
        config = {
            "bundle": {
                "name": "test-pipeline"
            },
            "resources": {
                "jobs": {
                    "main_job": {
                        "name": "test-job-${bundle.target}",
                        "tasks": [
                            {
                                "task_key": "process",
                                "notebook_task": {
                                    "notebook_path": "./notebook.py"
                                }
                            }
                        ]
                    }
                }
            },
            "targets": {
                "dev": {
                    "mode": "development"
                }
            }
        }
        
        bundle_file = temp_bundle_dir / "databricks.yml"
        with open(bundle_file, 'w') as f:
            yaml.dump(config, f)
        
        return bundle_file
    
    @pytest.mark.asyncio
    async def test_validate_bundle_tool_success(self, sample_bundle):
        """Test successful bundle validation through MCP tool"""
        result = await validate_bundle(
            bundle_path=str(sample_bundle),
            target="dev",
            check_best_practices=True,
            check_security=True
        )
        
        # Parse JSON response
        response = json.loads(result)
        
        assert response["success"] == True
        assert "validation_passed" in response["data"]
        assert "validation_summary" in response["data"]
        assert "recommendations" in response["data"]
    
    @pytest.mark.asyncio
    async def test_validate_bundle_tool_error_handling(self):
        """Test error handling in validate_bundle tool"""
        result = await validate_bundle(
            bundle_path="/nonexistent/path",
            target="dev"
        )
        
        response = json.loads(result)
        assert response["success"] == False
        assert "error" in response
    
    @pytest.mark.asyncio
    async def test_validate_bundle_tool_recommendations(self, sample_bundle):
        """Test that tool provides actionable recommendations"""
        result = await validate_bundle(
            bundle_path=str(sample_bundle),
            target="dev",
            check_best_practices=True,
            check_security=True
        )
        
        response = json.loads(result)
        
        if response["success"]:
            data = response["data"]
            recommendations = data["recommendations"]
            
            # Check recommendation structure
            assert "immediate_actions" in recommendations
            assert "improvements" in recommendations
            assert "next_steps" in recommendations
            
            # Should have next steps regardless of validation result
            assert len(recommendations["next_steps"]) > 0


class TestValidationIntegration:
    """Integration tests for validation workflow"""
    
    @pytest.fixture
    def temp_bundle_dir(self):
        """Create temporary bundle directory for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    def create_complete_bundle(self, temp_dir: Path):
        """Create a complete bundle structure for integration testing"""
        import yaml
        
        # Create main bundle config
        config = {
            "bundle": {
                "name": "integration-test-pipeline",
                "description": "Integration test bundle"
            },
            "variables": {
                "catalog": {
                    "description": "Catalog name",
                    "default": "test_catalog"
                },
                "environment": {
                    "description": "Environment identifier"
                }
            },
            "resources": {
                "jobs": {
                    "etl_pipeline": {
                        "name": "etl-${bundle.target}",
                        "email_notifications": {
                            "on_failure": ["${var.notification_email}"]
                        },
                        "timeout_seconds": 7200,
                        "max_retries": 3,
                        "job_clusters": [
                            {
                                "job_cluster_key": "main",
                                "new_cluster": {
                                    "spark_version": "13.3.x-scala2.12",
                                    "node_type_id": "i3.xlarge",
                                    "num_workers": 2,
                                    "autotermination_minutes": 30
                                }
                            }
                        ],
                        "tasks": [
                            {
                                "task_key": "extract",
                                "job_cluster_key": "main",
                                "notebook_task": {
                                    "notebook_path": "./notebooks/extract.py",
                                    "base_parameters": {
                                        "catalog": "${var.catalog}"
                                    }
                                }
                            },
                            {
                                "task_key": "transform",
                                "depends_on": [{"task_key": "extract"}],
                                "job_cluster_key": "main",
                                "notebook_task": {
                                    "notebook_path": "./notebooks/transform.py"
                                }
                            }
                        ]
                    }
                }
            },
            "targets": {
                "dev": {
                    "mode": "development",
                    "variables": {
                        "environment": "development",
                        "notification_email": "dev@company.com"
                    }
                },
                "prod": {
                    "mode": "production",
                    "variables": {
                        "environment": "production",
                        "notification_email": "prod@company.com"
                    }
                }
            }
        }
        
        bundle_file = temp_dir / "databricks.yml"
        with open(bundle_file, 'w') as f:
            yaml.dump(config, f)
        
        return bundle_file
    
    @pytest.mark.asyncio
    async def test_complete_validation_workflow(self, temp_bundle_dir):
        """Test complete validation workflow with realistic bundle"""
        bundle_file = self.create_complete_bundle(temp_bundle_dir)
        
        # Test development target
        dev_result = await validate_bundle(
            bundle_path=str(bundle_file),
            target="dev",
            check_best_practices=True,
            check_security=True
        )
        
        dev_response = json.loads(dev_result)
        assert dev_response["success"] == True
        
        # Test production target
        prod_result = await validate_bundle(
            bundle_path=str(bundle_file),
            target="prod",
            check_best_practices=True,
            check_security=True
        )
        
        prod_response = json.loads(prod_result)
        assert prod_response["success"] == True
        
        # Production should have stricter requirements
        dev_data = dev_response["data"]
        prod_data = prod_response["data"]
        
        # Both should validate successfully with this good configuration
        assert dev_data["validation_passed"] == True
        assert prod_data["validation_passed"] == True
        
        # Production should have good best practices score
        assert prod_data["best_practices"]["score"] >= 80


if __name__ == "__main__":
    # Run tests manually for development
    import asyncio
    
    async def run_tests():
        # Create test instances
        service = BundleValidationService()
        
        # Test basic functionality
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create a simple test bundle
            import yaml
            config = {
                "bundle": {"name": "test-bundle"},
                "resources": {
                    "jobs": {
                        "test_job": {
                            "name": "test",
                            "tasks": [{"task_key": "test", "notebook_task": {"notebook_path": "./test.py"}}]
                        }
                    }
                }
            }
            
            bundle_file = temp_path / "databricks.yml"
            with open(bundle_file, 'w') as f:
                yaml.dump(config, f)
            
            result = await service.validate_bundle(str(bundle_file))
            print("Test validation result:", json.dumps(result, indent=2))
    
    # Run if executed directly
    asyncio.run(run_tests())