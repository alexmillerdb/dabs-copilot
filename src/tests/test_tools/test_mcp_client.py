"""Tests for MCP client bridge"""
import pytest
from unittest.mock import Mock, patch
from tools.mcp_client import DatabricksMCPClient


def test_mcp_client_local_mode():
    """Test MCP client in local mode"""
    client = DatabricksMCPClient(mode="local")
    
    assert client.use_stdio is True
    assert "python" in client.server_command[0]
    assert "mcp/server/main.py" in client.server_command[1]


def test_mcp_client_remote_mode_default_url():
    """Test MCP client in remote mode with default URL"""
    client = DatabricksMCPClient(mode="remote")
    
    assert client.use_stdio is False
    assert "databricks-mcp-server" in client.base_url


def test_mcp_client_remote_mode_custom_url():
    """Test MCP client in remote mode with custom URL"""
    custom_url = "https://custom-server.example.com"
    client = DatabricksMCPClient(mode="remote", remote_url=custom_url)
    
    assert client.use_stdio is False
    assert client.base_url == custom_url


@patch.dict('os.environ', {'MCP_REMOTE_URL': 'https://env-server.example.com'})
def test_mcp_client_remote_mode_env_url():
    """Test MCP client uses environment variable for remote URL"""
    client = DatabricksMCPClient(mode="remote")
    
    assert client.base_url == "https://env-server.example.com"


@pytest.mark.asyncio
async def test_call_tool_interface():
    """Test that call_tool has the correct interface"""
    client = DatabricksMCPClient(mode="local")
    
    # Should have the method (even if not implemented yet)
    assert hasattr(client, 'call_tool')
    assert callable(client.call_tool)