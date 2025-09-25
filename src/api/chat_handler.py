import json
import uuid
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, AsyncGenerator

from claude_code_sdk import (
    AssistantMessage,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
)

try:
    # Try relative imports first (when run as module)
    from .models import ChatRequest, StreamMessage, ConversationState, ChatMessage, GeneratedFile
    from .claude_client import create_chat_client
except ImportError:
    # Fall back to absolute imports (when run directly)
    from models import ChatRequest, StreamMessage, ConversationState, ChatMessage, GeneratedFile
    from claude_client import create_chat_client

# In-memory storage for conversations (would use database in production)
conversations: Dict[str, ConversationState] = {}
generated_files: Dict[str, str] = {}

def generate_file_id(file_path: str) -> str:
    """Generate unique ID for file downloads"""
    file_id = str(uuid.uuid4())
    generated_files[file_id] = file_path
    return file_id

def get_or_create_conversation(conversation_id: str = None) -> ConversationState:
    """Get existing conversation or create new one"""
    if not conversation_id:
        conversation_id = str(uuid.uuid4())
    
    if conversation_id not in conversations:
        conversations[conversation_id] = ConversationState(
            conversation_id=conversation_id,
            messages=[],
            generated_files=[],
            context={},
            created_at=datetime.now(),
            last_activity=datetime.now()
        )
    
    return conversations[conversation_id]

async def stream_chat_response(request: ChatRequest) -> AsyncGenerator[str, None]:
    """Stream chat responses using Server-Sent Events format"""
    conversation = get_or_create_conversation(request.conversation_id)
    
    # Add user message to conversation
    user_message = ChatMessage(
        role="user",
        content=request.message,
        timestamp=datetime.now()
    )
    conversation.messages.append(user_message)
    conversation.last_activity = datetime.now()
    
    try:
        # Create Claude client and process message
        client = await create_chat_client()
        
        async with client:
            # Send initial response
            yield _format_sse_message({
                "type": "message",
                "content": f"🚀 Processing your request: {request.message}",
                "timestamp": datetime.now().isoformat()
            })
            
            # Query Claude with the user's message
            await client.query(request.message)
            
            assistant_content = []
            tools_used = []
            files_generated = []
            
            # Stream Claude's responses
            async for message in client.receive_messages():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            # Filter out raw tool result strings
                            text = block.text
                            if text and not text.startswith('{"type":') and not text.startswith('data:'):
                                assistant_content.append(text)
                                yield _format_sse_message({
                                    "type": "message",
                                    "content": text,
                                    "timestamp": datetime.now().isoformat()
                                })
                        elif isinstance(block, ToolUseBlock):
                            tools_used.append(block.name)
                            # Format tool name nicely
                            tool_display = block.name.replace('mcp__databricks-mcp__', '')
                            yield _format_sse_message({
                                "type": "tool_use",
                                "tool": tool_display,
                                "status": "starting",
                                "inputs": block.input if isinstance(block.input, dict) else {}
                            })
                
                # Handle tool results and file generation
                elif hasattr(message, "content"):
                    for block in message.content:
                        if isinstance(block, ToolResultBlock):
                            tool_name = getattr(block, "name", "")

                            # Check if this tool generated files
                            if _tool_generates_files(tool_name) and block.content:
                                # Extract content string from ToolResultBlock
                                content_str = ""
                                if hasattr(block.content, 'text'):
                                    content_str = block.content.text
                                elif isinstance(block.content, str):
                                    content_str = block.content
                                elif isinstance(block.content, list) and block.content:
                                    # Handle list of content blocks
                                    for item in block.content:
                                        if hasattr(item, 'text'):
                                            content_str += item.text + "\n"

                                file_path = _extract_file_path(content_str)
                                if file_path and Path(file_path).exists():
                                    file_id = generate_file_id(file_path)
                                    filename = Path(file_path).name
                                    download_url = f"/api/files/{file_id}"

                                    files_generated.append(filename)

                                    # Add to conversation state
                                    generated_file = GeneratedFile(
                                        filename=filename,
                                        file_path=file_path,
                                        download_url=download_url,
                                        created_at=datetime.now()
                                    )
                                    conversation.generated_files.append(generated_file)

                                    yield _format_sse_message({
                                        "type": "file_generated",
                                        "filename": filename,
                                        "download_url": download_url
                                    })
                
                if isinstance(message, ResultMessage):
                    # Conversation finished
                    break
            
            # Add assistant message to conversation history
            assistant_message = ChatMessage(
                role="assistant",
                content=" ".join(assistant_content),
                timestamp=datetime.now(),
                tool_uses=tools_used,
                files_generated=files_generated
            )
            conversation.messages.append(assistant_message)
            
            # Send completion message
            yield _format_sse_message({
                "type": "complete",
                "conversation_id": conversation.conversation_id,
                "files_generated": len(files_generated)
            })
    
    except Exception as e:
        # Send error message
        yield _format_sse_message({
            "type": "error",
            "content": f"Error processing request: {str(e)}",
            "timestamp": datetime.now().isoformat()
        })

def _format_sse_message(data: Dict[str, Any]) -> str:
    """Format message for Server-Sent Events"""
    return f"data: {json.dumps(data)}\n\n"

def _tool_generates_files(tool_name: str) -> bool:
    """Check if a tool typically generates downloadable files"""
    file_generating_tools = [
        "generate_bundle",
        "generate_bundle_from_job", 
        "export_notebook",
        "create_tests"
    ]
    return any(gen_tool in tool_name for gen_tool in file_generating_tools)

def _extract_file_path(tool_result: str) -> str:
    """Extract file path from tool result content"""
    import json
    import re

    # Try to parse as JSON first (for structured MCP responses)
    try:
        if tool_result.strip().startswith('{'):
            data = json.loads(tool_result)
            # Look for common file path fields
            for key in ['output_path', 'file_path', 'path', 'bundle_path']:
                if key in data and data[key]:
                    return data[key]
    except:
        pass

    # Fallback to text parsing
    lines = tool_result.split('\n')
    for line in lines:
        # Look for patterns like "Created bundle at: /path/to/bundle.zip"
        match = re.search(r'(?:created|generated|saved|written|output).*?([\w\-\/\.]+\.(?:zip|yml|yaml))', line, re.IGNORECASE)
        if match:
            return match.group(1)

        # Look for any path ending with .zip or .yml
        if 'bundle' in line.lower() and ('.zip' in line or '.yml' in line or '.yaml' in line):
            words = line.split()
            for word in words:
                if '/' in word and word.endswith(('.zip', '.yml', '.yaml')):
                    return word.strip('",')
    return ""