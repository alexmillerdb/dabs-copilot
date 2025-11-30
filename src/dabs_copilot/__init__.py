"""
DABs Copilot - Interactive Databricks Asset Bundle Generator

A lightweight SDK for generating, validating, and deploying Databricks Asset Bundles
using Claude Agent SDK with specialized subagents and skills.

Usage:
    # Interactive multi-turn
    async with DABsAgent() as agent:
        async for msg in agent.chat("Generate bundle from job 123"):
            print(msg)

    # One-shot
    async for msg in generate_bundle("Generate bundle from job 123"):
        print(msg)
"""

from .agent import (
    DABsAgent,
    generate_bundle,
    MCP_TOOLS,
    DESTRUCTIVE_TOOLS,
    ALLOWED_TOOLS,
    DABS_AGENTS,
    DABS_SYSTEM_PROMPT,
    get_mcp_config,
    get_project_root,
)

__version__ = "1.1.0"  # Added skills and subagents
__all__ = [
    # Main agent
    "DABsAgent",
    # One-shot function
    "generate_bundle",
    # Tool lists
    "MCP_TOOLS",
    "DESTRUCTIVE_TOOLS",
    "ALLOWED_TOOLS",
    # Subagent definitions
    "DABS_AGENTS",
    # Configuration helpers
    "DABS_SYSTEM_PROMPT",
    "get_mcp_config",
    "get_project_root",
]
