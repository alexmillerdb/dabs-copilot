"""
Tests for custom tools module.
Run from project root: python -m pytest tests/test_custom_tools.py -v
"""
import sys
from pathlib import Path

# Add tools module directly to path (bypass main package)
tools_dir = Path(__file__).parent.parent / "src" / "dabs_copilot" / "tools"
sys.path.insert(0, str(tools_dir))

import json
import os
import pytest
from unittest.mock import patch, MagicMock

# Import directly from tools module files
from responses import ok, err
from registry import ToolRegistry, ToolConfig, ToolCategory
from client import get_client, clear_client_cache

# Import tool modules to register tools with registry
import core_tools
import dab_tools
import workspace_tools


# =============================================================================
# Response Helpers Tests
# =============================================================================

class TestResponseHelpers:
    """Tests for ok() and err() response helpers."""

    def test_ok_returns_content_format(self):
        """ok() returns proper content format."""
        result = ok({"status": "healthy"})
        assert "content" in result
        assert len(result["content"]) == 1
        assert result["content"][0]["type"] == "text"

    def test_ok_contains_success_true(self):
        """ok() response contains success: true."""
        result = ok({"data": "test"})
        parsed = json.loads(result["content"][0]["text"])
        assert parsed["success"] is True

    def test_err_returns_content_format(self):
        """err() returns proper content format."""
        result = err("Something failed")
        assert "content" in result
        assert result["content"][0]["type"] == "text"

    def test_err_contains_success_false(self):
        """err() response contains success: false."""
        result = err("Connection failed")
        parsed = json.loads(result["content"][0]["text"])
        assert parsed["success"] is False
        assert "Connection failed" in parsed["error"]

    def test_err_maintains_conversation(self):
        """err() returns dict (not raises), maintaining conversation."""
        result = err("API rate limit exceeded")
        assert isinstance(result, dict)


# =============================================================================
# Tool Registry Tests
# =============================================================================

class TestToolRegistry:
    """Tests for ToolRegistry class."""

    def test_tools_registered(self):
        """All expected tools should be registered."""
        tool_names = ToolRegistry.get_tool_names()

        # Core tools
        assert "health" in tool_names
        assert "list_jobs" in tool_names
        assert "get_job" in tool_names

        # DAB tools
        assert "analyze_notebook" in tool_names
        assert "validate_bundle" in tool_names

        # Workspace tools
        assert "upload_bundle" in tool_names

    def test_get_all_tools(self):
        """get_tools() without config returns all tools."""
        tools = ToolRegistry.get_tools()
        assert len(tools) == 17  # 10 core + 4 DAB + 3 workspace

    def test_filter_by_category(self):
        """Filter tools by category."""
        config = ToolConfig(categories=[ToolCategory.DAB])
        tools = ToolRegistry.get_tools(config)
        names = ToolRegistry.get_tool_names(config)

        assert len(tools) == 4
        assert "analyze_notebook" in names
        assert "generate_bundle" in names
        assert "validate_bundle" in names

    def test_filter_by_include(self):
        """Include only specific tools."""
        config = ToolConfig(include=["health", "list_jobs"])
        names = ToolRegistry.get_tool_names(config)

        assert len(names) == 2
        assert "health" in names
        assert "list_jobs" in names

    def test_filter_by_exclude(self):
        """Exclude specific tools."""
        config = ToolConfig(exclude=["run_job", "execute_dbsql"])
        names = ToolRegistry.get_tool_names(config)

        assert "run_job" not in names
        assert "execute_dbsql" not in names
        assert "health" in names


class TestToolConfig:
    """Tests for ToolConfig dataclass."""

    def test_default_config(self):
        """Default config has no filters."""
        config = ToolConfig()
        assert config.categories is None
        assert config.include is None
        assert config.exclude is None


class TestToolCategory:
    """Tests for ToolCategory enum."""

    def test_category_values(self):
        """Check category enum values."""
        assert ToolCategory.CORE.value == "core"
        assert ToolCategory.DAB.value == "dab"
        assert ToolCategory.WORKSPACE.value == "workspace"


# =============================================================================
# Client Tests
# =============================================================================

class TestDatabricksClient:
    """Tests for get_client() singleton."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_client_cache()

    def test_client_is_cached(self):
        """get_client() returns same instance (cached)."""
        with patch("client.WorkspaceClient") as mock_ws:
            mock_ws.return_value = MagicMock()

            client1 = get_client()
            client2 = get_client()

            assert client1 is client2
            assert mock_ws.call_count == 1

    def test_clear_cache_resets(self):
        """clear_client_cache() forces new client creation."""
        with patch("client.WorkspaceClient") as mock_ws:
            mock_ws.return_value = MagicMock()

            get_client()
            clear_client_cache()
            get_client()

            assert mock_ws.call_count == 2


# =============================================================================
# Integration Test (requires Databricks connection)
# =============================================================================

@pytest.mark.integration
class TestIntegration:
    """Integration tests - require actual Databricks connection."""

    def test_client_connects(self):
        """Client can connect to Databricks (requires credentials)."""
        clear_client_cache()
        try:
            client = get_client()
            user = client.current_user.me()
            assert user.user_name is not None
            print(f"Connected as: {user.user_name}")
        except Exception as e:
            pytest.skip(f"Databricks connection not available: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
