"""Tests for configuration"""
import pytest
from config.settings import AgentSettings, get_settings


def test_agent_settings_defaults():
    """Test default configuration values"""
    settings = AgentSettings()
    
    assert settings.mcp_mode == "local"
    assert settings.default_target_env == "dev"
    assert settings.auto_validate_bundles is True
    assert settings.max_conversation_length == 100
    # API key should be loaded from .env file if available
    assert isinstance(settings.claude_api_key, (str, type(None)))


def test_agent_settings_from_env(monkeypatch):
    """Test configuration from environment variables"""
    monkeypatch.setenv("CLAUDE_API_KEY", "env-key")
    monkeypatch.setenv("MCP_MODE", "remote")
    monkeypatch.setenv("DEFAULT_TARGET_ENV", "staging")
    
    settings = AgentSettings()
    
    assert settings.claude_api_key == "env-key"
    assert settings.mcp_mode == "remote"
    assert settings.default_target_env == "staging"


def test_get_settings():
    """Test settings factory function"""
    settings = get_settings()
    assert isinstance(settings, AgentSettings)