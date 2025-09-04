# Databricks MCP Tools Specification

## Tool Categories & Implementation Plan

### 1. Core Workspace Tools (✅ Existing - Enhanced)

#### `health`
**Purpose**: Check server and Databricks connection health  
**Status**: NEW - Critical for debugging

```python
@mcp.tool()
async def health() -> str:
    """Check server and Databricks connection health"""
```

**Parameters**: None

**Response Format**:
```json
{
  "status": "success",
  "data": {
    "server_status": "healthy",
    "databricks_connection": "connected",
    "workspace_url": "https://workspace.databricks.com",
    "user": "user@company.com",
    "permissions": ["can_manage_jobs", "can_read_notebooks"],
    "available_warehouses": 3,
    "timestamp": "2024-09-04T10:30:00Z"
  }
}
```

#### `list_jobs` ✅ 
**Purpose**: List all jobs in workspace with filtering  
**Status**: EXISTING - Enhanced with better filtering

```python
@mcp.tool()
async def list_jobs(
    limit: int = Field(default=100, description="Maximum number of jobs to return"),
    name_filter: Optional[str] = Field(default=None, description="Filter jobs by name containing this string"),
    created_by: Optional[str] = Field(default=None, description="Filter by creator username"),
    tags: Optional[List[str]] = Field(default=None, description="Filter by job tags")
) -> str:
```

**Enhanced Response**:
```json
{
  "status": "success", 
  "data": {
    "jobs": [
      {
        "job_id": 123,
        "name": "ETL Pipeline",
        "created_time": "2024-09-01T10:00:00Z",
        "creator_user_name": "user@company.com",
        "job_type": "notebook",
        "schedule": "daily",
        "last_run_status": "success",
        "tags": {"environment": "prod", "team": "data"}
      }
    ],
    "count": 25,
    "total_available": 156,
    "filters_applied": {"name_filter": "ETL"}
  }
}
```

#### `get_job` ✅
**Purpose**: Get detailed job configuration  
**Status**: EXISTING - Enhanced with dependency analysis

```python
@mcp.tool()
async def get_job(
    job_id: int = Field(description="The ID of the job to retrieve"),
    include_runs: bool = Field(default=False, description="Include recent run history")
) -> str:
```

#### `run_job` ✅
**Purpose**: Execute a job with parameter support  
**Status**: EXISTING - Enhanced with monitoring

#### `list_notebooks` ✅ 
**Purpose**: List notebooks in workspace path  
**Status**: EXISTING - Enhanced with metadata

#### `export_notebook` ✅
**Purpose**: Export notebook content in various formats  
**Status**: EXISTING - Enhanced with analysis

### 2. SQL & Data Tools (🆕 New)

#### `execute_dbsql` 
**Purpose**: Execute SQL queries on Databricks SQL warehouses
**Status**: NEW - Critical for data analysis

```python
@mcp.tool()
async def execute_dbsql(
    query: str = Field(description="SQL query to execute"),
    warehouse_id: Optional[str] = Field(default=None, description="SQL warehouse ID (uses default if not provided)"),
    limit: int = Field(default=100, description="Maximum rows to return"),
    timeout: int = Field(default=30, description="Query timeout in seconds")
) -> str:
```

**Response Format**:
```json
{
  "status": "success",
  "data": {
    "query": "SELECT * FROM catalog.schema.table LIMIT 10",
    "rows": [
      {"col1": "value1", "col2": "value2"},
      {"col1": "value3", "col2": "value4"}
    ],
    "row_count": 10,
    "execution_time_ms": 1250,
    "warehouse_id": "abc123def456",
    "schema": [
      {"name": "col1", "type": "string"},
      {"name": "col2", "type": "integer"}
    ]
  }
}
```

#### `list_warehouses`
**Purpose**: List available SQL warehouses with capacity info
**Status**: NEW

```python
@mcp.tool()
async def list_warehouses() -> str:
```

**Response Format**:
```json
{
  "status": "success",
  "data": {
    "warehouses": [
      {
        "warehouse_id": "abc123",
        "name": "Starter Warehouse",
        "size": "2X-Small", 
        "state": "RUNNING",
        "cluster_count": 1,
        "auto_stop_mins": 10,
        "creator_name": "admin@company.com"
      }
    ],
    "default_warehouse_id": "abc123"
  }
}
```

### 3. File System Tools (🆕 New)

#### `list_dbfs_files`
**Purpose**: List files in Databricks File System
**Status**: NEW - For data exploration

```python
@mcp.tool()
async def list_dbfs_files(
    path: str = Field(default="/", description="DBFS path to list"),
    recursive: bool = Field(default=False, description="List recursively"),
    file_types: Optional[List[str]] = Field(default=None, description="Filter by file extensions")
) -> str:
```

#### `upload_file`
**Purpose**: Upload file to DBFS
**Status**: NEW - For data ingestion workflows

```python
@mcp.tool()
async def upload_file(
    local_path: str = Field(description="Local file path"),
    dbfs_path: str = Field(description="Destination DBFS path"),
    overwrite: bool = Field(default=False, description="Overwrite existing file")
) -> str:
```

#### `download_file`
**Purpose**: Download file from DBFS
**Status**: NEW

```python
@mcp.tool()
async def download_file(
    dbfs_path: str = Field(description="DBFS file path"),
    local_path: Optional[str] = Field(default=None, description="Local destination (temp if not provided)")
) -> str:
```

### 4. DAB Generation Tools (🚀 Core Feature)

#### `analyze_notebook`
**Purpose**: Deep analysis of notebook structure and dependencies
**Status**: NEW - Critical for DAB generation

```python
@mcp.tool()
async def analyze_notebook(
    path: str = Field(description="Notebook path to analyze"),
    include_dependencies: bool = Field(default=True, description="Analyze import dependencies"),
    include_data_sources: bool = Field(default=True, description="Identify data sources"),
    generate_recommendations: bool = Field(default=True, description="Generate optimization recommendations")
) -> str:
```

**Response Format**:
```json
{
  "status": "success",
  "data": {
    "notebook_info": {
      "path": "/Users/user@company.com/etl_pipeline.py",
      "language": "python",
      "size_bytes": 15420,
      "cell_count": 23,
      "last_modified": "2024-09-03T14:30:00Z"
    },
    "dependencies": {
      "imports": [
        "pandas", "pyspark.sql", "databricks.sdk", 
        "requests", "datetime"
      ],
      "databricks_libraries": [
        {"library": "pandas", "version": "1.5.3"},
        {"library": "requests", "version": "2.28.1"}
      ],
      "custom_modules": ["/shared/utils/data_utils.py"]
    },
    "data_sources": {
      "tables": [
        {
          "catalog": "prod", 
          "schema": "raw_data",
          "table": "customer_events",
          "access_pattern": "read"
        }
      ],
      "files": [
        {
          "path": "/mnt/data-lake/events/2024/",
          "format": "parquet", 
          "access_pattern": "read"
        }
      ],
      "external_apis": [
        {"url": "api.external-service.com", "method": "GET"}
      ]
    },
    "parameters": {
      "widgets": [
        {"name": "start_date", "type": "text", "default": "2024-01-01"},
        {"name": "environment", "type": "dropdown", "values": ["dev", "staging", "prod"]}
      ],
      "environment_variables": ["DATABRICKS_TOKEN", "API_KEY"]
    },
    "recommendations": [
      {
        "type": "performance",
        "message": "Consider using Delta Live Tables for streaming workload",
        "confidence": "high"
      },
      {
        "type": "security", 
        "message": "Use Databricks secrets for API_KEY instead of environment variable",
        "confidence": "critical"
      }
    ]
  }
}
```

#### `generate_bundle`
**Purpose**: Generate Databricks Asset Bundle configuration from analysis
**Status**: NEW - Core MVP feature

```python
@mcp.tool()
async def generate_bundle(
    name: str = Field(description="Bundle name"),
    notebooks: List[str] = Field(description="List of notebook paths to include"),
    jobs: Optional[List[int]] = Field(default=None, description="Existing job IDs to include"),
    target_env: str = Field(default="dev", description="Target environment (dev, staging, prod)"),
    include_tests: bool = Field(default=True, description="Generate test scaffolds"),
    cluster_config: Optional[str] = Field(default="shared", description="Cluster configuration type")
) -> str:
```

**Response Format**:
```json
{
  "status": "success",
  "data": {
    "bundle_config": {
      "bundle": {
        "name": "customer-etl-pipeline",
        "target": "dev"
      },
      "workspace": {
        "host": "${workspace.host}",
        "root_path": "/bundles/${bundle.target}/${bundle.name}"
      },
      "resources": {
        "jobs": {
          "etl_job": {
            "name": "${bundle.name}-etl-${bundle.target}",
            "tasks": [
              {
                "task_key": "extract_data",
                "notebook_task": {
                  "notebook_path": "../notebooks/extract.py",
                  "base_parameters": {
                    "environment": "${bundle.target}"
                  }
                },
                "job_cluster_key": "main_cluster"
              }
            ],
            "job_clusters": [
              {
                "job_cluster_key": "main_cluster",
                "new_cluster": {
                  "spark_version": "13.3.x-scala2.12",
                  "node_type_id": "i3.xlarge",
                  "num_workers": 2
                }
              }
            ]
          }
        }
      },
      "targets": {
        "dev": {
          "workspace": {
            "host": "https://dev.databricks.com"
          }
        }
      }
    },
    "files_created": [
      "bundle.yml",
      "notebooks/extract.py", 
      "tests/test_extract.py"
    ],
    "validation_status": "passed"
  }
}
```

#### `validate_bundle`
**Purpose**: Validate DAB configuration for errors and best practices
**Status**: NEW - Quality assurance

```python
@mcp.tool()
async def validate_bundle(
    bundle_path: str = Field(description="Path to bundle.yml file"),
    strict_mode: bool = Field(default=False, description="Enable strict validation rules"),
    check_permissions: bool = Field(default=True, description="Validate workspace permissions")
) -> str:
```

**Response Format**:
```json
{
  "status": "success",
  "data": {
    "validation_result": "passed",
    "errors": [],
    "warnings": [
      {
        "code": "CLUSTER_SIZE_RECOMMENDATION",
        "message": "Consider using smaller cluster for development target",
        "location": "resources.jobs.etl_job.job_clusters[0]"
      }
    ],
    "recommendations": [
      {
        "category": "cost_optimization",
        "message": "Use spot instances for non-critical workloads",
        "impact": "medium"
      }
    ],
    "bundle_info": {
      "total_jobs": 3,
      "total_notebooks": 5,
      "targets": ["dev", "staging", "prod"],
      "estimated_cost_per_run": "$2.50"
    }
  }
}
```

#### `create_tests`
**Purpose**: Generate unit test scaffolds for notebook code
**Status**: NEW - Development best practices

```python
@mcp.tool()
async def create_tests(
    notebook_path: str = Field(description="Path to notebook to test"),
    test_framework: str = Field(default="pytest", description="Testing framework (pytest, unittest)"),
    include_integration: bool = Field(default=False, description="Include integration test templates"),
    mock_external_deps: bool = Field(default=True, description="Generate mocks for external dependencies")
) -> str:
```

### 5. Monitoring & Analytics Tools (🔍 Observability)

#### `get_job_runs`
**Purpose**: Get job run history and performance metrics
**Status**: NEW - Operations support

```python
@mcp.tool()
async def get_job_runs(
    job_id: int = Field(description="Job ID"),
    limit: int = Field(default=20, description="Number of runs to retrieve"),
    status_filter: Optional[str] = Field(default=None, description="Filter by run status")
) -> str:
```

#### `analyze_job_performance`
**Purpose**: Analyze job performance trends and bottlenecks
**Status**: NEW - Optimization insights

```python
@mcp.tool()
async def analyze_job_performance(
    job_id: int = Field(description="Job ID to analyze"),
    days_back: int = Field(default=7, description="Days of history to analyze"),
    include_recommendations: bool = Field(default=True, description="Generate performance recommendations")
) -> str:
```

#### `get_cluster_metrics`
**Purpose**: Get cluster utilization and cost metrics
**Status**: NEW - Cost optimization

```python
@mcp.tool()
async def get_cluster_metrics(
    cluster_id: Optional[str] = Field(default=None, description="Specific cluster ID (all clusters if not provided)"),
    time_range: str = Field(default="24h", description="Time range: 1h, 24h, 7d, 30d")
) -> str:
```

## Tool Integration Workflows

### 1. Complete Notebook-to-DAB Workflow
```python
# User: "Analyze my ETL notebook and create a production-ready DAB"

# Step 1: Export and analyze notebook
notebook_content = await export_notebook("/Users/user/etl_pipeline.py", format="SOURCE")
analysis = await analyze_notebook("/Users/user/etl_pipeline.py", include_dependencies=True)

# Step 2: Generate bundle configuration  
bundle = await generate_bundle(
    name="production-etl",
    notebooks=["/Users/user/etl_pipeline.py"],
    target_env="prod",
    include_tests=True
)

# Step 3: Validate configuration
validation = await validate_bundle(bundle["bundle_path"], strict_mode=True)

# Step 4: Create test scaffolds
tests = await create_tests("/Users/user/etl_pipeline.py", include_integration=True)

# Return comprehensive results
return {
    "workflow": "notebook-to-dab-complete",
    "notebook_analysis": analysis,
    "bundle_config": bundle,
    "validation_results": validation,
    "test_scaffolds": tests
}
```

### 2. Job Analysis & Optimization Workflow
```python
# User: "Optimize my existing job performance"

# Step 1: Get job details
job_details = await get_job(job_id=123, include_runs=True)

# Step 2: Analyze performance history
performance = await analyze_job_performance(job_id=123, days_back=30)

# Step 3: Get cluster metrics
cluster_metrics = await get_cluster_metrics(cluster_id=job_details["cluster_id"])

# Return optimization recommendations
return {
    "workflow": "job-optimization", 
    "current_config": job_details,
    "performance_analysis": performance,
    "cluster_metrics": cluster_metrics,
    "recommendations": performance["recommendations"]
}
```

### 3. Data Pipeline Discovery Workflow  
```python
# User: "Help me understand my data pipeline dependencies"

# Step 1: List all jobs
jobs = await list_jobs(limit=50, tags=["pipeline"])

# Step 2: Analyze each job's notebooks
pipeline_analysis = []
for job in jobs["jobs"]:
    job_details = await get_job(job["job_id"])
    for task in job_details["tasks"]:
        if task["type"] == "notebook":
            analysis = await analyze_notebook(task["notebook_path"])
            pipeline_analysis.append({
                "job": job,
                "notebook": task["notebook_path"],
                "analysis": analysis
            })

# Return dependency map
return {
    "workflow": "pipeline-discovery",
    "total_jobs": len(jobs["jobs"]),
    "pipeline_analysis": pipeline_analysis,
    "dependency_graph": build_dependency_graph(pipeline_analysis)
}
```

## Error Handling & Response Standards

### Standard Error Codes
```python
ERROR_CODES = {
    # Connection errors
    "DATABRICKS_CONNECTION_FAILED": "Unable to connect to Databricks workspace",
    "DATABRICKS_AUTH_FAILED": "Authentication failed - check token",
    "WAREHOUSE_UNAVAILABLE": "SQL warehouse is not available",
    
    # Resource errors  
    "JOB_NOT_FOUND": "Job ID does not exist",
    "NOTEBOOK_NOT_FOUND": "Notebook path does not exist",
    "INVALID_PATH": "Invalid workspace path provided",
    
    # Permission errors
    "INSUFFICIENT_PERMISSIONS": "User lacks required permissions",
    "WAREHOUSE_ACCESS_DENIED": "Cannot access SQL warehouse",
    
    # Validation errors
    "INVALID_BUNDLE_CONFIG": "Bundle configuration is invalid",
    "INVALID_SQL_QUERY": "SQL query contains syntax errors",
    "INVALID_PARAMETERS": "Tool parameters are invalid",
    
    # Rate limiting
    "RATE_LIMIT_EXCEEDED": "Too many requests - please wait",
    "QUOTA_EXCEEDED": "Usage quota exceeded for operation"
}
```

### Response Format Standards
```python
# Success response
{
    "status": "success",
    "data": {...},
    "timestamp": "2024-09-04T10:30:00Z",
    "request_id": "req_123456"
}

# Error response
{
    "status": "error", 
    "error": {
        "code": "JOB_NOT_FOUND",
        "message": "Job ID 999 does not exist",
        "context": {"job_id": 999, "user": "user@company.com"}
    },
    "timestamp": "2024-09-04T10:30:00Z",
    "request_id": "req_123456"
}

# Partial success response
{
    "status": "partial",
    "data": {...},
    "warnings": [
        "Some notebooks could not be analyzed due to permissions"
    ],
    "timestamp": "2024-09-04T10:30:00Z"
}
```

## Implementation Priority

### Phase 1 (Week 2) - Core Tools
1. ✅ `health` - Critical for debugging
2. ✅ Enhanced `list_jobs`, `get_job`, `run_job` 
3. ✅ Enhanced `list_notebooks`, `export_notebook`
4. 🆕 `execute_dbsql`, `list_warehouses`
5. 🆕 `list_dbfs_files`

### Phase 2 (Week 2-3) - DAB Generation  
1. 🚀 `analyze_notebook` - Core analysis engine
2. 🚀 `generate_bundle` - DAB creation
3. 🚀 `validate_bundle` - Quality assurance
4. 🚀 `create_tests` - Development workflow

### Phase 3 (Week 3-4) - Advanced Features
1. 🔍 `get_job_runs`, `analyze_job_performance`
2. 🔍 `get_cluster_metrics`  
3. 🆕 `upload_file`, `download_file`
4. Integration workflows and optimization

This specification provides a comprehensive toolkit for Databricks workspace operations, analysis, and DAB generation that supports both Claude Code CLI and web UI workflows.