"""
Workspace client factory for Databricks MCP Server
Provides centralized client creation and management
"""

import os
import logging
from typing import Optional, Dict, Any
from databricks.sdk import WorkspaceClient

logger = logging.getLogger(__name__)

# Module-level cache for singleton pattern
_workspace_client: Optional[WorkspaceClient] = None


def create_workspace_client(config: Optional[Dict[str, Any]] = None) -> Optional[WorkspaceClient]:
    """
    Factory function to create Databricks workspace client.
    
    Args:
        config: Optional configuration dictionary with keys:
            - profile: Databricks CLI profile name
            - host: Databricks workspace host URL
            - token: Databricks access token
    
    Returns:
        WorkspaceClient instance or None if creation fails
        
    Priority:
        1. Config parameter (if provided)
        2. Environment variable DATABRICKS_CONFIG_PROFILE
        3. Environment variables DATABRICKS_HOST and DATABRICKS_TOKEN
        4. Default profile
    """
    try:
        logger.info(f"create_workspace_client called with config: {config}")
        logger.info(f"Environment DATABRICKS_CONFIG_PROFILE: {os.getenv('DATABRICKS_CONFIG_PROFILE')}")
        logger.info(f"Environment DATABRICKS_HOST: {os.getenv('DATABRICKS_HOST')}")

        # Use provided config first
        if config:
            if 'profile' in config:
                logger.info(f"Creating Databricks client with profile from config: {config['profile']}")
                return WorkspaceClient(profile=config['profile'])
            elif 'host' in config and 'token' in config:
                logger.info(f"Creating Databricks client with host from config: {config['host']}")
                return WorkspaceClient(host=config['host'], token=config['token'])

        # Check for profile in environment
        profile = os.getenv("DATABRICKS_CONFIG_PROFILE")
        if profile:
            logger.info(f"Creating Databricks client with profile: {profile}")
            return WorkspaceClient(profile=profile)
        
        # Check for host and token in environment
        host = os.getenv("DATABRICKS_HOST")
        token = os.getenv("DATABRICKS_TOKEN")
        if host and token:
            logger.info(f"Creating Databricks client with host: {host}")
            return WorkspaceClient(host=host, token=token)
        
        # Fall back to default profile
        logger.info("Creating Databricks client with default profile")
        return WorkspaceClient()
        
    except Exception as e:
        logger.error(f"Failed to create Databricks client: {e}")
        return None


def get_or_create_client(config: Optional[Dict[str, Any]] = None) -> Optional[WorkspaceClient]:
    """
    Get existing workspace client or create new one (singleton pattern).
    
    Args:
        config: Optional configuration for creating new client
        
    Returns:
        Cached or newly created WorkspaceClient instance
    """
    global _workspace_client
    
    if _workspace_client is None:
        _workspace_client = create_workspace_client(config)
    
    return _workspace_client


def reset_client() -> None:
    """
    Reset the cached workspace client.
    Useful for testing or when configuration changes.
    """
    global _workspace_client
    _workspace_client = None
    logger.info("Workspace client cache reset")


def is_client_initialized() -> bool:
    """
    Check if workspace client is initialized.
    
    Returns:
        True if client exists, False otherwise
    """
    return _workspace_client is not None