# from claude_code_sdk import query, ClaudeCodeOptions
# import asyncio

# async def use_local_mcp():
#     options = ClaudeCodeOptions(
#         mcp_config=".mcp.json",
#         # allowed_tools=["mcp__databricks-mcp__your_tool_name"]  # Replace with actual tool names
#     )
    
#     async for message in query(
#         prompt="List all tools available",
#         options=options
#     ):
#         print(message)

# asyncio.run(use_local_mcp())
from claude_code_sdk import query, ClaudeCodeOptions
import asyncio

async def use_direct_mcp():
    options = ClaudeCodeOptions(
        mcp_servers={
            "databricks-mcp": {
                "command": "python",
                "args": ["mcp/server/main.py"]
            }
        },
        # allowed_tools=["mcp__databricks-mcp__your_tool_name"]
    )
    
    async for message in query(
        prompt="List all tools available",
        options=options
    ):
        print(message)

asyncio.run(use_direct_mcp())