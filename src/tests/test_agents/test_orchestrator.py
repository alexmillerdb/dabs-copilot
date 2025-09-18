"""Tests for orchestrator agent"""
import pytest
from unittest.mock import Mock, AsyncMock
from agents.orchestrator import OrchestratorAgent


@pytest.fixture
def mock_mcp_client():
    """Mock MCP client for testing"""
    client = Mock()
    client.list_jobs = AsyncMock(return_value={"success": True, "data": {"jobs": []}})
    client.get_job = AsyncMock(return_value={"success": True, "data": {"job_id": 123}})
    return client


def test_orchestrator_initialization():
    """Test orchestrator agent initialization"""
    agent = OrchestratorAgent()
    
    assert agent.name == "orchestrator"
    assert hasattr(agent, 'mcp_client')


@pytest.mark.asyncio
async def test_orchestrator_simple_request(mock_mcp_client):
    """Test simple request handling"""
    agent = OrchestratorAgent()
    agent.mcp_client = mock_mcp_client
    
    result = await agent.handle_request("list jobs")
    
    assert "jobs" in result.lower()
    mock_mcp_client.list_jobs.assert_called_once()


@pytest.mark.asyncio
async def test_orchestrator_job_request(mock_mcp_client):
    """Test job-specific request handling"""
    agent = OrchestratorAgent()
    agent.mcp_client = mock_mcp_client
    
    result = await agent.handle_request("get job 123")
    
    assert "123" in result
    mock_mcp_client.get_job.assert_called_once_with(123)