"""Tests for base agent"""
import pytest
from agents.base import BaseAgent


class MockAgent(BaseAgent):
    """Mock agent for testing"""
    
    def _create_client(self):
        return "mock_client"
    
    async def handle_request(self, request: str) -> str:
        return f"Handled: {request}"


def test_base_agent_initialization():
    """Test base agent initialization"""
    agent = MockAgent("test-agent")
    
    assert agent.name == "test-agent"
    assert agent._client is None


def test_base_agent_lazy_client_loading():
    """Test lazy loading of Claude SDK client"""
    agent = MockAgent("test-agent")
    
    # Client should be None initially
    assert agent._client is None
    
    # Accessing client should trigger creation
    client = agent.client
    assert client == "mock_client"
    assert agent._client == "mock_client"


@pytest.mark.asyncio
async def test_base_agent_handle_request():
    """Test request handling"""
    agent = MockAgent("test-agent")
    
    result = await agent.handle_request("test request")
    assert result == "Handled: test request"


def test_base_agent_repr():
    """Test string representation"""
    agent = MockAgent("test-agent")
    
    assert repr(agent) == "MockAgent(name='test-agent')"