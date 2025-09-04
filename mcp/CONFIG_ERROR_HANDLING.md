# Configuration Management & Error Handling Strategy

## Configuration System Design

### 1. YAML-Based Configuration Architecture

Following the reference implementation pattern, the configuration system uses YAML with environment variable substitution for flexible deployment across environments.

#### Main Configuration File (`config.yaml`)
```yaml
# config.yaml - Master configuration template
server:
  name: "databricks-mcp-server"
  version: "0.2.0"
  
  # FastAPI configuration
  fastapi:
    title: "${SERVER_TITLE:Databricks MCP Server}"
    host: "${SERVER_HOST:localhost}"
    port: ${SERVER_PORT:8000}
    debug: ${DEBUG:false}
    reload: ${RELOAD:false}
    
  # FastMCP configuration  
  mcp:
    host: "${MCP_HOST:localhost}"
    port: ${MCP_PORT:5173}
    name: "${MCP_SERVER_NAME:databricks-mcp-server}"

# Databricks connection configuration
databricks:
  # Primary connection
  host: "${DATABRICKS_HOST}"
  token: "${DATABRICKS_TOKEN}"
  
  # SQL warehouse configuration
  warehouse_id: "${DATABRICKS_WAREHOUSE_ID}"
  warehouse_timeout: ${WAREHOUSE_TIMEOUT:300}
  
  # Connection pooling
  max_connections: ${MAX_CONNECTIONS:10}
  connection_timeout: ${CONNECTION_TIMEOUT:30}
  retry_attempts: ${RETRY_ATTEMPTS:3}
  retry_delay: ${RETRY_DELAY:5}

# Logging configuration
logging:
  level: "${LOG_LEVEL:INFO}"
  format: "${LOG_FORMAT:%(asctime)s - %(name)s - %(levelname)s - %(message)s}"
  file: "${LOG_FILE:logs/mcp_server.log}"
  max_size: "${LOG_MAX_SIZE:10MB}"
  backup_count: ${LOG_BACKUP_COUNT:5}
  
  # Component-specific logging
  loggers:
    databricks.sdk: "${DATABRICKS_SDK_LOG_LEVEL:WARNING}"
    fastapi: "${FASTAPI_LOG_LEVEL:INFO}"
    mcp.server: "${MCP_LOG_LEVEL:INFO}"

# CORS configuration for web UI integration
cors:
  enabled: ${CORS_ENABLED:true}
  origins:
    - "${FRONTEND_URL:http://localhost:3000}"
    - "http://localhost:5173"
    - "https://*.databricks.com"
  allow_methods:
    - "GET"
    - "POST" 
    - "PUT"
    - "DELETE"
    - "OPTIONS"
  allow_headers:
    - "Content-Type"
    - "Authorization"
    - "X-Requested-With"

# MCP Tools configuration
tools:
  # Enable/disable specific tools
  enabled:
    # Core workspace tools
    health: ${TOOL_HEALTH:true}
    list_jobs: ${TOOL_LIST_JOBS:true}
    get_job: ${TOOL_GET_JOB:true}
    run_job: ${TOOL_RUN_JOB:true}
    list_notebooks: ${TOOL_LIST_NOTEBOOKS:true}
    export_notebook: ${TOOL_EXPORT_NOTEBOOK:true}
    
    # SQL tools
    execute_dbsql: ${TOOL_EXECUTE_DBSQL:true}
    list_warehouses: ${TOOL_LIST_WAREHOUSES:true}
    
    # File system tools
    list_dbfs_files: ${TOOL_LIST_DBFS:true}
    upload_file: ${TOOL_UPLOAD_FILE:false}  # Disabled by default for security
    download_file: ${TOOL_DOWNLOAD_FILE:false}
    
    # DAB generation tools
    analyze_notebook: ${TOOL_ANALYZE_NOTEBOOK:true}
    generate_bundle: ${TOOL_GENERATE_BUNDLE:true}
    validate_bundle: ${TOOL_VALIDATE_BUNDLE:true}
    create_tests: ${TOOL_CREATE_TESTS:true}
    
    # Analytics tools
    get_job_runs: ${TOOL_GET_JOB_RUNS:true}
    analyze_job_performance: ${TOOL_ANALYZE_PERFORMANCE:true}
    get_cluster_metrics: ${TOOL_CLUSTER_METRICS:false}  # Requires advanced permissions

  # Rate limiting configuration
  rate_limits:
    default: "${RATE_LIMIT_DEFAULT:100/minute}"
    export_notebook: "${RATE_LIMIT_EXPORT:10/minute}"
    execute_dbsql: "${RATE_LIMIT_SQL:50/minute}"
    run_job: "${RATE_LIMIT_RUN_JOB:5/minute}"
    
  # Tool-specific settings
  settings:
    export_notebook:
      max_size_mb: ${EXPORT_MAX_SIZE:50}
      allowed_formats: ["SOURCE", "HTML", "JUPYTER", "DBC"]
      
    execute_dbsql:
      max_rows: ${SQL_MAX_ROWS:1000}
      timeout_seconds: ${SQL_TIMEOUT:60}
      
    list_jobs:
      default_limit: ${JOBS_DEFAULT_LIMIT:100}
      max_limit: ${JOBS_MAX_LIMIT:500}

# Caching configuration
cache:
  enabled: ${CACHE_ENABLED:true}
  backend: "${CACHE_BACKEND:memory}"  # memory, redis, file
  
  # Cache TTL by resource type
  ttl:
    jobs: ${CACHE_TTL_JOBS:300}          # 5 minutes
    notebooks: ${CACHE_TTL_NOTEBOOKS:180} # 3 minutes
    warehouses: ${CACHE_TTL_WAREHOUSES:600} # 10 minutes
    cluster_metrics: ${CACHE_TTL_METRICS:60} # 1 minute
    
  # Cache size limits
  max_size: ${CACHE_MAX_SIZE:100MB}
  max_entries: ${CACHE_MAX_ENTRIES:1000}

# Security configuration
security:
  # API key validation
  require_api_key: ${REQUIRE_API_KEY:false}
  api_keys: "${API_KEYS:}"  # Comma-separated list
  
  # Request validation
  validate_requests: ${VALIDATE_REQUESTS:true}
  max_request_size: "${MAX_REQUEST_SIZE:10MB}"
  
  # SQL injection prevention
  enable_sql_validation: ${ENABLE_SQL_VALIDATION:true}
  allowed_sql_operations: ["SELECT", "DESCRIBE", "SHOW", "EXPLAIN"]

# Development/testing settings  
development:
  mock_databricks: ${MOCK_DATABRICKS:false}
  fake_data: ${FAKE_DATA:false}
  debug_tools: ${DEBUG_TOOLS:false}
  profiling: ${PROFILING:false}

# Environment-specific overrides
environments:
  dev:
    logging:
      level: "DEBUG"
    server:
      fastapi:
        debug: true
        reload: true
    security:
      require_api_key: false
    development:
      debug_tools: true
      
  staging:
    logging:
      level: "INFO"
    server:
      fastapi:
        debug: false
    security:
      require_api_key: true
      
  prod:
    logging:
      level: "WARNING"
    server:
      fastapi:
        debug: false
    security:
      require_api_key: true
      validate_requests: true
    tools:
      enabled:
        upload_file: false
        download_file: false
        run_job: false  # Require explicit approval
```

### 2. Configuration Management Implementation

#### Configuration Loader (`config/loader.py`)
```python
import os
import yaml
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field
import re

@dataclass
class ServerConfig:
    """Server configuration data class"""
    name: str
    version: str
    fastapi: Dict[str, Any] = field(default_factory=dict)
    mcp: Dict[str, Any] = field(default_factory=dict)

@dataclass 
class DatabricksConfig:
    """Databricks configuration data class"""
    host: str
    token: str
    warehouse_id: Optional[str] = None
    warehouse_timeout: int = 300
    max_connections: int = 10
    connection_timeout: int = 30
    retry_attempts: int = 3
    retry_delay: int = 5

@dataclass
class AppConfig:
    """Main application configuration"""
    server: ServerConfig
    databricks: DatabricksConfig
    logging: Dict[str, Any] = field(default_factory=dict)
    cors: Dict[str, Any] = field(default_factory=dict)
    tools: Dict[str, Any] = field(default_factory=dict)
    cache: Dict[str, Any] = field(default_factory=dict)
    security: Dict[str, Any] = field(default_factory=dict)

class ConfigLoader:
    """Configuration loading and environment variable substitution"""
    
    ENV_VAR_PATTERN = re.compile(r'\$\{([^}]+)\}')
    
    def __init__(self, config_path: str = "config.yaml", env: str = None):
        self.config_path = Path(config_path)
        self.env = env or os.getenv("ENVIRONMENT", "dev")
        self.logger = logging.getLogger(__name__)
        
    def load(self) -> AppConfig:
        """Load configuration with environment variable substitution"""
        try:
            # Load base configuration
            with open(self.config_path, 'r') as file:
                config_data = yaml.safe_load(file)
            
            # Apply environment-specific overrides
            if self.env in config_data.get('environments', {}):
                env_config = config_data['environments'][self.env]
                config_data = self._deep_merge(config_data, env_config)
            
            # Substitute environment variables
            config_data = self._substitute_env_vars(config_data)
            
            # Validate required configuration
            self._validate_config(config_data)
            
            # Create configuration objects
            return self._create_config_objects(config_data)
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise ConfigurationError(f"Configuration loading failed: {e}")
    
    def _substitute_env_vars(self, data: Any) -> Any:
        """Recursively substitute environment variables in configuration"""
        if isinstance(data, dict):
            return {key: self._substitute_env_vars(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._substitute_env_vars(item) for item in data]
        elif isinstance(data, str):
            return self._substitute_string(data)
        else:
            return data
    
    def _substitute_string(self, value: str) -> Any:
        """Substitute environment variables in a string value"""
        def replace_env_var(match):
            var_spec = match.group(1)
            if ':' in var_spec:
                var_name, default_value = var_spec.split(':', 1)
                env_value = os.getenv(var_name, default_value)
            else:
                var_name = var_spec
                env_value = os.getenv(var_name)
                if env_value is None:
                    raise ConfigurationError(f"Required environment variable {var_name} not set")
            
            # Type conversion
            return self._convert_type(env_value)
        
        return self.ENV_VAR_PATTERN.sub(replace_env_var, value)
    
    def _convert_type(self, value: str) -> Any:
        """Convert string values to appropriate Python types"""
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        elif value.isdigit():
            return int(value)
        elif value.replace('.', '').isdigit():
            return float(value)
        else:
            return value
    
    def _deep_merge(self, base: Dict, overlay: Dict) -> Dict:
        """Deep merge two dictionaries"""
        result = base.copy()
        for key, value in overlay.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    
    def _validate_config(self, config: Dict[str, Any]):
        """Validate required configuration values"""
        required_fields = [
            'databricks.host',
            'databricks.token',
            'server.name'
        ]
        
        for field in required_fields:
            if not self._get_nested_value(config, field):
                raise ConfigurationError(f"Required configuration field missing: {field}")
    
    def _get_nested_value(self, data: Dict, path: str) -> Any:
        """Get nested dictionary value using dot notation"""
        keys = path.split('.')
        value = data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value
    
    def _create_config_objects(self, config_data: Dict[str, Any]) -> AppConfig:
        """Create typed configuration objects"""
        server_config = ServerConfig(
            name=config_data['server']['name'],
            version=config_data['server']['version'],
            fastapi=config_data['server']['fastapi'],
            mcp=config_data['server']['mcp']
        )
        
        databricks_config = DatabricksConfig(
            host=config_data['databricks']['host'],
            token=config_data['databricks']['token'],
            warehouse_id=config_data['databricks'].get('warehouse_id'),
            warehouse_timeout=config_data['databricks'].get('warehouse_timeout', 300),
            max_connections=config_data['databricks'].get('max_connections', 10),
            connection_timeout=config_data['databricks'].get('connection_timeout', 30),
            retry_attempts=config_data['databricks'].get('retry_attempts', 3),
            retry_delay=config_data['databricks'].get('retry_delay', 5)
        )
        
        return AppConfig(
            server=server_config,
            databricks=databricks_config,
            logging=config_data.get('logging', {}),
            cors=config_data.get('cors', {}),
            tools=config_data.get('tools', {}),
            cache=config_data.get('cache', {}),
            security=config_data.get('security', {})
        )

class ConfigurationError(Exception):
    """Configuration-related error"""
    pass
```

## Error Handling Strategy

### 1. Comprehensive Error Classification System

#### Error Categories & Codes
```python
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass
import traceback
import logging

class ErrorCategory(str, Enum):
    """Error category classification"""
    CONNECTION = "connection"
    AUTHENTICATION = "authentication"
    PERMISSION = "permission"
    VALIDATION = "validation"
    RESOURCE = "resource"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    INTERNAL = "internal"
    EXTERNAL = "external"

class ErrorSeverity(str, Enum):
    """Error severity levels"""
    LOW = "low"           # Warnings, non-critical issues
    MEDIUM = "medium"     # Errors that can be handled gracefully
    HIGH = "high"         # Critical errors affecting functionality
    CRITICAL = "critical" # System failures requiring immediate attention

@dataclass
class ErrorDetail:
    """Detailed error information"""
    code: str
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    context: Optional[Dict[str, Any]] = None
    user_message: Optional[str] = None  # User-friendly message
    recovery_actions: Optional[List[str]] = None
    documentation_url: Optional[str] = None

# Comprehensive error code registry
ERROR_REGISTRY = {
    # Connection errors
    "DATABRICKS_CONNECTION_FAILED": ErrorDetail(
        code="DATABRICKS_CONNECTION_FAILED",
        category=ErrorCategory.CONNECTION,
        severity=ErrorSeverity.HIGH,
        message="Unable to connect to Databricks workspace",
        user_message="Cannot connect to your Databricks workspace. Please check your connection settings.",
        recovery_actions=[
            "Verify DATABRICKS_HOST is correct",
            "Check network connectivity",
            "Ensure workspace is running"
        ]
    ),
    
    "DATABRICKS_AUTH_FAILED": ErrorDetail(
        code="DATABRICKS_AUTH_FAILED", 
        category=ErrorCategory.AUTHENTICATION,
        severity=ErrorSeverity.HIGH,
        message="Authentication failed with provided token",
        user_message="Authentication failed. Please check your access token.",
        recovery_actions=[
            "Verify DATABRICKS_TOKEN is valid",
            "Check token expiration",
            "Ensure token has required permissions"
        ]
    ),
    
    # Resource errors
    "JOB_NOT_FOUND": ErrorDetail(
        code="JOB_NOT_FOUND",
        category=ErrorCategory.RESOURCE,
        severity=ErrorSeverity.MEDIUM,
        message="Job with specified ID does not exist",
        user_message="The requested job was not found.",
        recovery_actions=[
            "Verify job ID is correct",
            "Check if job was deleted",
            "Ensure you have access to the job"
        ]
    ),
    
    "NOTEBOOK_NOT_FOUND": ErrorDetail(
        code="NOTEBOOK_NOT_FOUND",
        category=ErrorCategory.RESOURCE, 
        severity=ErrorSeverity.MEDIUM,
        message="Notebook at specified path does not exist",
        user_message="The requested notebook was not found.",
        recovery_actions=[
            "Verify notebook path is correct",
            "Check if notebook was moved or deleted",
            "Ensure you have read access to the path"
        ]
    ),
    
    # Permission errors
    "INSUFFICIENT_PERMISSIONS": ErrorDetail(
        code="INSUFFICIENT_PERMISSIONS",
        category=ErrorCategory.PERMISSION,
        severity=ErrorSeverity.HIGH,
        message="User lacks required permissions for operation",
        user_message="You don't have permission to perform this action.",
        recovery_actions=[
            "Contact workspace administrator",
            "Request appropriate permissions",
            "Use a different account with required permissions"
        ]
    ),
    
    # Validation errors
    "INVALID_SQL_QUERY": ErrorDetail(
        code="INVALID_SQL_QUERY",
        category=ErrorCategory.VALIDATION,
        severity=ErrorSeverity.MEDIUM,
        message="SQL query contains syntax errors",
        user_message="The SQL query has syntax errors.",
        recovery_actions=[
            "Check SQL syntax",
            "Verify table and column names",
            "Test query in Databricks SQL editor"
        ]
    ),
    
    # Rate limiting
    "RATE_LIMIT_EXCEEDED": ErrorDetail(
        code="RATE_LIMIT_EXCEEDED",
        category=ErrorCategory.RATE_LIMIT,
        severity=ErrorSeverity.MEDIUM,
        message="Request rate limit exceeded",
        user_message="Too many requests. Please wait before trying again.",
        recovery_actions=[
            "Wait before retrying",
            "Reduce request frequency",
            "Contact administrator for higher limits"
        ]
    )
}
```

### 2. Exception Handling Classes

#### Custom Exception Hierarchy
```python
class MCPError(Exception):
    """Base exception for MCP server errors"""
    
    def __init__(
        self, 
        error_code: str, 
        context: Dict[str, Any] = None,
        original_error: Exception = None
    ):
        self.error_detail = ERROR_REGISTRY.get(
            error_code, 
            ErrorDetail(
                code="UNKNOWN_ERROR",
                category=ErrorCategory.INTERNAL,
                severity=ErrorSeverity.MEDIUM,
                message="An unknown error occurred"
            )
        )
        self.context = context or {}
        self.original_error = original_error
        super().__init__(self.error_detail.message)

class DatabricksConnectionError(MCPError):
    """Databricks connection-related errors"""
    pass

class DatabricksAuthError(MCPError):
    """Databricks authentication errors"""
    pass

class ResourceNotFoundError(MCPError):
    """Resource not found errors"""
    pass

class PermissionError(MCPError):
    """Permission-related errors"""
    pass

class ValidationError(MCPError):
    """Input validation errors"""
    pass

class RateLimitError(MCPError):
    """Rate limiting errors"""
    pass

class ConfigurationError(MCPError):
    """Configuration-related errors"""
    pass
```

### 3. Error Handler Implementation

#### Centralized Error Handling System
```python
import json
import logging
from typing import Any, Dict
from datetime import datetime
import uuid

class ErrorHandler:
    """Centralized error handling and response formatting"""
    
    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(__name__)
    
    def handle_error(
        self, 
        error: Exception, 
        context: Dict[str, Any] = None,
        request_id: str = None
    ) -> str:
        """Handle error and return formatted response"""
        
        # Generate request ID if not provided
        if not request_id:
            request_id = str(uuid.uuid4())
        
        # Extract error details
        if isinstance(error, MCPError):
            error_detail = error.error_detail
            error_context = {**error.context, **(context or {})}
        else:
            # Handle unexpected errors
            error_detail = ErrorDetail(
                code="UNEXPECTED_ERROR",
                category=ErrorCategory.INTERNAL,
                severity=ErrorSeverity.HIGH,
                message=str(error),
                user_message="An unexpected error occurred. Please try again."
            )
            error_context = context or {}
        
        # Log error with full context
        self._log_error(error, error_detail, error_context, request_id)
        
        # Create user-facing response
        return self._create_error_response(error_detail, error_context, request_id)
    
    def _log_error(
        self, 
        error: Exception, 
        error_detail: ErrorDetail,
        context: Dict[str, Any],
        request_id: str
    ):
        """Log error with appropriate level and detail"""
        
        log_data = {
            "request_id": request_id,
            "error_code": error_detail.code,
            "error_category": error_detail.category,
            "error_severity": error_detail.severity,
            "message": error_detail.message,
            "context": context
        }
        
        # Include stack trace for internal errors
        if error_detail.category == ErrorCategory.INTERNAL:
            log_data["stack_trace"] = traceback.format_exc()
        
        # Log at appropriate level
        if error_detail.severity == ErrorSeverity.CRITICAL:
            self.logger.critical("Critical error occurred", extra=log_data)
        elif error_detail.severity == ErrorSeverity.HIGH:
            self.logger.error("High severity error", extra=log_data)
        elif error_detail.severity == ErrorSeverity.MEDIUM:
            self.logger.warning("Medium severity error", extra=log_data)
        else:
            self.logger.info("Low severity error", extra=log_data)
    
    def _create_error_response(
        self,
        error_detail: ErrorDetail,
        context: Dict[str, Any],
        request_id: str
    ) -> str:
        """Create standardized error response"""
        
        response = {
            "status": "error",
            "error": {
                "code": error_detail.code,
                "message": error_detail.user_message or error_detail.message,
                "category": error_detail.category,
                "severity": error_detail.severity
            },
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id
        }
        
        # Include recovery actions for user-facing errors
        if error_detail.recovery_actions:
            response["error"]["recovery_actions"] = error_detail.recovery_actions
        
        # Include documentation link if available
        if error_detail.documentation_url:
            response["error"]["documentation_url"] = error_detail.documentation_url
        
        # Include safe context information
        if context:
            safe_context = self._sanitize_context(context)
            if safe_context:
                response["error"]["context"] = safe_context
        
        return json.dumps(response, indent=2)
    
    def _sanitize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive information from error context"""
        sensitive_keys = {
            'token', 'password', 'secret', 'key', 'authorization',
            'cookie', 'session', 'credentials'
        }
        
        sanitized = {}
        for key, value in context.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, (str, int, float, bool, list)):
                sanitized[key] = value
            else:
                sanitized[key] = str(type(value).__name__)
        
        return sanitized

# Global error handler instance
error_handler = ErrorHandler()

# Decorator for automatic error handling
def handle_errors(func):
    """Decorator to automatically handle and format errors"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            context = {
                "function": func.__name__,
                "args": str(args)[:500],  # Truncate long arguments
                "kwargs": {k: str(v)[:100] for k, v in kwargs.items()}
            }
            return error_handler.handle_error(e, context)
    return wrapper
```

### 4. Response Format Standards

#### Success Response Helper
```python
def create_success_response(
    data: Any,
    warnings: List[str] = None,
    request_id: str = None
) -> str:
    """Create standardized success response"""
    
    response = {
        "status": "success",
        "data": data,
        "timestamp": datetime.now().isoformat()
    }
    
    if warnings:
        response["warnings"] = warnings
        
    if request_id:
        response["request_id"] = request_id
    
    return json.dumps(response, indent=2, default=str)
```

### 5. Environment-Specific Configuration

#### Development Environment (`.env.dev`)
```bash
# Development environment configuration
ENVIRONMENT=dev
DEBUG=true
LOG_LEVEL=DEBUG

# Server configuration
SERVER_HOST=localhost
SERVER_PORT=8000
MCP_PORT=5173
CORS_ENABLED=true

# Databricks (use development workspace)
DATABRICKS_HOST=https://dev.cloud.databricks.com
DATABRICKS_TOKEN=your-dev-token
DATABRICKS_WAREHOUSE_ID=your-dev-warehouse

# Enable debug features
DEBUG_TOOLS=true
MOCK_DATABRICKS=false
PROFILING=true

# Relaxed security for development
REQUIRE_API_KEY=false
VALIDATE_REQUESTS=true
```

#### Production Environment (`.env.prod`)
```bash
# Production environment configuration
ENVIRONMENT=prod
DEBUG=false
LOG_LEVEL=WARNING

# Server configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8080
CORS_ENABLED=false

# Databricks (production workspace)
DATABRICKS_HOST=https://prod.cloud.databricks.com
DATABRICKS_TOKEN=your-prod-token
DATABRICKS_WAREHOUSE_ID=your-prod-warehouse

# Enhanced security
REQUIRE_API_KEY=true
VALIDATE_REQUESTS=true
API_KEYS=key1,key2,key3

# Disable risky tools
TOOL_UPLOAD_FILE=false
TOOL_DOWNLOAD_FILE=false
TOOL_RUN_JOB=false
```

This comprehensive configuration and error handling strategy provides:
- Flexible, environment-aware configuration management
- Comprehensive error classification and handling
- User-friendly error messages with recovery guidance
- Secure credential management
- Development and production environment separation
- Detailed logging and monitoring capabilities