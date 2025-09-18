"""Configuration settings for DAB agents"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class AgentSettings(BaseSettings):
    """Agent system configuration"""
    
    # MCP Server Configuration
    mcp_mode: str = "local"  # "local" or "remote"
    mcp_remote_url: str = "https://databricks-mcp-server-1444828305810485.aws.databricksapps.com"
    mcp_local_command: str = "python mcp/server/main.py"
    
    # Claude SDK - supports both CLAUDE_API_KEY and ANTHROPIC_API_KEY
    claude_api_key: Optional[str] = None
    max_conversation_length: int = 100
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Fallback to ANTHROPIC_API_KEY if CLAUDE_API_KEY not set
        if not self.claude_api_key:
            self.claude_api_key = os.getenv("ANTHROPIC_API_KEY")
    
    # Agent Behavior
    auto_validate_bundles: bool = True
    default_target_env: str = "dev"
    enable_advanced_analysis: bool = True
    
    model_config = {
        "env_file": [".env", "../.env"], 
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }


def get_settings() -> AgentSettings:
    """Get application settings"""
    return AgentSettings()