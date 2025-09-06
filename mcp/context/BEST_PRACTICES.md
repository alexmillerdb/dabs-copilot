# Databricks Asset Bundle Best Practices

This document outlines best practices for creating production-ready Databricks Asset Bundles based on notebook analysis and industry standards.

## Bundle Structure Best Practices

### 1. Naming Conventions

#### Bundle Names
```yaml
# Good: Descriptive, environment-aware
bundle:
  name: customer-analytics-pipeline
  name: fraud-detection-ml
  name: real-time-recommendations

# Avoid: Generic or unclear names
bundle:
  name: my-bundle
  name: test123
  name: notebook-job
```

#### Resource Names
```yaml
# Use consistent naming with environment and purpose
resources:
  jobs:
    customer_analytics_etl:           # snake_case for keys
      name: customer-analytics-${bundle.target}  # kebab-case for names

  pipelines:
    bronze_silver_pipeline:
      name: bronze-silver-${bundle.target}

  model_serving_endpoints:
    recommendation_model:
      name: recommendations-${bundle.target}
```

### 2. Variable Management

#### Environment-Specific Variables
```yaml
variables:
  # Always provide descriptions
  catalog:
    description: Unity Catalog catalog name for data storage
    default: ${bundle.target}_catalog

  warehouse_id:
    description: SQL warehouse ID for query execution
    # No default - force explicit configuration

  notification_email:
    description: Email for job notifications
    default: ${workspace.current_user.userName}

  # Environment-specific overrides
targets:
  dev:
    variables:
      catalog: dev_analytics
      warehouse_id: ${var.dev_warehouse_id}
      
  prod:
    variables:
      catalog: main
      warehouse_id: ${var.prod_warehouse_id}
      notification_email: data-team@company.com
```

#### Sensitive Data Handling
```yaml
# Use secrets for sensitive information
variables:
  api_key:
    description: External API key
    default: ${secrets.external_api.key}

  database_password:
    description: Database connection password  
    default: ${secrets.database.password}

# Reference in notebook parameters
tasks:
  - task_key: data_extraction
    notebook_task:
      base_parameters:
        api_key: ${var.api_key}
        db_password: ${var.database_password}
```

### 3. Cluster Configuration Best Practices

#### Use Job Clusters (Not All-Purpose)
```yaml
# Good: Job-specific clusters
job_clusters:
  - job_cluster_key: etl_cluster
    new_cluster:
      spark_version: "13.3.x-scala2.12"
      node_type_id: "i3.xlarge"
      num_workers: 4

# Avoid: All-purpose clusters in production
# existing_cluster_id: "cluster-123"  # Only for dev/testing
```

#### Environment-Appropriate Sizing
```yaml
targets:
  dev:
    resources:
      jobs:
        my_job:
          job_clusters:
            - job_cluster_key: main
              new_cluster:
                node_type_id: "i3.large"     # Smaller for dev
                num_workers: 2
                spot_bid_price_percent: 50    # Cost optimization
  
  prod:
    resources:
      jobs:
        my_job:
          job_clusters:
            - job_cluster_key: main
              new_cluster:
                node_type_id: "i3.2xlarge"   # Larger for prod
                num_workers: 8
                # No spot instances for reliability
```

## Job Design Best Practices

### 1. Task Dependencies

#### Clear Dependency Chains
```yaml
tasks:
  - task_key: extract_data
    notebook_task:
      notebook_path: ./notebooks/01_extract.py

  - task_key: validate_data
    depends_on:
      - task_key: extract_data
    notebook_task:
      notebook_path: ./notebooks/02_validate.py

  - task_key: transform_data
    depends_on:
      - task_key: validate_data     # Single dependency
    notebook_task:
      notebook_path: ./notebooks/03_transform.py

  - task_key: load_data
    depends_on:
      - task_key: transform_data
    notebook_task:
      notebook_path: ./notebooks/04_load.py

  # Multiple dependencies for final tasks
  - task_key: generate_report
    depends_on:
      - task_key: load_data
      - task_key: validate_data     # Can depend on multiple
```

#### Avoid Complex Dependencies
```yaml
# Good: Linear or tree-like dependencies
extract -> validate -> transform -> load

# Avoid: Complex circular or diamond dependencies
task_a -> task_b -> task_d
task_a -> task_c -> task_d  # Diamond - can cause issues
```

### 2. Error Handling and Notifications

#### Comprehensive Notifications
```yaml
email_notifications:
  on_start:
    - ${var.notification_email}
  on_success:
    - data-team@company.com
  on_failure:
    - ${var.notification_email}
    - oncall@company.com
  no_alert_for_skipped_runs: false
```

#### Timeout Settings
```yaml
# Set appropriate timeouts
tasks:
  - task_key: long_running_task
    notebook_task:
      notebook_path: ./notebooks/heavy_processing.py
    timeout_seconds: 7200  # 2 hours

  - task_key: quick_task
    notebook_task:
      notebook_path: ./notebooks/validation.py
    timeout_seconds: 600   # 10 minutes

# Job-level timeout
timeout_seconds: 14400  # 4 hours total
```

#### Retry Configuration
```yaml
# Add retries for flaky operations
max_retries: 2
min_retry_interval_millis: 60000  # 1 minute
retry_on_timeout: true

tasks:
  - task_key: external_api_call
    notebook_task:
      notebook_path: ./notebooks/api_integration.py
    max_retries: 3  # Higher retries for external dependencies
```

### 3. Scheduling Best Practices

#### Appropriate Schedules
```yaml
# Daily ETL at off-peak hours
schedule:
  quartz_cron_expression: "0 2 * * *"  # 2 AM daily
  timezone_id: "UTC"

# Hourly for real-time processing
schedule:
  quartz_cron_expression: "0 0 * * * *"  # Every hour

# Weekly for heavy reporting
schedule:
  quartz_cron_expression: "0 0 6 * * SUN"  # Sundays at 6 AM
```

#### Environment-Specific Schedules
```yaml
targets:
  dev:
    resources:
      jobs:
        my_job:
          schedule:
            pause_status: PAUSED  # Don't run automatically in dev
            
  prod:
    resources:
      jobs:
        my_job:
          schedule:
            quartz_cron_expression: "0 2 * * *"
            timezone_id: "UTC"
```

## Security and Permissions

### 1. Unity Catalog Integration

#### Proper Catalog Structure
```yaml
variables:
  catalog:
    description: Unity Catalog catalog
    default: ${bundle.target}

# Use in notebook parameters
tasks:
  - task_key: process_data
    notebook_task:
      base_parameters:
        catalog: ${var.catalog}
        source_schema: raw
        target_schema: silver
```

#### Schema and Table Management
```yaml
# Let notebooks create tables dynamically
# But define schema structure in bundle for governance
resources:
  schemas:
    raw_data:
      catalog_name: ${var.catalog}
      name: raw
      comment: Raw data ingestion schema
      
    processed_data:
      catalog_name: ${var.catalog}
      name: silver
      comment: Processed and validated data
```

### 2. Access Control

#### Job-Level Permissions
```yaml
# Restrict who can manage jobs
permissions:
  - level: CAN_VIEW
    group_name: data_analysts
  - level: CAN_RUN
    group_name: data_engineers
  - level: CAN_MANAGE
    user_name: ${workspace.current_user.userName}
  - level: CAN_MANAGE
    service_principal_name: ${var.deployment_sp}
```

#### Service Principal Usage
```yaml
# Use service principals for production deployments
variables:
  deployment_service_principal:
    description: Service principal for deployments
    default: databricks-deployment-sp

# Reference in permissions and configurations
permissions:
  - level: CAN_MANAGE
    service_principal_name: ${var.deployment_service_principal}
```

## Performance and Cost Optimization

### 1. Resource Optimization

#### Adaptive Query Execution
```yaml
spark_conf:
  spark.sql.adaptive.enabled: "true"
  spark.sql.adaptive.coalescePartitions.enabled: "true"
  spark.sql.adaptive.skewJoin.enabled: "true"
  spark.databricks.delta.optimizeWrite.enabled: "true"
```

#### Auto-termination
```yaml
new_cluster:
  autotermination_minutes: 30  # Terminate idle clusters
  enable_elastic_disk: true    # Scale disk as needed
```

### 2. Development vs Production

#### Development Optimizations
```yaml
targets:
  dev:
    resources:
      jobs:
        my_job:
          job_clusters:
            - job_cluster_key: dev_cluster
              new_cluster:
                node_type_id: "i3.large"        # Smaller
                num_workers: 1                   # Fewer workers
                spot_bid_price_percent: 50       # Use spot instances
                autotermination_minutes: 15      # Faster termination
```

#### Production Optimizations
```yaml
targets:
  prod:
    resources:
      jobs:
        my_job:
          job_clusters:
            - job_cluster_key: prod_cluster
              new_cluster:
                node_type_id: "i3.2xlarge"      # Appropriate size
                num_workers: 8                   # Based on workload
                # No spot instances for reliability
                autotermination_minutes: 60      # Longer for stability
```

## Monitoring and Observability

### 1. Logging Best Practices

#### Structured Logging in Notebooks
```python
# Add to notebook parameters
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Log key events
logger.info(f"Processing data for date: {processing_date}")
logger.info(f"Processed {row_count} rows")
logger.error(f"Failed to process batch: {error_msg}")
```

#### Job-Level Monitoring
```yaml
# Enable job metrics
email_notifications:
  on_duration_warning_threshold_exceeded:
    - performance-team@company.com
    
# Set duration thresholds
health:
  rules:
    - metric: RUN_DURATION_SECONDS
      op: GREATER_THAN
      value: 7200  # Alert if runs longer than 2 hours
```

### 2. Data Quality Monitoring

#### Built-in Quality Checks
```yaml
# Add data validation tasks
tasks:
  - task_key: data_quality_check
    depends_on:
      - task_key: load_data
    notebook_task:
      notebook_path: ./notebooks/data_quality_validation.py
      base_parameters:
        table_name: ${var.catalog}.silver.customer_data
        quality_threshold: "95"
```

## Deployment Best Practices

### 1. CI/CD Integration

#### Bundle Validation
```yaml
# Always validate before deployment
# Add to CI/CD pipeline:
# databricks bundle validate --target staging
# databricks bundle deploy --target staging
# run tests
# databricks bundle deploy --target prod
```

#### Environment Promotion
```yaml
# Clear environment progression
dev -> staging -> prod

# With appropriate testing at each stage
targets:
  dev:
    mode: development  # Allows destructive changes
    
  staging:  
    mode: development  # Still allows changes for testing
    
  prod:
    mode: production   # Restricts destructive changes
```

### 2. Version Control

#### Git Integration
```yaml
# Include in bundle for traceability
bundle:
  name: customer-analytics
  description: Customer analytics pipeline
  git:
    origin_url: https://github.com/company/analytics-pipelines
    branch: main
```

## Common Anti-Patterns to Avoid

### 1. Configuration Anti-Patterns

❌ **Hardcoded Values**
```yaml
# Bad: Environment-specific values hardcoded
tasks:
  - task_key: process
    notebook_task:
      base_parameters:
        database_url: "jdbc:postgresql://prod-db:5432/analytics"
```

✅ **Parameterized Configuration**
```yaml
# Good: Use variables
tasks:
  - task_key: process
    notebook_task:
      base_parameters:
        database_url: ${var.database_url}
```

❌ **All-Purpose Clusters in Production**
```yaml
# Bad: Using existing all-purpose clusters
tasks:
  - task_key: etl
    existing_cluster_id: "0123-456789-abc123"
```

✅ **Job Clusters**
```yaml
# Good: Job-specific clusters
job_clusters:
  - job_cluster_key: etl_cluster
    new_cluster:
      spark_version: "13.3.x-scala2.12"
      node_type_id: "i3.xlarge"
```

### 2. Security Anti-Patterns

❌ **Secrets in Code**
```yaml
# Bad: Hardcoded secrets
base_parameters:
  api_key: "sk-1234567890abcdef"
```

✅ **Proper Secret Management**
```yaml
# Good: Reference secrets
base_parameters:
  api_key: ${secrets.external_api.key}
```

### 3. Performance Anti-Patterns

❌ **Over-provisioned Development**
```yaml
# Bad: Same size clusters for all environments
node_type_id: "i3.8xlarge"  # Expensive for dev
num_workers: 16
```

✅ **Environment-Appropriate Sizing**
```yaml
# Good: Right-sized per environment
targets:
  dev:
    # Smaller, cheaper
  prod:
    # Production-appropriate
```