from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime
    tool_uses: List[str] = []
    files_generated: List[str] = []

class GeneratedFile(BaseModel):
    filename: str
    file_path: str
    download_url: str
    created_at: datetime

class ConversationState(BaseModel):
    conversation_id: str
    messages: List[ChatMessage]
    generated_files: List[GeneratedFile]
    context: Dict[str, Any] = {}
    created_at: datetime
    last_activity: datetime

class StreamMessage(BaseModel):
    type: str  # "message", "tool_use", "file_generated", "error"
    content: Optional[str] = None
    timestamp: Optional[datetime] = None
    tool: Optional[str] = None
    status: Optional[str] = None
    inputs: Optional[Dict[str, Any]] = None
    filename: Optional[str] = None
    download_url: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    databricks_connected: bool
    claude_configured: bool
    mcp_tools: int
    timestamp: str