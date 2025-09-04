"""
Simple Configuration Loader
Following reference implementation patterns
"""

import os
import yaml
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

@dataclass
class DatabricksConfig:
    """Databricks configuration"""
    host: str
    token: str
    warehouse_id: Optional[str] = None

@dataclass
class AppConfig:
    """Main application configuration"""
    servername: str
    databricks: DatabricksConfig
    server: Dict[str, Any] = field(default_factory=dict)
    cors: Dict[str, Any] = field(default_factory=dict)
    logging: Dict[str, Any] = field(default_factory=dict)
    tools: Dict[str, Any] = field(default_factory=dict)

class ConfigLoader:
    """Simple configuration loader"""
    
    def __init__(self, config_path: str = "config.yaml", env: str = None):
        self.config_path = Path(config_path)
        self.env = env or os.getenv("ENVIRONMENT", "dev")
        
    def load(self) -> AppConfig:
        """Load configuration"""
        try:
            # Load YAML config
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    config_data = yaml.safe_load(f)
            else:
                logger.warning(f"Config file {self.config_path} not found, using defaults")
                config_data = {}
            
            # Get values with environment variable fallbacks
            databricks_config = DatabricksConfig(
                host=os.getenv("DATABRICKS_HOST", config_data.get("databricks", {}).get("host", "")),
                token=os.getenv("DATABRICKS_TOKEN", config_data.get("databricks", {}).get("token", "")),
                warehouse_id=os.getenv("DATABRICKS_WAREHOUSE_ID", config_data.get("databricks", {}).get("warehouse_id"))
            )
            
            return AppConfig(
                servername=config_data.get("servername", "databricks-mcp-server"),
                databricks=databricks_config,
                server=config_data.get("server", {}),
                cors=config_data.get("cors", {}),
                logging=config_data.get("logging", {}),
                tools=config_data.get("tools", {})
            )
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise

class ConfigurationError(Exception):
    """Configuration error"""
    pass