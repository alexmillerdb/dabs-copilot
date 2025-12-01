#!/usr/bin/env python3
"""
Interactive REPL for testing DABsAgent multi-turn conversations.

Uses custom tools mode (in-process SDK MCP server) - no external MCP server required.

Usage:
    cd src/dabs_copilot && python interactive_test.py
    # or
    python -m src.dabs_copilot.interactive_test
"""
import asyncio
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

# Handle both package and standalone imports
try:
    from .agent import DABsAgent, get_custom_tool_names
except ImportError:
    from agent import DABsAgent, get_custom_tool_names

load_dotenv()


def print_message(msg):
    """Format and print SDK messages."""
    if isinstance(msg, AssistantMessage):
        if hasattr(msg, "content") and msg.content:
            for block in msg.content:
                if isinstance(block, TextBlock):
                    print(f"Agent: {block.text}")
                elif isinstance(block, ToolUseBlock):
                    print(f"  → Tool: {block.name}")
                    if hasattr(block, "input") and block.input:
                        # Show abbreviated input for readability
                        input_str = str(block.input)
                        if len(input_str) > 100:
                            input_str = input_str[:100] + "..."
                        print(f"    Input: {input_str}")
    elif isinstance(msg, ResultMessage):
        print("✓ Turn complete")
        if hasattr(msg, "total_cost_usd") and msg.total_cost_usd:
            print(f"  Cost: ${msg.total_cost_usd:.4f}")
    elif isinstance(msg, SystemMessage):
        # Optionally show system messages for debugging
        if hasattr(msg, "subtype"):
            pass  # print(f"  [System: {msg.subtype}]")
    elif isinstance(msg, UserMessage):
        pass  # Skip user messages (we already printed the prompt)


async def confirm_action(tool_name: str, tool_input: dict) -> bool:
    """Prompt user before destructive actions."""
    print(f"\n⚠️  Destructive action requested: {tool_name}")
    print(f"   Input: {tool_input}")
    try:
        response = input("   Proceed? [y/N]: ")
        return response.lower() == "y"
    except EOFError:
        return False


def print_help():
    """Print available commands."""
    print("""
Commands:
  /quit, /exit  - Exit the REPL
  /reset        - Start a new session (clears conversation history)
  /tools        - List available tools
  /help         - Show this help message
""")


def print_tools():
    """Print available tools."""
    tools = get_custom_tool_names()
    print(f"\nAvailable tools ({len(tools)}):")
    for tool in sorted(tools):
        # Strip the mcp__databricks__ prefix for readability
        short_name = tool.replace("mcp__databricks__", "")
        print(f"  - {short_name}")
    print()


async def repl():
    """Main REPL loop with multi-turn support."""
    print("=" * 50)
    print("DABs Copilot - Interactive Test")
    print("=" * 50)
    print("Tool mode: custom (in-process)")
    print(f"Available tools: {len(get_custom_tool_names())}")
    print("Type /help for commands, /quit to exit")
    print()

    agent = None
    try:
        while True:
            # Create agent if needed
            if agent is None:
                agent = DABsAgent(
                    tool_mode="custom",
                    confirm_destructive=confirm_action
                )
                await agent.__aenter__()
                print("Session started.\n")

            # Get user input
            try:
                user_input = input("You: ").strip()
            except EOFError:
                print("\nGoodbye!")
                break
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break

            if not user_input:
                continue

            # Handle commands
            if user_input.startswith("/"):
                cmd = user_input.lower()
                if cmd in ("/quit", "/exit"):
                    print("Goodbye!")
                    break
                elif cmd == "/reset":
                    if agent:
                        await agent.__aexit__(None, None, None)
                        agent = None
                    print("Session reset. Starting fresh...\n")
                    continue
                elif cmd == "/tools":
                    print_tools()
                    continue
                elif cmd == "/help":
                    print_help()
                    continue
                else:
                    print(f"Unknown command: {user_input}")
                    print_help()
                    continue

            # Send message and stream response
            print("-" * 40)
            try:
                async for msg in agent.chat(user_input):
                    print_message(msg)
            except Exception as e:
                print(f"Error: {e}")
            print()

    finally:
        if agent:
            await agent.__aexit__(None, None, None)


def main():
    """Entry point."""
    try:
        asyncio.run(repl())
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(0)


if __name__ == "__main__":
    main()
