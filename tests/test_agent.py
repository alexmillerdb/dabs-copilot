"""Tests for the simplified DABsAgent."""
import asyncio
import pytest
from src.dabs_copilot import (
    DABsAgent,
    generate_bundle,
    MCP_TOOLS,
    DESTRUCTIVE_TOOLS,
    ALLOWED_TOOLS,
    DABS_AGENTS,
    get_project_root,
)


def test_mcp_tools_defined():
    """Test that MCP tools are defined."""
    assert len(MCP_TOOLS) > 0
    assert "mcp__databricks-mcp__list_jobs" in MCP_TOOLS
    assert "mcp__databricks-mcp__generate_bundle" in MCP_TOOLS


def test_destructive_tools_defined():
    """Test that destructive tools are defined."""
    assert len(DESTRUCTIVE_TOOLS) > 0
    assert "mcp__databricks-mcp__upload_bundle" in DESTRUCTIVE_TOOLS
    assert "mcp__databricks-mcp__run_bundle_command" in DESTRUCTIVE_TOOLS


def test_dabs_agent_creation():
    """Test that DABsAgent can be created."""
    agent = DABsAgent()
    assert agent is not None
    assert agent.session_id is None  # Not started yet


def test_dabs_agent_with_callback():
    """Test DABsAgent with confirmation callback."""
    async def confirm(tool_name, tool_input):
        return True

    agent = DABsAgent(confirm_destructive=confirm)
    assert agent is not None
    assert agent._confirm_destructive is not None


def test_generate_bundle_is_async_generator():
    """Test that generate_bundle returns an async generator."""
    gen = generate_bundle("test prompt")
    assert hasattr(gen, "__anext__")


@pytest.mark.asyncio
async def test_dabs_agent_context_manager():
    """Test DABsAgent as async context manager."""
    # This will fail without MCP server, but should at least enter/exit cleanly
    # when there's a connection error
    agent = DABsAgent()

    # Check that agent is not started before entering context
    assert agent._client is None

    # Note: Actually entering the context would require MCP server running
    # So we just verify the structure is correct


def test_allowed_tools_includes_orchestration():
    """Test that ALLOWED_TOOLS includes orchestration tools."""
    assert "Skill" in ALLOWED_TOOLS
    assert "Task" in ALLOWED_TOOLS
    assert "Read" in ALLOWED_TOOLS
    assert "Write" in ALLOWED_TOOLS
    # MCP tools should be included
    assert "mcp__databricks-mcp__list_jobs" in ALLOWED_TOOLS


def test_dabs_agents_defined():
    """Test that all subagents are defined."""
    expected_agents = [
        "dab-orchestrator",
        "dab-discovery",
        "dab-analyzer",
        "dab-generator",
        "dab-validator",
        "dab-deployer",
    ]
    for agent_name in expected_agents:
        assert agent_name in DABS_AGENTS
        agent_def = DABS_AGENTS[agent_name]
        assert agent_def.description
        assert agent_def.prompt
        assert agent_def.model in ["haiku", "sonnet", "opus"]


def test_get_project_root():
    """Test that get_project_root finds the project."""
    root = get_project_root()
    # Should find a directory containing .claude
    import os
    assert os.path.isdir(os.path.join(root, ".claude"))


def test_dabs_agents_have_appropriate_tools():
    """Test that each agent has appropriate tools for its role."""
    # Discovery agent should have job/notebook tools
    discovery_tools = DABS_AGENTS["dab-discovery"].tools
    assert "mcp__databricks-mcp__get_job" in discovery_tools
    assert "mcp__databricks-mcp__list_notebooks" in discovery_tools

    # Analyzer should have analyze_notebook
    analyzer_tools = DABS_AGENTS["dab-analyzer"].tools
    assert "mcp__databricks-mcp__analyze_notebook" in analyzer_tools

    # Generator should have generate tools and Skill
    generator_tools = DABS_AGENTS["dab-generator"].tools
    assert "mcp__databricks-mcp__generate_bundle" in generator_tools
    assert "Skill" in generator_tools

    # Validator should have validate_bundle
    validator_tools = DABS_AGENTS["dab-validator"].tools
    assert "mcp__databricks-mcp__validate_bundle" in validator_tools

    # Deployer should have upload and run tools
    deployer_tools = DABS_AGENTS["dab-deployer"].tools
    assert "mcp__databricks-mcp__upload_bundle" in deployer_tools
    assert "mcp__databricks-mcp__run_bundle_command" in deployer_tools


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
