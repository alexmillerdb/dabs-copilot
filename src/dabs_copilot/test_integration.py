"""
Local integration test for DABsAgent.

Run with: python -m src.dabs_copilot.test_integration
         or: cd src/dabs_copilot && python test_integration.py

Tests include:
- Basic connectivity and MCP tool access
- Skills loading (databricks-asset-bundles)
- Subagent invocation (analyst, builder, deployer)
- Data listing (jobs, apps, pipelines via SQL)
- Enhanced notebook analysis (complexity_score, dependencies, data_sources)
- Analysis caching behavior
- Hybrid analysis workflow (deterministic + semantic)
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

from claude_agent_sdk import (
    AssistantMessage,
    SystemMessage,
    UserMessage,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)

# Handle both direct execution and pytest from project root
try:
    from agent import (
        DABsAgent,
        MCP_TOOLS,
        MCP_DESTRUCTIVE_TOOLS,
        DABS_AGENTS,
        CUSTOM_TOOLS_SERVER,
    )
    from prompts import (
        SUBAGENT_ANALYST,
        SUBAGENT_BUILDER,
        SUBAGENT_DEPLOYER,
    )
except ImportError:
    from dabs_copilot.agent import (
        DABsAgent,
        MCP_TOOLS,
        MCP_DESTRUCTIVE_TOOLS,
        DABS_AGENTS,
        CUSTOM_TOOLS_SERVER,
    )
    from dabs_copilot.prompts import (
        SUBAGENT_ANALYST,
        SUBAGENT_BUILDER,
        SUBAGENT_DEPLOYER,
    )

load_dotenv()


def print_message(msg):
    """Print a message in a human-readable format."""
    if isinstance(msg, AssistantMessage):
        if hasattr(msg, "content") and msg.content:
            for block in msg.content:
                if isinstance(block, TextBlock):
                    print(f"Agent: {block.text}")
                elif isinstance(block, ToolUseBlock):
                    # Check if this is a subagent invocation (Task tool)
                    if block.name == "Task":
                        subagent = block.input.get("subagent_type", "unknown") if block.input else "unknown"
                        description = block.input.get("description", "") if block.input else ""
                        print(f"  Subagent: {subagent}")
                        if description:
                            print(f"    Task: {description}")
                    else:
                        print(f"  → Tool: {block.name}")
                        if hasattr(block, "input"):
                            print(f"    Input: {block.input}")
    elif isinstance(msg, ResultMessage):
        print("✓ Result received")
        if hasattr(msg, "result") and msg.result:
            print(f"  Result: {str(msg.result)[:200]}...")
    elif isinstance(msg, SystemMessage):
        if hasattr(msg, "subtype"):
            print(f"  [System: {msg.subtype}]")
    elif isinstance(msg, UserMessage):
        pass  # Skip user messages (we already printed the prompt)
    else:
        # Fallback: print class name and any useful attributes
        print(f"  [{type(msg).__name__}]")


async def confirm_action(tool_name: str, tool_input: dict) -> bool:
    """Prompt user before destructive actions."""
    print(f"\n⚠️  Destructive action requested: {tool_name}")
    print(f"   Input: {tool_input}")
    response = input("   Proceed? [y/N]: ")
    return response.lower() == "y"


async def test_health_check():
    """Test basic connectivity and health check."""
    print("\n" + "=" * 60)
    print("TEST 1: Health Check")
    print("=" * 60)

    try:
        async with DABsAgent(confirm_destructive=confirm_action) as agent:
            prompt = "Check if the Databricks connection is healthy using the health tool. Return the workspace URL and user."
            print(f"\nYou: {prompt}")
            print("-" * 40)

            async for msg in agent.chat(prompt):
                print_message(msg)

            print("\n✓ Health check test complete")

    except Exception as e:
        print(f"✗ Error: {e}")
        raise


async def test_list_jobs():
    """Test listing 5 jobs."""
    print("\n" + "=" * 60)
    print("TEST 2: List Jobs (limit 5)")
    print("=" * 60)

    try:
        async with DABsAgent(confirm_destructive=confirm_action) as agent:
            prompt = "List 5 jobs from the workspace using the list_jobs tool with limit=5. Show job ID, name, and creator for each."
            print(f"\nYou: {prompt}")
            print("-" * 40)

            async for msg in agent.chat(prompt):
                print_message(msg)

            print("\n✓ List jobs test complete")

    except Exception as e:
        print(f"✗ Error: {e}")
        raise


async def test_list_apps():
    """Test listing 5 apps."""
    print("\n" + "=" * 60)
    print("TEST 3: List Apps (limit 5)")
    print("=" * 60)

    try:
        async with DABsAgent(confirm_destructive=confirm_action) as agent:
            prompt = "List 5 Databricks Apps from the workspace using the list_apps tool with limit=5. Show app name, URL, and status for each."
            print(f"\nYou: {prompt}")
            print("-" * 40)

            async for msg in agent.chat(prompt):
                print_message(msg)

            print("\n✓ List apps test complete")

    except Exception as e:
        print(f"✗ Error: {e}")
        raise


async def test_list_pipelines():
    """Test listing 5 DLT pipelines using list_pipelines tool."""
    print("\n" + "=" * 60)
    print("TEST 4: List Pipelines (limit 5)")
    print("=" * 60)

    try:
        async with DABsAgent(confirm_destructive=confirm_action) as agent:
            prompt = "List 5 DLT pipelines from the workspace using the list_pipelines tool with limit=5. Show pipeline ID, name, creator, and state for each."
            print(f"\nYou: {prompt}")
            print("-" * 40)

            async for msg in agent.chat(prompt):
                print_message(msg)

            print("\n✓ List pipelines test complete")

    except Exception as e:
        print(f"✗ Error: {e}")
        raise


async def test_skill_loading():
    """Test loading the databricks-asset-bundles skill."""
    print("\n" + "=" * 60)
    print("TEST 5: Skill Loading")
    print("=" * 60)

    try:
        async with DABsAgent(confirm_destructive=confirm_action) as agent:
            prompt = """Load the databricks-asset-bundles skill using the Skill tool.
Then briefly describe what patterns are available (ETL, ML, DLT, Apps, Multi-team).
Just list the pattern names and one-line descriptions."""
            print(f"\nYou: {prompt}")
            print("-" * 40)

            async for msg in agent.chat(prompt):
                print_message(msg)

            print("\n✓ Skill loading test complete")

    except Exception as e:
        print(f"✗ Error: {e}")
        raise


async def test_subagent_analyst():
    """Test the analyst subagent."""
    print("\n" + "=" * 60)
    print(f"TEST 6: Subagent - {SUBAGENT_ANALYST}")
    print("=" * 60)

    try:
        async with DABsAgent(confirm_destructive=confirm_action) as agent:
            prompt = f"""Use the Task tool to spawn the '{SUBAGENT_ANALYST}' subagent with this task:
"List 3 jobs from the workspace and identify their workload types (ETL, ML, DLT, or other)."

Return the subagent's analysis results."""
            print(f"\nYou: {prompt}")
            print("-" * 40)

            async for msg in agent.chat(prompt):
                print_message(msg)

            print(f"\n✓ {SUBAGENT_ANALYST} test complete")

    except Exception as e:
        print(f"✗ Error: {e}")
        raise


async def test_subagent_builder():
    """Test the builder subagent."""
    print("\n" + "=" * 60)
    print(f"TEST 7: Subagent - {SUBAGENT_BUILDER}")
    print("=" * 60)

    try:
        async with DABsAgent(confirm_destructive=confirm_action) as agent:
            prompt = f"""Use the Task tool to spawn the '{SUBAGENT_BUILDER}' subagent with this task:
"Load the databricks-asset-bundles skill and describe the recommended bundle structure for a simple ETL job with 2 tasks."

Return the subagent's recommendations (do NOT generate actual YAML)."""
            print(f"\nYou: {prompt}")
            print("-" * 40)

            async for msg in agent.chat(prompt):
                print_message(msg)

            print(f"\n✓ {SUBAGENT_BUILDER} test complete")

    except Exception as e:
        print(f"✗ Error: {e}")
        raise


async def test_subagent_deployer():
    """Test the deployer subagent."""
    print("\n" + "=" * 60)
    print(f"TEST 8: Subagent - {SUBAGENT_DEPLOYER}")
    print("=" * 60)

    try:
        async with DABsAgent(confirm_destructive=confirm_action) as agent:
            prompt = f"""Use the Task tool to spawn the '{SUBAGENT_DEPLOYER}' subagent with this task:
"Load the databricks-asset-bundles skill and explain the deployment best practices for a dev target."

Return the subagent's deployment guidance (do NOT execute any deployment)."""
            print(f"\nYou: {prompt}")
            print("-" * 40)

            async for msg in agent.chat(prompt):
                print_message(msg)

            print(f"\n✓ {SUBAGENT_DEPLOYER} test complete")

    except Exception as e:
        print(f"✗ Error: {e}")
        raise


async def test_interactive():
    """Test interactive multi-turn conversation."""
    print("\n" + "=" * 60)
    print("TEST 9: Interactive Multi-turn Conversation")
    print("=" * 60)

    try:
        async with DABsAgent(confirm_destructive=confirm_action) as agent:
            # First turn
            prompt1 = "What MCP tools do you have available? Just list the tool names grouped by category."
            print(f"\nYou: {prompt1}")
            print("-" * 40)

            async for msg in agent.chat(prompt1):
                print_message(msg)

            print(f"\nSession ID: {agent.session_id}")

            # Second turn - follow-up referencing previous context
            prompt2 = "From those tools, which ones are for Databricks Apps? List them."
            print(f"\nYou: {prompt2}")
            print("-" * 40)

            async for msg in agent.chat(prompt2):
                print_message(msg)

            print("\n✓ Interactive test complete")

    except Exception as e:
        print(f"✗ Error: {e}")
        raise


async def test_enhanced_analysis():
    """Test enhanced notebook analysis with new fields (complexity_score, dependencies, etc.)."""
    print("\n" + "=" * 60)
    print("TEST 10: Enhanced Notebook Analysis")
    print("=" * 60)

    try:
        async with DABsAgent(confirm_destructive=confirm_action) as agent:
            prompt = """Use the analyze_notebook tool to analyze a notebook from the workspace.
First, list notebooks in /Workspace/Users/ (limit to first few) and pick one Python notebook.
Then call analyze_notebook on it.

Report these fields from the analysis result:
- path and file_type
- workflow_type and detection_confidence
- complexity_score and complexity_factors
- dependencies (show categories: standard_library, third_party, databricks)
- data_sources (input_tables, output_tables if any)
- databricks_features (widgets, notebook_calls)
- cached status"""
            print(f"\nYou: {prompt}")
            print("-" * 40)

            async for msg in agent.chat(prompt):
                print_message(msg)

            print("\n✓ Enhanced analysis test complete")

    except Exception as e:
        print(f"✗ Error: {e}")
        raise


async def test_analysis_caching():
    """Test analysis caching behavior with skip_cache parameter."""
    print("\n" + "=" * 60)
    print("TEST 11: Analysis Caching")
    print("=" * 60)

    try:
        async with DABsAgent(confirm_destructive=confirm_action) as agent:
            prompt = """Test the analysis caching feature:

1. First, list notebooks in /Workspace/Users/ and pick one notebook path.
2. Call analyze_notebook on that path (first call - should have cached: false).
3. Call analyze_notebook on the SAME path again (second call - should have cached: true).

Report for each call:
- The notebook path used
- The 'cached' field value (true/false)
- The 'cache_key' field

Confirm whether caching is working (second call should show cached: true)."""
            print(f"\nYou: {prompt}")
            print("-" * 40)

            async for msg in agent.chat(prompt):
                print_message(msg)

            print("\n✓ Analysis caching test complete")

    except Exception as e:
        print(f"✗ Error: {e}")
        raise


async def test_hybrid_analysis_workflow():
    """Test hybrid analysis workflow via analyst subagent."""
    print("\n" + "=" * 60)
    print(f"TEST 12: Hybrid Analysis Workflow ({SUBAGENT_ANALYST})")
    print("=" * 60)

    try:
        async with DABsAgent(confirm_destructive=confirm_action) as agent:
            prompt = f"""Use the Task tool to spawn the '{SUBAGENT_ANALYST}' subagent with this task:
"Perform a hybrid analysis on a notebook from /Workspace/Users/:
1. Use analyze_notebook to get deterministic analysis including complexity_score
2. Report the complexity_score value
3. If complexity_score >= 0.5, provide semantic insights about:
   - Primary intent of the notebook
   - Data flow pattern
   - Any quality concerns
4. If complexity_score < 0.5, explain that deterministic analysis is sufficient

List the notebook path analyzed and the analysis approach taken."

Return the subagent's complete analysis report."""
            print(f"\nYou: {prompt}")
            print("-" * 40)

            async for msg in agent.chat(prompt):
                print_message(msg)

            print("\n✓ Hybrid analysis workflow test complete")

    except Exception as e:
        print(f"✗ Error: {e}")
        raise


async def run_quick_tests():
    """Run quick tests only (health, jobs, apps)."""
    await test_health_check()
    await test_list_jobs()
    await test_list_apps()


async def run_data_tests():
    """Run data listing tests (jobs, apps, pipelines)."""
    await test_list_jobs()
    await test_list_apps()
    await test_list_pipelines()


async def run_skill_tests():
    """Run skill-related tests."""
    await test_skill_loading()


async def run_subagent_tests():
    """Run all subagent tests."""
    await test_subagent_analyst()
    await test_subagent_builder()
    await test_subagent_deployer()


async def run_analysis_tests():
    """Run analysis-related tests (enhanced analysis, caching, hybrid workflow)."""
    await test_enhanced_analysis()
    await test_analysis_caching()
    await test_hybrid_analysis_workflow()


async def run_all_tests():
    """Run all integration tests."""
    await test_health_check()
    await test_list_jobs()
    await test_list_apps()
    await test_list_pipelines()
    await test_skill_loading()
    await test_subagent_analyst()
    await test_subagent_builder()
    await test_subagent_deployer()
    await test_interactive()
    await test_enhanced_analysis()
    await test_analysis_caching()
    await test_hybrid_analysis_workflow()


async def main():
    print("=" * 60)
    print("DABs Copilot Agent - Integration Test Suite")
    print("=" * 60)

    print(f"\nConfiguration:")
    print(f"  MCP Tools available: {len(MCP_TOOLS)}")
    print(f"  Destructive tools: {len(MCP_DESTRUCTIVE_TOOLS)}")
    print(f"  Subagents defined: {len(DABS_AGENTS)}")
    print(f"    - {SUBAGENT_ANALYST}")
    print(f"    - {SUBAGENT_BUILDER}")
    print(f"    - {SUBAGENT_DEPLOYER}")
    print(f"  Custom tools server: {CUSTOM_TOOLS_SERVER}")

    # Check environment
    mcp_url = os.getenv("DABS_MCP_SERVER_URL")
    if mcp_url:
        print(f"  MCP Server URL: {mcp_url}")
    else:
        print("  MCP Server: Local subprocess mode")

    # Parse command line args for test selection
    test_suite = "all"
    if len(sys.argv) > 1:
        test_suite = sys.argv[1].lower()

    print(f"\nTest suite: {test_suite}")
    print("\nAvailable test suites:")
    print("  all       - Run all 12 tests (default)")
    print("  quick     - Health, jobs, apps only (3 tests)")
    print("  data      - Jobs, apps, pipelines (3 tests)")
    print("  skills    - Skill loading test (1 test)")
    print("  subagents - All 3 subagent tests")
    print("  analysis  - Enhanced analysis, caching, hybrid workflow (3 tests)")
    print("  interactive - Multi-turn conversation test")

    # Run selected tests
    try:
        match test_suite:
            case "quick":
                await run_quick_tests()
            case "data":
                await run_data_tests()
            case "skills":
                await run_skill_tests()
            case "subagents":
                await run_subagent_tests()
            case "analysis":
                await run_analysis_tests()
            case "interactive":
                await test_interactive()
            case _:
                await run_all_tests()

        print("\n" + "=" * 60)
        print("All integration tests passed!")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
