from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
from pathlib import Path
from datetime import datetime
from typing import Dict
from dotenv import load_dotenv

# Load environment variables from project root .env file
project_root = Path(__file__).parent.parent.parent  # Go up from src/api to project root
dotenv_path = project_root / ".env"
load_dotenv(dotenv_path)

try:
    # Try relative imports first (when run as module)
    from .models import ChatRequest
    from .chat_handler import stream_chat_response, generated_files
except ImportError:
    # Fall back to absolute imports (when run directly)
    from models import ChatRequest
    from chat_handler import stream_chat_response, generated_files

app = FastAPI(title="DAB Generator Chat API", version="1.0.0")

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get the directory where this main.py file is located
current_dir = Path(__file__).parent
static_dir = current_dir / "static"

# Serve static files
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Serve the main page at root
@app.get("/")
async def read_root():
    return FileResponse(str(static_dir / "index.html"))

@app.get("/test")
async def read_test():
    return FileResponse(str(static_dir / "test.html"))

@app.post("/api/test-chat")
async def test_chat_endpoint(request: ChatRequest):
    """Simple test endpoint without Claude integration"""
    async def mock_response():
        import json
        import asyncio
        from datetime import datetime
        
        # Mock streaming response
        messages = [
            {"type": "message", "content": "🚀 Processing your request: " + request.message, "timestamp": datetime.now().isoformat()},
            {"type": "message", "content": "This is a test response without Claude integration.", "timestamp": datetime.now().isoformat()},
            {"type": "tool_use", "tool": "mock_tool", "status": "starting"},
            {"type": "message", "content": "✅ Test completed successfully!", "timestamp": datetime.now().isoformat()},
            {"type": "complete", "conversation_id": "test-123", "files_generated": 0}
        ]
        
        for msg in messages:
            yield f"data: {json.dumps(msg)}\n\n"
            await asyncio.sleep(0.5)  # Simulate processing time
    
    return StreamingResponse(
        mock_response(),
        media_type="text/plain", 
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """Handle chat requests with streaming responses"""
    # Check if required environment is configured
    claude_key = os.getenv("CLAUDE_API_KEY")
    if not claude_key:
        async def error_response():
            import json
            from datetime import datetime
            error_msg = {
                "type": "error",
                "content": "Claude API key not configured. Please set CLAUDE_API_KEY environment variable.",
                "timestamp": datetime.now().isoformat()
            }
            yield f"data: {json.dumps(error_msg)}\n\n"
        
        return StreamingResponse(
            error_response(),
            media_type="text/plain",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )
    
    return StreamingResponse(
        stream_chat_response(request),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )

@app.get("/api/health")
async def health_check():
    """Health check endpoint to verify API and Databricks connectivity"""
    try:
        # Check if required environment variables are set
        databricks_profile = os.getenv("DATABRICKS_CONFIG_PROFILE", "")
        databricks_host = os.getenv("DATABRICKS_HOST", "")
        claude_api_key = os.getenv("CLAUDE_API_KEY", "")
        
        return {
            "status": "healthy",
            "databricks_connected": bool(databricks_profile and databricks_host),
            "claude_configured": bool(claude_api_key),
            "mcp_tools": 18,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@app.get("/api/files/{file_id}")
async def download_file(file_id: str):
    """Download generated bundle files"""
    if file_id not in generated_files:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_path = generated_files[file_id]
    if not Path(file_path).exists():
        raise HTTPException(status_code=404, detail="File no longer available")
    
    return FileResponse(
        file_path,
        media_type='application/octet-stream',
        filename=Path(file_path).name
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)