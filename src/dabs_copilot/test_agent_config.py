"""
Unit tests for agent.py configuration to verify tool wiring.

Run with: python -m pytest src/dabs_copilot/test_agent_config.py -v
      or: cd src/dabs_copilot && python test_agent_config.py
"""
import pytest

# Import agent configuration (handle both direct execution and pytest)
try:
    from agent import (
        DABS_AGENTS,
        _MCP_TOOL_NAMES,
        MCP_TOOLS,
        BASE_TOOLS,
        ALLOWED_TOOLS,
        CUSTOM_TOOLS_SERVER,
    )
except ImportError:
    from dabs_copilot.agent import (
        DABS_AGENTS,
        _MCP_TOOL_NAMES,
        MCP_TOOLS,
        BASE_TOOLS,
        ALLOWED_TOOLS,
        CUSTOM_TOOLS_SERVER,
    )


class TestMCPToolsConfig:
    """Tests for MCP tools configuration."""

    def test_mcp_tool_count(self):
        """Verify all 24 MCP tools are registered (17 original + 5 apps + 2 pipelines)."""
        assert len(_MCP_TOOL_NAMES) == 24

    def test_apps_tools_in_mcp_names(self):
        """Verify all 5 apps tools are in MCP tool names."""
        apps_tools = [
            "list_apps",
            "get_app",
            "get_app_deployment",
            "get_app_environment",
            "get_app_permissions",
        ]
        for tool in apps_tools:
            assert tool in _MCP_TOOL_NAMES, f"Missing {tool} in _MCP_TOOL_NAMES"

    def test_pipeline_tools_in_mcp_names(self):
        """Verify all 2 pipeline tools are in MCP tool names."""
        pipeline_tools = [
            "list_pipelines",
            "get_pipeline",
        ]
        for tool in pipeline_tools:
            assert tool in _MCP_TOOL_NAMES, f"Missing {tool} in _MCP_TOOL_NAMES"

    def test_mcp_tools_formatted_correctly(self):
        """Verify MCP tools are formatted with correct prefix."""
        for tool in MCP_TOOLS:
            assert tool.startswith(f"mcp__{CUSTOM_TOOLS_SERVER}__"), f"Invalid format: {tool}"

    def test_base_tools_includes_skill(self):
        """Verify Skill tool is in base tools."""
        assert "Skill" in BASE_TOOLS


class TestSubagentConfig:
    """Tests for subagent configuration."""

    def test_analyst_has_skill_tool(self):
        """Verify analyst subagent has Skill tool."""
        analyst_tools = DABS_AGENTS["dab-analyst"].tools
        assert "Skill" in analyst_tools

    def test_analyst_has_apps_tools(self):
        """Verify analyst subagent has all 5 apps tools."""
        analyst_tools = DABS_AGENTS["dab-analyst"].tools
        apps_tools = [
            "mcp__databricks-mcp__list_apps",
            "mcp__databricks-mcp__get_app",
            "mcp__databricks-mcp__get_app_deployment",
            "mcp__databricks-mcp__get_app_environment",
            "mcp__databricks-mcp__get_app_permissions",
        ]
        for tool in apps_tools:
            assert tool in analyst_tools, f"Analyst missing {tool}"

    def test_analyst_has_pipeline_tools(self):
        """Verify analyst subagent has all 2 pipeline tools."""
        analyst_tools = DABS_AGENTS["dab-analyst"].tools
        pipeline_tools = [
            "mcp__databricks-mcp__list_pipelines",
            "mcp__databricks-mcp__get_pipeline",
        ]
        for tool in pipeline_tools:
            assert tool in analyst_tools, f"Analyst missing {tool}"

    def test_builder_has_skill_tool(self):
        """Verify builder subagent has Skill tool."""
        builder_tools = DABS_AGENTS["dab-builder"].tools
        assert "Skill" in builder_tools

    def test_builder_has_apps_tools(self):
        """Verify builder subagent has all 5 apps tools."""
        builder_tools = DABS_AGENTS["dab-builder"].tools
        apps_tools = [
            "mcp__databricks-mcp__list_apps",
            "mcp__databricks-mcp__get_app",
            "mcp__databricks-mcp__get_app_deployment",
            "mcp__databricks-mcp__get_app_environment",
            "mcp__databricks-mcp__get_app_permissions",
        ]
        for tool in apps_tools:
            assert tool in builder_tools, f"Builder missing {tool}"

    def test_deployer_has_skill_tool(self):
        """Verify deployer subagent has Skill tool."""
        deployer_tools = DABS_AGENTS["dab-deployer"].tools
        assert "Skill" in deployer_tools

    def test_analyst_tool_count(self):
        """Verify analyst has expected number of tools."""
        analyst_tools = DABS_AGENTS["dab-analyst"].tools
        # 6 discovery + 5 apps + 2 pipelines + 4 file/pattern tools = 17
        assert len(analyst_tools) == 17

    def test_builder_tool_count(self):
        """Verify builder has expected number of tools."""
        builder_tools = DABS_AGENTS["dab-builder"].tools
        # 3 bundle + 5 apps + 4 file/pattern tools = 12
        assert len(builder_tools) == 12

    def test_deployer_tool_count(self):
        """Verify deployer has expected number of tools."""
        deployer_tools = DABS_AGENTS["dab-deployer"].tools
        # 3 deployment + 1 Skill = 4
        assert len(deployer_tools) == 4


class TestToolCategories:
    """Tests for tool category configuration."""

    def test_core_tools_exist(self):
        """Verify core tools are included."""
        core_tools = ["health", "list_jobs", "get_job", "run_job"]
        for tool in core_tools:
            assert tool in _MCP_TOOL_NAMES

    def test_dab_tools_exist(self):
        """Verify DAB tools are included."""
        dab_tools = ["analyze_notebook", "generate_bundle", "validate_bundle"]
        for tool in dab_tools:
            assert tool in _MCP_TOOL_NAMES

    def test_workspace_tools_exist(self):
        """Verify workspace tools are included."""
        workspace_tools = ["upload_bundle", "run_bundle_command", "sync_workspace_to_local"]
        for tool in workspace_tools:
            assert tool in _MCP_TOOL_NAMES


def run_manual_tests():
    """Run tests manually without pytest."""
    print("=" * 60)
    print("Running manual tests for agent configuration")
    print("=" * 60)

    # Test MCP tools
    print("\n1. Testing MCP tools configuration...")
    assert len(_MCP_TOOL_NAMES) == 24, f"Expected 24 tools, got {len(_MCP_TOOL_NAMES)}"
    print(f"   ✓ {len(_MCP_TOOL_NAMES)} MCP tools registered")

    apps_tools = ["list_apps", "get_app", "get_app_deployment", "get_app_environment", "get_app_permissions"]
    for tool in apps_tools:
        assert tool in _MCP_TOOL_NAMES, f"Missing {tool}"
    print("   ✓ All 5 apps tools in MCP tool names")

    pipeline_tools = ["list_pipelines", "get_pipeline"]
    for tool in pipeline_tools:
        assert tool in _MCP_TOOL_NAMES, f"Missing {tool}"
    print("   ✓ All 2 pipeline tools in MCP tool names")

    # Test subagent tools
    print("\n2. Testing subagent tool configuration...")

    assert "Skill" in DABS_AGENTS["dab-analyst"].tools, "Analyst missing Skill"
    print("   ✓ Analyst has Skill tool")

    assert "Skill" in DABS_AGENTS["dab-builder"].tools, "Builder missing Skill"
    print("   ✓ Builder has Skill tool")

    assert "Skill" in DABS_AGENTS["dab-deployer"].tools, "Deployer missing Skill"
    print("   ✓ Deployer has Skill tool")

    # Test apps tools in subagents
    print("\n3. Testing apps tools in subagents...")

    for agent_name in ["dab-analyst", "dab-builder"]:
        for tool in ["mcp__databricks-mcp__list_apps", "mcp__databricks-mcp__get_app"]:
            assert tool in DABS_AGENTS[agent_name].tools, f"{agent_name} missing {tool}"
    print("   ✓ Apps tools in analyst and builder")

    # Test pipeline tools in analyst
    print("\n4. Testing pipeline tools in analyst...")

    for tool in ["mcp__databricks-mcp__list_pipelines", "mcp__databricks-mcp__get_pipeline"]:
        assert tool in DABS_AGENTS["dab-analyst"].tools, f"Analyst missing {tool}"
    print("   ✓ Pipeline tools in analyst")

    # Summary
    print("\n" + "=" * 60)
    print("All manual tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    run_manual_tests()
