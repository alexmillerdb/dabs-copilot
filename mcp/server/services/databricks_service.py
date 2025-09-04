"""
Databricks Service - Simple business logic layer
Following reference implementation patterns
"""

import os
import logging
from typing import Dict, Any, Optional, List
from databricks.sdk import WorkspaceClient
from databricks.sdk.service import jobs, workspace
from datetime import datetime

logger = logging.getLogger(__name__)

class DatabricksService:
    """Simple Databricks operations service"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.client = None
        
    async def initialize(self):
        """Initialize Databricks client"""
        try:
            host = os.getenv("DATABRICKS_HOST")
            token = os.getenv("DATABRICKS_TOKEN")
            
            if host and token:
                self.client = WorkspaceClient(host=host, token=token)
                logger.info(f"Databricks service initialized: {host}")
            else:
                self.client = WorkspaceClient()
                logger.info("Databricks service initialized with default profile")
                
        except Exception as e:
            logger.error(f"Failed to initialize Databricks service: {e}")
            raise
    
    async def check_health(self) -> Dict[str, Any]:
        """Check Databricks connection health"""
        if not self.client:
            return {"connection_status": "not_initialized"}
        
        try:
            user = self.client.current_user.me()
            return {
                "connection_status": "connected",
                "workspace_url": self.client.config.host,
                "user": user.user_name,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "connection_status": "failed",
                "error": str(e)
            }
    
    def is_ready(self) -> bool:
        """Check if service is ready"""
        return self.client is not None