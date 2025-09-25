#!/usr/bin/env python3
"""
Streamlit-based DAB Generator Frontend
Simple, reliable alternative to the complex FastAPI + JS frontend
"""

import streamlit as st
import asyncio
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import json
from typing import Any

# Load environment variables
project_root = Path(__file__).parent.parent.parent
dotenv_path = project_root / ".env"
load_dotenv(dotenv_path)

from claude_code_sdk import (
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
    ResultMessage,
)

# Try importing the client
try:
    from claude_client import create_chat_client
    CLIENT_AVAILABLE = True
except ImportError as e:
    CLIENT_AVAILABLE = False
    CLIENT_ERROR = str(e)

# Streamlit page config
st.set_page_config(
    page_title="DAB Generator",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .stApp > header {
        background-color: transparent;
    }
    .main-header {
        background: linear-gradient(90deg, #FF6B35 0%, #F7931E 100%);
        color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 2rem;
        text-align: center;
    }
    .tool-call {
        background: #e3f2fd;
        border-left: 4px solid #2196f3;
        padding: 0.5rem;
        margin: 0.5rem 0;
        border-radius: 0.25rem;
    }
    .success-message {
        background: #e8f5e8;
        border-left: 4px solid #4caf50;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 0.25rem;
    }
    .error-message {
        background: #ffebee;
        border-left: 4px solid #f44336;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 0.25rem;
    }
    .download-button {
        background: #4caf50;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 0.25rem;
        text-decoration: none;
        display: inline-block;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

def init_session_state():
    """Initialize session state variables"""
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'conversation_id' not in st.session_state:
        st.session_state.conversation_id = None
    if 'processing' not in st.session_state:
        st.session_state.processing = False
    if 'generated_files' not in st.session_state:
        st.session_state.generated_files = []

def check_environment():
    """Check if environment is properly configured"""
    claude_key = os.getenv("CLAUDE_API_KEY")
    databricks_host = os.getenv("DATABRICKS_HOST")
    databricks_profile = os.getenv("DATABRICKS_CONFIG_PROFILE", "DEFAULT")

    return {
        'claude_configured': bool(claude_key),
        'databricks_host': databricks_host,
        'databricks_profile': databricks_profile,
        'client_available': CLIENT_AVAILABLE
    }

def display_header():
    """Display the main header"""
    st.markdown("""
    <div class="main-header">
        <h1>🚀 Databricks Asset Bundle Generator</h1>
        <p>Transform your Databricks jobs and workspace code into production-ready bundles</p>
    </div>
    """, unsafe_allow_html=True)

def display_sidebar():
    """Display the sidebar with configuration and examples"""
    with st.sidebar:
        st.header("🔧 Configuration")

        # Environment status
        env = check_environment()

        st.subheader("Environment Status")
        st.write("🔑 Claude API:", "✅ Ready" if env['claude_configured'] else "❌ Missing")
        st.write("🏢 Databricks Host:", env['databricks_host'] or "❌ Not set")
        st.write("👤 Profile:", env['databricks_profile'])
        st.write("🔌 Client:", "✅ Ready" if env['client_available'] else "❌ Error")

        if not env['client_available']:
            st.error(f"Client Error: {CLIENT_ERROR if 'CLIENT_ERROR' in globals() else 'Unknown'}")

        st.divider()

        # Example prompts
        st.subheader("💡 Example Prompts")

        examples = [
            "Generate a bundle from job 662067900958232",
            "List workspace files in /Workspace/Users/alex.miller",
            "Create a bundle from my ML training pipeline",
            "Generate tests for my streaming job bundle"
        ]

        for i, example in enumerate(examples):
            if st.button(f"📋 Try: {example[:30]}...", key=f"example_{i}"):
                st.session_state.selected_prompt = example
                st.rerun()

        st.divider()

        # Generated files
        if st.session_state.generated_files:
            st.subheader("📁 Generated Files")
            for file_info in st.session_state.generated_files:
                st.write(f"📄 {file_info['name']}")
                if st.button(f"⬇️ Download", key=f"dl_{file_info['name']}"):
                    st.info("Download functionality would be implemented here")

def _to_str(content: Any) -> str:
    if hasattr(content, 'text'):
        return content.text
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if hasattr(item, 'text'):
                parts.append(item.text)
        return "\n".join(parts)
    return str(content)

async def process_chat_message(message: str):
    """Process a chat message using Claude Code SDK"""
    if not CLIENT_AVAILABLE:
        st.error("Claude Code client is not available. Please check your configuration.")
        return

    try:
        # Create client
        client = await create_chat_client()

        # Create message containers
        progress_container = st.container()

        with progress_container:
            with st.spinner("🤖 Processing your request..."):

                async with client:
                    # Send query
                    await client.query(message)

                    # Process responses
                    assistant_responses = []
                    tool_calls = []
                    message_count = 0
                    max_messages = 20  # Prevent infinite loops

                    async for msg in client.receive_messages():
                        message_count += 1

                        if message_count > max_messages:
                            st.warning("⚠️ Maximum message limit reached to prevent infinite loop")
                            break

                        if isinstance(msg, AssistantMessage):
                            for block in msg.content:
                                if isinstance(block, TextBlock):
                                    # Filter out raw tool results
                                    text = block.text
                                    if text and not text.startswith('{') and not text.startswith('data:'):
                                        assistant_responses.append(text)

                                        # Display response in real-time
                                        with st.chat_message("assistant"):
                                            st.write(text)

                                elif isinstance(block, ToolUseBlock):
                                    tool_name = block.name.replace('mcp__databricks-mcp__', '')
                                    tool_calls.append(tool_name)

                                    # Display tool usage
                                    st.markdown(f"""
                                    <div class="tool-call">
                                        🔧 <strong>Using:</strong> {tool_name}
                                    </div>
                                    """, unsafe_allow_html=True)

                        # Handle tool results
                        elif hasattr(msg, 'content'):
                            for block in msg.content:
                                if isinstance(block, ToolResultBlock):
                                    # Check for file generation
                                    if hasattr(block, 'content'):
                                        content_str = ""
                                        if hasattr(block.content, 'text'):
                                            content_str = block.content.text
                                        elif isinstance(block.content, str):
                                            content_str = block.content

                                        # Look for file paths in results
                                        if any(ext in content_str for ext in ['.zip', '.yml', '.yaml']):
                                            # Extract file info (simplified)
                                            lines = content_str.split('\n')
                                            for line in lines:
                                                if any(ext in line for ext in ['.zip', '.yml', '.yaml']):
                                                    filename = line.split('/')[-1] if '/' in line else line
                                                    st.session_state.generated_files.append({
                                                        'name': filename,
                                                        'path': line.strip(),
                                                        'created': datetime.now()
                                                    })

                                                    st.markdown(f"""
                                                    <div class="success-message">
                                                        ✅ <strong>Generated:</strong> {filename}
                                                    </div>
                                                    """, unsafe_allow_html=True)
                                                    break

                                    # Fallback: show structured results for non-file tools
                                    content_str = _to_str(block.content)
                                    if content_str:
                                        try:
                                            data = json.loads(content_str) if content_str.strip().startswith("{") else None
                                        except Exception:
                                            data = None

                                        if isinstance(data, dict) and data.get("success"):
                                            payload = data.get("data", data)
                                            # Recognize list_jobs output
                                            if isinstance(payload, dict) and "jobs" in payload and isinstance(payload["jobs"], list):
                                                st.subheader("Jobs")
                                                st.dataframe(payload["jobs"])
                                            else:
                                                st.subheader("Result")
                                                st.code(json.dumps(payload, indent=2))
                                        else:
                                            # Plain-text or unstructured result
                                            st.subheader("Result")
                                            st.code(content_str[:2000])

                        if isinstance(msg, ResultMessage):
                            st.info("✅ Conversation completed successfully")
                            break

                    # Store conversation
                    st.session_state.messages.append({
                        'role': 'user',
                        'content': message,
                        'timestamp': datetime.now()
                    })

                    st.session_state.messages.append({
                        'role': 'assistant',
                        'content': ' '.join(assistant_responses),
                        'tool_calls': tool_calls,
                        'timestamp': datetime.now()
                    })

        st.success("✅ Request completed successfully!")

    except Exception as e:
        st.error(f"❌ Error processing request: {str(e)}")
        with st.expander("Error Details"):
            st.code(str(e))

def main():
    """Main application function"""
    init_session_state()
    display_header()
    display_sidebar()

    # Main chat interface
    st.header("💬 Chat with DAB Generator")

    # Display conversation history
    if st.session_state.messages:
        for msg in st.session_state.messages[-10:]:  # Show last 10 messages
            with st.chat_message(msg['role']):
                st.write(msg['content'])
                if msg['role'] == 'assistant' and 'tool_calls' in msg:
                    if msg['tool_calls']:
                        st.caption(f"🔧 Tools used: {', '.join(msg['tool_calls'])}")

    # Input area
    prompt = st.chat_input("Ask me to generate bundles, analyze jobs, or explore workspace...")

    # Handle selected prompt from sidebar
    if hasattr(st.session_state, 'selected_prompt'):
        prompt = st.session_state.selected_prompt
        delattr(st.session_state, 'selected_prompt')

    # Process input
    if prompt and not st.session_state.processing:
        st.session_state.processing = True

        # Display user message
        with st.chat_message("user"):
            st.write(prompt)

        # Process with Claude
        try:
            asyncio.run(process_chat_message(prompt))
        except Exception as e:
            st.error(f"Failed to process message: {str(e)}")
        finally:
            st.session_state.processing = False
            st.rerun()

    elif st.session_state.processing:
        st.info("🤖 Processing your request...")

    # Quick actions
    if not st.session_state.processing:
        st.subheader("🚀 Quick Actions")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("🔍 List Jobs", help="List all Databricks jobs"):
                asyncio.run(process_chat_message("List Databricks jobs (limit 50) and show a table."))

        with col2:
            if st.button("📁 Browse Workspace", help="Browse workspace files"):
                asyncio.run(process_chat_message("List workspace files in /Workspace/Users"))

        with col3:
            if st.button("🏥 Health Check", help="Check MCP server health"):
                asyncio.run(process_chat_message("Check Databricks MCP server health and show user and workspace URL."))

if __name__ == "__main__":
    main()