"""
Unit tests for Databricks Apps tools in sdk_tools.py.

Run with: python -m pytest src/dabs_copilot/tools/test_apps_tools.py -v
      or: cd src/dabs_copilot/tools && python test_apps_tools.py
"""
import asyncio
import json
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime

# Import the tools under test
# Handle both direct execution and pytest from project root
try:
    from sdk_tools import (
        list_apps,
        get_app,
        get_app_deployment,
        get_app_environment,
        get_app_permissions,
        APP_TOOLS,
        ALL_TOOLS,
    )
    SDK_MODULE_PATH = "sdk_tools"
except ImportError:
    from dabs_copilot.tools.sdk_tools import (
        list_apps,
        get_app,
        get_app_deployment,
        get_app_environment,
        get_app_permissions,
        APP_TOOLS,
        ALL_TOOLS,
    )
    SDK_MODULE_PATH = "dabs_copilot.tools.sdk_tools"


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_workspace_client():
    """Create a mock WorkspaceClient for testing."""
    with patch(f"{SDK_MODULE_PATH}._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        yield mock_client


@pytest.fixture
def sample_app():
    """Create a sample app object for testing."""
    app = MagicMock()
    app.name = "my-test-app"
    app.description = "A test application"
    app.create_time = datetime(2024, 1, 15, 10, 30, 0)
    app.update_time = datetime(2024, 1, 16, 12, 0, 0)
    app.creator = "user@example.com"
    app.url = "https://my-test-app.databricksapps.com"
    app.pending_deployment = None
    app.active_deployment = MagicMock()
    app.active_deployment.deployment_id = "deploy-123"
    app.compute_status = MagicMock()
    app.compute_status.state = MagicMock()
    app.compute_status.state.value = "RUNNING"
    app.default_source_code_path = "/Workspace/Users/user@example.com/apps/my-test-app"
    app.resources = []
    return app


@pytest.fixture
def sample_deployment():
    """Create a sample deployment object for testing."""
    deployment = MagicMock()
    deployment.deployment_id = "deploy-123"
    deployment.source_code_path = "/Workspace/apps/my-app"
    deployment.status = MagicMock()
    deployment.status.state = MagicMock()
    deployment.status.state.value = "SUCCEEDED"
    deployment.status.message = "Deployment successful"
    deployment.create_time = datetime(2024, 1, 15, 10, 30, 0)
    deployment.update_time = datetime(2024, 1, 15, 10, 35, 0)
    deployment.mode = MagicMock()
    deployment.mode.value = "AUTO_SYNC"
    deployment.deployment_artifacts = MagicMock()
    deployment.deployment_artifacts.source_code_path = "/build/path"
    return deployment


# =============================================================================
# TEST: list_apps
# =============================================================================

class TestListApps:
    """Tests for list_apps tool."""

    @pytest.mark.asyncio
    async def test_list_apps_success(self, mock_workspace_client, sample_app):
        """Test successful listing of apps."""
        mock_workspace_client.apps.list.return_value = [sample_app]

        result = await list_apps.handler({"limit": 10})
        response = json.loads(result["content"][0]["text"])

        assert "apps" in response
        assert response["count"] == 1
        assert response["apps"][0]["name"] == "my-test-app"
        assert response["apps"][0]["url"] == "https://my-test-app.databricksapps.com"

    @pytest.mark.asyncio
    async def test_list_apps_empty(self, mock_workspace_client):
        """Test listing apps when none exist."""
        mock_workspace_client.apps.list.return_value = []

        result = await list_apps.handler({})
        response = json.loads(result["content"][0]["text"])

        assert response["apps"] == []
        assert response["count"] == 0

    @pytest.mark.asyncio
    async def test_list_apps_with_limit(self, mock_workspace_client, sample_app):
        """Test that limit parameter is respected."""
        # Create multiple apps
        apps = [sample_app, sample_app, sample_app]
        mock_workspace_client.apps.list.return_value = apps

        result = await list_apps.handler({"limit": 2})
        response = json.loads(result["content"][0]["text"])

        assert response["count"] == 2

    @pytest.mark.asyncio
    async def test_list_apps_error(self, mock_workspace_client):
        """Test error handling when API fails."""
        mock_workspace_client.apps.list.side_effect = Exception("API error")

        result = await list_apps.handler({})
        response = json.loads(result["content"][0]["text"])

        assert "error" in response
        assert "Failed to list apps" in response["error"]


# =============================================================================
# TEST: get_app
# =============================================================================

class TestGetApp:
    """Tests for get_app tool."""

    @pytest.mark.asyncio
    async def test_get_app_success(self, mock_workspace_client, sample_app):
        """Test successful retrieval of app details."""
        mock_workspace_client.apps.get.return_value = sample_app

        result = await get_app.handler({"name": "my-test-app"})
        response = json.loads(result["content"][0]["text"])

        assert response["name"] == "my-test-app"
        assert response["description"] == "A test application"
        assert response["url"] == "https://my-test-app.databricksapps.com"
        assert response["active_deployment_id"] == "deploy-123"

    @pytest.mark.asyncio
    async def test_get_app_missing_name(self):
        """Test error when name is not provided."""
        result = await get_app.handler({})
        response = json.loads(result["content"][0]["text"])

        assert "error" in response
        assert "name is required" in response["error"]

    @pytest.mark.asyncio
    async def test_get_app_with_resources(self, mock_workspace_client, sample_app):
        """Test get_app with resource bindings."""
        # Add resource bindings
        resource = MagicMock()
        resource.name = "my-job"
        resource.description = "Background job"
        resource.job = MagicMock()
        resource.job.id = "job-123"
        resource.job.permission = "CAN_MANAGE_RUN"
        resource.secret = None
        resource.sql_warehouse = None
        resource.serving_endpoint = None
        sample_app.resources = [resource]

        mock_workspace_client.apps.get.return_value = sample_app

        result = await get_app.handler({"name": "my-test-app"})
        response = json.loads(result["content"][0]["text"])

        assert len(response["resources"]) == 1
        assert response["resources"][0]["name"] == "my-job"
        assert response["resources"][0]["job"]["id"] == "job-123"

    @pytest.mark.asyncio
    async def test_get_app_not_found(self, mock_workspace_client):
        """Test error when app doesn't exist."""
        mock_workspace_client.apps.get.side_effect = Exception("App not found")

        result = await get_app.handler({"name": "nonexistent-app"})
        response = json.loads(result["content"][0]["text"])

        assert "error" in response


# =============================================================================
# TEST: get_app_deployment
# =============================================================================

class TestGetAppDeployment:
    """Tests for get_app_deployment tool."""

    @pytest.mark.asyncio
    async def test_get_deployment_success(self, mock_workspace_client, sample_deployment):
        """Test successful retrieval of deployment details."""
        mock_workspace_client.apps.get_deployment.return_value = sample_deployment

        result = await get_app_deployment.handler({
            "app_name": "my-test-app",
            "deployment_id": "deploy-123"
        })
        response = json.loads(result["content"][0]["text"])

        assert response["deployment_id"] == "deploy-123"
        assert response["status"] == "SUCCEEDED"
        assert response["mode"] == "AUTO_SYNC"

    @pytest.mark.asyncio
    async def test_get_deployment_missing_app_name(self):
        """Test error when app_name is not provided."""
        result = await get_app_deployment.handler({"deployment_id": "deploy-123"})
        response = json.loads(result["content"][0]["text"])

        assert "error" in response
        assert "app_name is required" in response["error"]

    @pytest.mark.asyncio
    async def test_get_deployment_missing_deployment_id(self):
        """Test error when deployment_id is not provided."""
        result = await get_app_deployment.handler({"app_name": "my-app"})
        response = json.loads(result["content"][0]["text"])

        assert "error" in response
        assert "deployment_id is required" in response["error"]


# =============================================================================
# TEST: get_app_environment
# =============================================================================

class TestGetAppEnvironment:
    """Tests for get_app_environment tool."""

    @pytest.mark.asyncio
    async def test_get_environment_success(self, mock_workspace_client):
        """Test successful retrieval of app environment."""
        env = MagicMock()
        env_var = MagicMock()
        env_var.name = "DATABASE_URL"
        env_var.value = "jdbc:postgresql://..."
        env_var.value_from = None
        env.env = [env_var]

        mock_workspace_client.apps.get_environment.return_value = env

        result = await get_app_environment.handler({"name": "my-test-app"})
        response = json.loads(result["content"][0]["text"])

        assert response["name"] == "my-test-app"
        assert len(response["env"]) == 1
        assert response["env"][0]["name"] == "DATABASE_URL"

    @pytest.mark.asyncio
    async def test_get_environment_missing_name(self):
        """Test error when name is not provided."""
        result = await get_app_environment.handler({})
        response = json.loads(result["content"][0]["text"])

        assert "error" in response
        assert "name is required" in response["error"]

    @pytest.mark.asyncio
    async def test_get_environment_empty(self, mock_workspace_client):
        """Test app with no environment variables."""
        env = MagicMock()
        env.env = None

        mock_workspace_client.apps.get_environment.return_value = env

        result = await get_app_environment.handler({"name": "my-test-app"})
        response = json.loads(result["content"][0]["text"])

        assert response["env"] == []


# =============================================================================
# TEST: get_app_permissions
# =============================================================================

class TestGetAppPermissions:
    """Tests for get_app_permissions tool."""

    @pytest.mark.asyncio
    async def test_get_permissions_success(self, mock_workspace_client):
        """Test successful retrieval of app permissions."""
        perms = MagicMock()
        level = MagicMock()
        level.permission_level = MagicMock()
        level.permission_level.value = "CAN_MANAGE"
        level.description = "User can manage this app"
        perms.permission_levels = [level]

        mock_workspace_client.apps.get_permission_levels.return_value = perms

        result = await get_app_permissions.handler({"app_name": "my-test-app"})
        response = json.loads(result["content"][0]["text"])

        assert response["app_name"] == "my-test-app"
        assert len(response["permission_levels"]) == 1
        assert response["permission_levels"][0]["permission_level"] == "CAN_MANAGE"

    @pytest.mark.asyncio
    async def test_get_permissions_missing_app_name(self):
        """Test error when app_name is not provided."""
        result = await get_app_permissions.handler({})
        response = json.loads(result["content"][0]["text"])

        assert "error" in response
        assert "app_name is required" in response["error"]


# =============================================================================
# TEST: Tool Registration
# =============================================================================

class TestToolRegistration:
    """Tests for tool registration and categorization."""

    def test_app_tools_count(self):
        """Verify all 5 apps tools are registered."""
        assert len(APP_TOOLS) == 5

    def test_app_tools_in_all_tools(self):
        """Verify apps tools are in ALL_TOOLS."""
        for tool in APP_TOOLS:
            assert tool in ALL_TOOLS

    def test_app_tools_names(self):
        """Verify apps tools have correct names."""
        expected_names = {
            "list_apps",
            "get_app",
            "get_app_deployment",
            "get_app_environment",
            "get_app_permissions",
        }
        actual_names = {t.name for t in APP_TOOLS}
        assert actual_names == expected_names


# =============================================================================
# MAIN - Run tests directly
# =============================================================================

async def run_manual_tests():
    """Run tests manually without pytest (for quick verification)."""
    print("=" * 60)
    print("Running manual tests for Apps tools")
    print("=" * 60)

    # Test tool registration
    print("\n1. Testing tool registration...")
    assert len(APP_TOOLS) == 5, "Expected 5 apps tools"
    print("   ✓ 5 apps tools registered")

    for tool in APP_TOOLS:
        assert tool in ALL_TOOLS, f"Tool {tool.name} not in ALL_TOOLS"
    print("   ✓ All apps tools in ALL_TOOLS")

    # Test error handling (no mocking needed)
    print("\n2. Testing error handling...")

    result = await get_app.handler({})
    response = json.loads(result["content"][0]["text"])
    assert "error" in response, "Expected error for missing name"
    print("   ✓ get_app rejects missing name")

    result = await get_app_deployment.handler({})
    response = json.loads(result["content"][0]["text"])
    assert "error" in response, "Expected error for missing params"
    print("   ✓ get_app_deployment rejects missing params")

    result = await get_app_environment.handler({})
    response = json.loads(result["content"][0]["text"])
    assert "error" in response, "Expected error for missing name"
    print("   ✓ get_app_environment rejects missing name")

    result = await get_app_permissions.handler({})
    response = json.loads(result["content"][0]["text"])
    assert "error" in response, "Expected error for missing app_name"
    print("   ✓ get_app_permissions rejects missing app_name")

    print("\n" + "=" * 60)
    print("All manual tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_manual_tests())
