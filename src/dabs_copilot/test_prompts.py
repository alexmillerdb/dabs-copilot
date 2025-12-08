"""
Unit tests for prompts.py to verify skill references are included.

Run with: python -m pytest src/dabs_copilot/test_prompts.py -v
      or: cd src/dabs_copilot && python test_prompts.py
"""
import pytest

# Import prompts (handle both direct execution and pytest)
try:
    from prompts import (
        DAB_ANALYST_PROMPT,
        DAB_BUILDER_PROMPT,
        DAB_DEPLOYER_PROMPT,
        DABS_SYSTEM_PROMPT,
        SUBAGENT_ANALYST,
        SUBAGENT_BUILDER,
        SUBAGENT_DEPLOYER,
    )
except ImportError:
    from dabs_copilot.prompts import (
        DAB_ANALYST_PROMPT,
        DAB_BUILDER_PROMPT,
        DAB_DEPLOYER_PROMPT,
        DABS_SYSTEM_PROMPT,
        SUBAGENT_ANALYST,
        SUBAGENT_BUILDER,
        SUBAGENT_DEPLOYER,
    )


class TestPromptSkillReferences:
    """Tests to verify skill references are included in prompts."""

    def test_analyst_prompt_has_skill_reference(self):
        """Analyst prompt should reference skills."""
        assert "Skill" in DAB_ANALYST_PROMPT
        assert "databricks-asset-bundles" in DAB_ANALYST_PROMPT

    def test_analyst_prompt_has_workload_classification(self):
        """Analyst prompt should include workload classification guidance."""
        assert "Workload Classification" in DAB_ANALYST_PROMPT
        assert "ETL" in DAB_ANALYST_PROMPT
        assert "ML" in DAB_ANALYST_PROMPT
        assert "DLT" in DAB_ANALYST_PROMPT
        assert "Apps" in DAB_ANALYST_PROMPT
        assert "Multi-team" in DAB_ANALYST_PROMPT

    def test_analyst_prompt_has_apps_tools(self):
        """Analyst prompt should reference apps tools."""
        assert "list_apps" in DAB_ANALYST_PROMPT
        assert "get_app" in DAB_ANALYST_PROMPT
        assert "get_app_deployment" in DAB_ANALYST_PROMPT

    def test_builder_prompt_has_skill_reference(self):
        """Builder prompt should reference skills."""
        assert "Skill" in DAB_BUILDER_PROMPT
        assert "databricks-asset-bundles" in DAB_BUILDER_PROMPT

    def test_builder_prompt_has_pattern_selection(self):
        """Builder prompt should include pattern selection guidance."""
        assert "Pattern Selection" in DAB_BUILDER_PROMPT
        assert "etl.md" in DAB_BUILDER_PROMPT
        assert "ml.md" in DAB_BUILDER_PROMPT
        assert "dlt.md" in DAB_BUILDER_PROMPT
        assert "apps.md" in DAB_BUILDER_PROMPT
        assert "multi-team.md" in DAB_BUILDER_PROMPT

    def test_builder_prompt_has_bundle_structure(self):
        """Builder prompt should include bundle structure guidance."""
        assert "Bundle Structure" in DAB_BUILDER_PROMPT
        assert "resources/" in DAB_BUILDER_PROMPT

    def test_builder_prompt_has_apps_bundle_section(self):
        """Builder prompt should include apps bundle guidance."""
        assert "For apps bundle" in DAB_BUILDER_PROMPT
        assert "resource bindings" in DAB_BUILDER_PROMPT

    def test_deployer_prompt_has_skill_reference(self):
        """Deployer prompt should reference skills."""
        assert "Skill" in DAB_DEPLOYER_PROMPT
        assert "databricks-asset-bundles" in DAB_DEPLOYER_PROMPT

    def test_deployer_prompt_has_best_practices(self):
        """Deployer prompt should include deployment best practices."""
        assert "Deployment Best Practices" in DAB_DEPLOYER_PROMPT
        assert "validate before deploy" in DAB_DEPLOYER_PROMPT

    def test_system_prompt_has_skills_section(self):
        """Main system prompt should have skills section."""
        assert "Skills Available" in DABS_SYSTEM_PROMPT
        assert "databricks-asset-bundles" in DABS_SYSTEM_PROMPT

    def test_system_prompt_references_all_patterns(self):
        """System prompt should reference all 5 skill patterns."""
        assert "ETL" in DABS_SYSTEM_PROMPT
        assert "ML" in DABS_SYSTEM_PROMPT
        assert "DLT" in DABS_SYSTEM_PROMPT
        assert "Apps" in DABS_SYSTEM_PROMPT
        assert "Multi-team" in DABS_SYSTEM_PROMPT

    def test_system_prompt_has_apps_direct_tools(self):
        """System prompt should reference apps direct tools."""
        assert "list_apps" in DABS_SYSTEM_PROMPT
        assert "get_app" in DABS_SYSTEM_PROMPT

    def test_system_prompt_includes_workload_type_in_workflow(self):
        """System prompt workflow should mention workload type."""
        assert "workload type" in DABS_SYSTEM_PROMPT


class TestSubagentConstants:
    """Tests for subagent name constants."""

    def test_subagent_names(self):
        """Verify subagent names are correct."""
        assert SUBAGENT_ANALYST == "dab-analyst"
        assert SUBAGENT_BUILDER == "dab-builder"
        assert SUBAGENT_DEPLOYER == "dab-deployer"

    def test_subagent_names_in_prompts(self):
        """Verify subagent names appear in system prompt."""
        assert SUBAGENT_ANALYST in DABS_SYSTEM_PROMPT
        assert SUBAGENT_BUILDER in DABS_SYSTEM_PROMPT
        assert SUBAGENT_DEPLOYER in DABS_SYSTEM_PROMPT


def run_manual_tests():
    """Run tests manually without pytest."""
    print("=" * 60)
    print("Running manual tests for prompts")
    print("=" * 60)

    # Test skill references
    print("\n1. Testing skill references in prompts...")

    assert "Skill" in DAB_ANALYST_PROMPT, "Analyst prompt missing Skill reference"
    assert "databricks-asset-bundles" in DAB_ANALYST_PROMPT, "Analyst missing skill name"
    print("   ✓ Analyst prompt has skill references")

    assert "Skill" in DAB_BUILDER_PROMPT, "Builder prompt missing Skill reference"
    assert "databricks-asset-bundles" in DAB_BUILDER_PROMPT, "Builder missing skill name"
    print("   ✓ Builder prompt has skill references")

    assert "Skill" in DAB_DEPLOYER_PROMPT, "Deployer prompt missing Skill reference"
    print("   ✓ Deployer prompt has skill references")

    assert "Skills Available" in DABS_SYSTEM_PROMPT, "System prompt missing Skills section"
    print("   ✓ System prompt has skills section")

    # Test workload patterns
    print("\n2. Testing workload pattern references...")

    for pattern in ["ETL", "ML", "DLT", "Apps", "Multi-team"]:
        assert pattern in DABS_SYSTEM_PROMPT, f"System prompt missing {pattern}"
    print("   ✓ System prompt references all 5 workload patterns")

    for ref in ["etl.md", "ml.md", "dlt.md", "apps.md", "multi-team.md"]:
        assert ref in DAB_BUILDER_PROMPT, f"Builder prompt missing {ref}"
    print("   ✓ Builder prompt references all 5 skill files")

    # Test apps tools
    print("\n3. Testing apps tool references...")

    for tool in ["list_apps", "get_app"]:
        assert tool in DAB_ANALYST_PROMPT, f"Analyst missing {tool}"
        assert tool in DABS_SYSTEM_PROMPT, f"System prompt missing {tool}"
    print("   ✓ Apps tools referenced in prompts")

    print("\n" + "=" * 60)
    print("All manual tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    run_manual_tests()
