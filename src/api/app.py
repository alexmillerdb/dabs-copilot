#!/usr/bin/env python3
"""
Enhanced Streamlit DAB Generator with Improved State Management
Better conversation tracking, message structure, and user experience
"""

import streamlit as st
import asyncio
import os
import uuid
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import json

# Load environment variables (only if .env exists - for local development)
project_root = Path(__file__).parent.parent.parent
dotenv_path = project_root / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)
    print("📁 Loaded .env file from local development")
else:
    print("☁️ Running in production mode (no .env file)")

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

# Enhanced Message Structure
@dataclass
class Message:
    id: str
    role: str  # 'user', 'assistant', 'system', 'tool'
    content: str
    timestamp: datetime
    message_type: str = 'text'  # 'text', 'tool_call', 'tool_result', 'file', 'error'
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class Conversation:
    id: str
    messages: List[Message]
    title: str
    created_at: datetime
    last_activity: datetime
    generated_files: List[Dict[str, Any]]
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

# Streamlit page config
st.set_page_config(
    page_title="DABscribe",
    page_icon="✍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS with conversation styling
st.markdown("""
<style>
    .stApp > header { background-color: transparent; }
    .main-header {
        background: linear-gradient(90deg, #FF6B35 0%, #F7931E 100%);
        color: white; padding: 1rem; border-radius: 0.5rem;
        margin-bottom: 2rem; text-align: center;
    }
    .message-container {
        margin: 1rem 0; padding: 1rem;
        border-radius: 0.5rem; border-left: 4px solid #e0e0e0;
    }
    .user-message {
        background: #f0f8ff; border-left-color: #4CAF50;
    }
    .assistant-message {
        background: #f9f9f9; border-left-color: #FF6B35;
    }
    .tool-message {
        background: #e3f2fd; border-left-color: #2196F3;
    }
    .error-message {
        background: #ffebee; border-left-color: #f44336;
    }
    .message-header {
        font-size: 0.8rem; color: #666;
        margin-bottom: 0.5rem; font-weight: 500;
    }
    .conversation-stats {
        background: #f5f5f5; padding: 0.5rem;
        border-radius: 0.25rem; font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

def init_enhanced_session_state():
    """Initialize enhanced session state with better structure"""

    # Current conversation
    if 'current_conversation_id' not in st.session_state:
        st.session_state.current_conversation_id = str(uuid.uuid4())

    # All conversations (support multiple conversations)
    if 'conversations' not in st.session_state:
        st.session_state.conversations = {}

    # Processing state
    if 'processing' not in st.session_state:
        st.session_state.processing = False

    # UI preferences
    if 'show_metadata' not in st.session_state:
        st.session_state.show_metadata = False

    if 'max_messages_display' not in st.session_state:
        st.session_state.max_messages_display = 50

    # Ensure current conversation exists
    current_id = st.session_state.current_conversation_id
    if current_id not in st.session_state.conversations:
        st.session_state.conversations[current_id] = Conversation(
            id=current_id,
            messages=[],
            title="New Conversation",
            created_at=datetime.now(),
            last_activity=datetime.now(),
            generated_files=[]
        )

def get_current_conversation() -> Conversation:
    """Get the current active conversation"""
    current_id = st.session_state.current_conversation_id
    return st.session_state.conversations[current_id]

def add_message(role: str, content: str, message_type: str = 'text', metadata: Dict = None) -> Message:
    """Add a message to the current conversation"""
    conversation = get_current_conversation()

    message = Message(
        id=str(uuid.uuid4()),
        role=role,
        content=content,
        timestamp=datetime.now(),
        message_type=message_type,
        metadata=metadata or {}
    )

    conversation.messages.append(message)
    conversation.last_activity = datetime.now()

    # Auto-generate title from first user message
    if role == 'user' and len(conversation.messages) <= 2 and conversation.title == "New Conversation":
        conversation.title = content[:50] + ("..." if len(content) > 50 else "")

    return message

def clear_current_conversation():
    """Clear the current conversation"""
    current_id = st.session_state.current_conversation_id
    st.session_state.conversations[current_id] = Conversation(
        id=current_id,
        messages=[],
        title="New Conversation",
        created_at=datetime.now(),
        last_activity=datetime.now(),
        generated_files=[]
    )

def create_new_conversation() -> str:
    """Create a new conversation and return its ID"""
    new_id = str(uuid.uuid4())
    st.session_state.conversations[new_id] = Conversation(
        id=new_id,
        messages=[],
        title="New Conversation",
        created_at=datetime.now(),
        last_activity=datetime.now(),
        generated_files=[]
    )
    st.session_state.current_conversation_id = new_id
    return new_id

def display_message(message: Message):
    """Display a single message with proper styling"""

    # Determine message styling
    if message.role == 'user':
        container_class = "message-container user-message"
        icon = "👤"
    elif message.role == 'assistant':
        container_class = "message-container assistant-message"
        icon = "🤖"
    elif message.message_type == 'tool_call':
        container_class = "message-container tool-message"
        icon = "🔧"
    else:
        container_class = "message-container"
        icon = "ℹ️"

    # Display message
    st.markdown(f"""
    <div class="{container_class}">
        <div class="message-header">
            {icon} {message.role.title()} • {message.timestamp.strftime('%H:%M:%S')} • {message.message_type}
        </div>
        <div class="message-content">
            {message.content}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Show metadata if enabled
    if st.session_state.show_metadata and message.metadata:
        with st.expander("📊 Message Metadata"):
            st.json(message.metadata)

def display_conversation_history():
    """Display the conversation history with enhanced formatting"""
    conversation = get_current_conversation()

    if not conversation.messages:
        st.info("👋 Welcome to DABscribe! I'll help you write Databricks Asset Bundles. Try asking me to generate a bundle from a job or workspace path.")
        return

    # Conversation stats
    stats_col1, stats_col2, stats_col3 = st.columns(3)
    with stats_col1:
        st.metric("Messages", len(conversation.messages))
    with stats_col2:
        st.metric("Files Generated", len(conversation.generated_files))
    with stats_col3:
        st.metric("Duration", f"{(conversation.last_activity - conversation.created_at).seconds//60}m")

    # Display messages
    max_display = st.session_state.max_messages_display
    messages_to_show = conversation.messages[-max_display:] if len(conversation.messages) > max_display else conversation.messages

    if len(conversation.messages) > max_display:
        st.info(f"Showing last {max_display} messages ({len(conversation.messages)} total)")

    for message in messages_to_show:
        display_message(message)

def display_enhanced_sidebar():
    """Enhanced sidebar with conversation management"""

    with st.sidebar:
        st.header("✍️ DABscribe")

        # Environment status
        env = check_environment()
        st.subheader("🔌 Status")

        status_color = "🟢" if env.get('claude_valid', False) and env['client_available'] else "🔴"
        st.write(f"{status_color} Claude: {env.get('claude_status', 'Unknown')}")
        st.write(f"🏢 Databricks: {env['databricks_host'] or 'Not configured'}")
        st.write(f"👤 Profile: {env['databricks_profile']}")
        st.write(f"🔐 OAuth: {'Available' if env.get('oauth_available') else 'Not available'}")

        st.divider()

        # Conversation Management
        st.subheader("💬 Conversations")

        conversation = get_current_conversation()
        st.write(f"**Current:** {conversation.title}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🆕 New", help="Start new conversation"):
                create_new_conversation()
                st.rerun()
        with col2:
            if st.button("🗑️ Clear", help="Clear current conversation"):
                clear_current_conversation()
                st.rerun()

        # Conversation list
        if len(st.session_state.conversations) > 1:
            with st.expander("📂 All Conversations"):
                for conv_id, conv in st.session_state.conversations.items():
                    prefix = "▶️ " if conv_id == st.session_state.current_conversation_id else "  "
                    if st.button(f"{prefix}{conv.title}", key=f"conv_{conv_id}"):
                        st.session_state.current_conversation_id = conv_id
                        st.rerun()

        st.divider()

        # Display Settings
        st.subheader("⚙️ Display")
        st.session_state.show_metadata = st.checkbox("Show message metadata", st.session_state.show_metadata)
        st.session_state.max_messages_display = st.slider("Max messages", 10, 100, st.session_state.max_messages_display)

        st.divider()

        # Quick Actions
        st.subheader("🚀 Quick Actions")

        if st.button("🔍 List Jobs", disabled=st.session_state.processing):
            asyncio.run(process_enhanced_chat_message("List Databricks jobs and show results in a table"))

        if st.button("📁 Browse Workspace", disabled=st.session_state.processing):
            asyncio.run(process_enhanced_chat_message("List workspace files in /Workspace/Users"))

        if st.button("🏥 Health Check", disabled=st.session_state.processing):
            asyncio.run(process_enhanced_chat_message("Check Databricks MCP server health"))

        st.divider()

        # Generated Files
        if conversation.generated_files:
            st.subheader("📁 Generated Files")
            for file_info in conversation.generated_files:
                st.write(f"📄 {file_info.get('name', 'Unknown')}")
                st.caption(f"Created: {file_info.get('created', 'Unknown')}")

def get_oauth_token() -> str:
    """Get OAuth token from Databricks Apps context"""
    try:
        if hasattr(st, 'context') and hasattr(st.context, 'headers'):
            token = st.context.headers.get("x-forwarded-access-token")
            if token:
                print("🔐 OAuth token found in Databricks Apps context")
                return token
    except Exception as e:
        print(f"⚠️ Could not get OAuth token from Apps context: {e}")
    return None

def check_environment():
    """Check environment status"""
    claude_key = os.getenv("CLAUDE_API_KEY")
    databricks_host = os.getenv("DATABRICKS_HOST")
    databricks_profile = os.getenv("DATABRICKS_CONFIG_PROFILE", "aws-apps")
    oauth_token = get_oauth_token()

    # Validate API key
    claude_valid = False
    claude_status = "Missing"
    if claude_key:
        if claude_key.startswith("sk-ant-"):
            claude_valid = True
            # Mask the key for display
            masked_key = f"{claude_key[:10]}...{claude_key[-4:]}"
            claude_status = f"Valid ({masked_key})"
        else:
            claude_status = "Invalid format"

    return {
        'claude_configured': bool(claude_key),
        'claude_valid': claude_valid,
        'claude_status': claude_status,
        'databricks_host': databricks_host,
        'databricks_profile': databricks_profile,
        'client_available': CLIENT_AVAILABLE,
        'oauth_available': bool(oauth_token)
    }

async def process_enhanced_chat_message(message: str):
    """Enhanced chat message processing with better state management"""

    if not CLIENT_AVAILABLE:
        add_message('system', 'Claude Code client is not available. Please check your configuration.', 'error')
        st.error("Claude Code client not available")
        return

    # Add user message
    add_message('user', message)

    # Show processing state
    st.session_state.processing = True

    # Create progress containers
    status_container = st.empty()
    progress_container = st.container()

    try:
        oauth_token = get_oauth_token()
        client = await create_chat_client(oauth_token=oauth_token)

        with status_container:
            st.info("🤖 Processing your request...")

        async with client:
            await client.query(message)

            assistant_responses = []
            tool_calls = []
            message_count = 0
            max_messages = st.session_state.max_messages_display

            async for msg in client.receive_messages():
                message_count += 1

                if message_count > max_messages:
                    add_message('system', f"⚠️ Reached maximum message limit ({max_messages}) to prevent infinite loops", 'warning')
                    break

                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            text = block.text
                            if text and not text.startswith('{"type":') and not text.startswith('data:'):
                                assistant_responses.append(text)

                                # Add as streaming message
                                with progress_container:
                                    st.write(f"🤖 {text}")

                        elif isinstance(block, ToolUseBlock):
                            tool_name = block.name.replace('mcp__databricks-mcp__', '')
                            tool_calls.append(tool_name)

                            # Add tool call message
                            add_message('tool', f"Using: {tool_name}", 'tool_call', {
                                'tool_name': tool_name,
                                'full_name': block.name,
                                'inputs': block.input if isinstance(block.input, dict) else {}
                            })

                            with progress_container:
                                st.info(f"🔧 Using: {tool_name}")

                elif hasattr(msg, 'content'):
                    for block in msg.content:
                        if isinstance(block, ToolResultBlock):
                            content_str = _extract_content_string(block.content)

                            if content_str:
                                # Check for file generation
                                if any(ext in content_str for ext in ['.zip', '.yml', '.yaml']):
                                    # Handle file generation
                                    filename = _extract_filename(content_str)
                                    if filename:
                                        conversation = get_current_conversation()
                                        conversation.generated_files.append({
                                            'name': filename,
                                            'created': datetime.now().isoformat(),
                                            'path': content_str
                                        })

                                        add_message('system', f"✅ Generated file: {filename}", 'file', {
                                            'filename': filename,
                                            'content': content_str
                                        })

                                        with progress_container:
                                            st.success(f"📄 Generated: {filename}")

                                # Display structured results
                                try:
                                    if content_str.strip().startswith('{'):
                                        data = json.loads(content_str)
                                        if isinstance(data, dict) and data.get("success"):
                                            payload = data.get("data", data)

                                            with progress_container:
                                                if isinstance(payload, dict) and "jobs" in payload:
                                                    st.subheader("📊 Jobs")
                                                    st.dataframe(payload["jobs"])
                                                else:
                                                    st.subheader("📄 Result")
                                                    st.json(payload)
                                        else:
                                            with progress_container:
                                                st.code(content_str[:1000])
                                    else:
                                        with progress_container:
                                            st.code(content_str[:1000])
                                except:
                                    with progress_container:
                                        st.text(content_str[:500])

                if isinstance(msg, ResultMessage):
                    add_message('system', "✅ Conversation completed successfully", 'completion')
                    with status_container:
                        st.success("✅ Request completed!")
                    break

            # Add final assistant message
            if assistant_responses:
                final_content = ' '.join(assistant_responses)
                add_message('assistant', final_content, 'text', {
                    'tool_calls_used': tool_calls,
                    'response_parts': len(assistant_responses)
                })

    except Exception as e:
        add_message('system', f"❌ Error processing request: {str(e)}", 'error', {
            'error_type': type(e).__name__,
            'error_details': str(e)
        })
        st.error(f"Error: {str(e)}")
    finally:
        st.session_state.processing = False
        st.rerun()

def _extract_content_string(content):
    """Extract string content from various content formats"""
    if hasattr(content, 'text'):
        return content.text
    elif isinstance(content, str):
        return content
    elif isinstance(content, list):
        parts = []
        for item in content:
            if hasattr(item, 'text'):
                parts.append(item.text)
        return "\n".join(parts)
    return str(content)

def _extract_filename(content_str: str) -> str:
    """Extract filename from content string"""
    lines = content_str.split('\n')
    for line in lines:
        if any(ext in line for ext in ['.zip', '.yml', '.yaml']):
            parts = line.split()
            for part in parts:
                if part.endswith(('.zip', '.yml', '.yaml')):
                    return part.split('/')[-1]
    return None

def main():
    """Enhanced main application with improved state management"""

    # Initialize enhanced state
    init_enhanced_session_state()

    # Validate API key on startup (only once per session)
    if 'api_key_validated' not in st.session_state:
        api_key = os.getenv("CLAUDE_API_KEY")
        if api_key:
            if api_key.startswith("sk-ant-"):
                masked = f"{api_key[:10]}...{api_key[-4:]}"
                print(f"✅ API key validated on startup: {masked}")
                st.session_state.api_key_validated = True
            else:
                print("⚠️ API key found but invalid format")
                st.session_state.api_key_validated = False
        else:
            print("❌ No API key found in environment")
            st.session_state.api_key_validated = False

    # Display header
    st.markdown("""
    <div class="main-header">
        <h1>✍️ DABscribe</h1>
        <p>Writing your bundles, so you don't have to</p>
    </div>
    """, unsafe_allow_html=True)

    # Enhanced sidebar
    display_enhanced_sidebar()

    # Main content area
    st.header("💬 Conversation")

    # Display conversation history
    display_conversation_history()

    # Input area
    if not st.session_state.processing:
        user_input = st.chat_input("Ask me to generate bundles, analyze jobs, or explore workspace...")

        if user_input:
            asyncio.run(process_enhanced_chat_message(user_input))
    else:
        st.info("🔄 Processing your request... Please wait.")

if __name__ == "__main__":
    main()