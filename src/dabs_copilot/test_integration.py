"""
Local integration test for DABsAgent.

Run with: python -m src.dabs_copilot.test_integration
         or: cd src/dabs_copilot && python test_integration.py
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

from agent import DABsAgent, MCP_TOOLS, MCP_DESTRUCTIVE_TOOLS, DABS_AGENTS, CUSTOM_TOOLS_SERVER

load_dotenv()


def print_message(msg):
    """Print a message in a human-readable format."""
    if isinstance(msg, AssistantMessage):
        if hasattr(msg, "content") and msg.content:
            for block in msg.content:
                if isinstance(block, TextBlock):
                    print(f"Agent: {block.text}")
                elif isinstance(block, ToolUseBlock):
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


async def test_interactive():
    """Test interactive multi-turn conversation."""
    print("\n" + "=" * 60)
    print("TEST: Interactive DABsAgent")
    print("=" * 60)

    try:
        async with DABsAgent(confirm_destructive=confirm_action) as agent:
            # First turn
            prompt1 = "What MCP tools do you have available? Just list the tool names."
            print(f"\nYou: {prompt1}")
            print("-" * 40)

            async for msg in agent.chat(prompt1):
                print_message(msg)

            print(f"\nSession ID: {agent.session_id}")

            # Second turn - follow-up
            prompt2 = "Now check if the Databricks connection is healthy using the health tool."
            print(f"\nYou: {prompt2}")
            print("-" * 40)

            async for msg in agent.chat(prompt2):
                print_message(msg)

            print("\n✓ Interactive test complete")

    except Exception as e:
        print(f"✗ Error: {e}")
        raise


async def main():
    print("=" * 60)
    print("DABs Copilot Agent - Integration Test")
    print("=" * 60)

    print(f"\nMCP Tools available: {len(MCP_TOOLS)}")
    print(f"Destructive tools (MCP mode): {len(MCP_DESTRUCTIVE_TOOLS)}")
    print(f"Subagents defined: {len(DABS_AGENTS)}")
    print(f"Custom tools server: {CUSTOM_TOOLS_SERVER}")

    # Check environment
    mcp_url = os.getenv("DABS_MCP_SERVER_URL")
    if mcp_url:
        print(f"MCP Server URL: {mcp_url}")
    else:
        print("MCP Server: Local subprocess mode")

    # Run tests
    try:
        await test_interactive()

        print("\n" + "=" * 60)
        print("All integration tests passed!")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nTest failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
