---
name: databricks-asset-bundles
description: Use when generating, validating, or deploying Databricks Asset Bundles (DABs). Provides patterns, best practices, and YAML templates for bundle configuration.
---

# Databricks Asset Bundles (DABs) Skill

This skill provides comprehensive knowledge for generating, validating, and deploying Databricks Asset Bundles.

## Bundle Structure

### Required Fields
- `bundle.name` - Unique bundle identifier (use kebab-case)
- `resources.jobs` - At least one job definition
- `job.name` - Human-readable job name
- `job.tasks` - At least one task
- `task.task_key` - Unique task identifier within job

### File Structure
```
my-bundle/
├── databricks.yml        # Main bundle configuration
├── resources/            # Optional: Additional YAML configs
│   └── jobs.yml
├── src/                  # Optional: Source code
│   └── notebooks/
└── README.md             # Usage instructions
```

---

## Pattern Selection

Choose the pattern based on workload characteristics:

| Workload | Pattern | Key Features |
|----------|---------|--------------|
| Single notebook | Simple ETL | One task, minimal cluster |
| Multiple notebooks with dependencies | Multi-stage ETL | Task dependencies, shared cluster |
| MLflow detected | ML Pipeline | ML runtime, larger nodes |
| Streaming operations | Streaming Job | Long-running, auto-scale |
| DLT notebooks | DLT Pipeline | Serverless, declarative |

---

## Patterns

### 1. Simple ETL
Single notebook or script running on a schedule.

```yaml
bundle:
  name: simple-etl

resources:
  jobs:
    main_job:
      name: ${bundle.name}-${bundle.target}
      job_clusters:
        - job_cluster_key: main
          new_cluster:
            spark_version: "14.3.x-scala2.12"
            node_type_id: "i3.xlarge"
            num_workers: 2
      tasks:
        - task_key: process
          job_cluster_key: main
          notebook_task:
            notebook_path: ./notebook.py

targets:
  dev:
    mode: development
    default: true
```

### 2. Multi-stage ETL
Multiple notebooks with task dependencies.

```yaml
bundle:
  name: pipeline-etl

variables:
  catalog:
    description: Unity Catalog name
    default: main

resources:
  jobs:
    pipeline:
      name: ${bundle.name}-${bundle.target}
      job_clusters:
        - job_cluster_key: main
          new_cluster:
            spark_version: "14.3.x-scala2.12"
            node_type_id: "i3.xlarge"
            num_workers: 4
      tasks:
        - task_key: extract
          job_cluster_key: main
          notebook_task:
            notebook_path: ./01_extract.py
        - task_key: transform
          job_cluster_key: main
          depends_on:
            - task_key: extract
          notebook_task:
            notebook_path: ./02_transform.py
        - task_key: load
          job_cluster_key: main
          depends_on:
            - task_key: transform
          notebook_task:
            notebook_path: ./03_load.py

targets:
  dev:
    mode: development
    default: true
  prod:
    mode: production
```

### 3. ML Pipeline
Machine learning workload with MLflow integration.

```yaml
bundle:
  name: ml-pipeline

resources:
  jobs:
    ml_job:
      name: ${bundle.name}-${bundle.target}
      job_clusters:
        - job_cluster_key: ml
          new_cluster:
            spark_version: "14.3.x-ml-scala2.12"
            node_type_id: "i3.2xlarge"
            num_workers: 4
            spark_conf:
              spark.databricks.mlflow.trackingUrl: "databricks"
      tasks:
        - task_key: prepare
          job_cluster_key: ml
          notebook_task:
            notebook_path: ./01_prepare_data.py
        - task_key: train
          job_cluster_key: ml
          depends_on:
            - task_key: prepare
          notebook_task:
            notebook_path: ./02_train_model.py
        - task_key: evaluate
          job_cluster_key: ml
          depends_on:
            - task_key: train
          notebook_task:
            notebook_path: ./03_evaluate.py
```

### 4. Streaming Job
Long-running streaming workload.

```yaml
bundle:
  name: streaming-job

resources:
  jobs:
    streaming:
      name: ${bundle.name}-${bundle.target}
      continuous:
        pause_status: UNPAUSED
      job_clusters:
        - job_cluster_key: streaming
          new_cluster:
            spark_version: "14.3.x-scala2.12"
            node_type_id: "i3.xlarge"
            autoscale:
              min_workers: 2
              max_workers: 8
      tasks:
        - task_key: stream
          job_cluster_key: streaming
          notebook_task:
            notebook_path: ./stream_processor.py
```

---

## Best Practices

### Naming Conventions
- **Bundle name**: `descriptive-kebab-case` (e.g., `sales-data-pipeline`)
- **Job name**: `${bundle.name}-${bundle.target}` for environment-specific naming
- **Resource keys**: `snake_case` (e.g., `main_job`, `etl_cluster`)
- **Task keys**: `snake_case` descriptive names (e.g., `extract_data`, `train_model`)

### Configuration
- **Use job clusters**, not existing clusters (except for interactive development)
- **Add email notifications** for all production jobs
- **Set timeouts**: `timeout_seconds` prevents runaway jobs
- **Set retries**: `max_retries` for transient failures
- **Use variables** for environment-specific values: `${var.catalog}`

### Security
- **Never hardcode secrets** - use `${secrets.scope.key}` syntax
- **Add permissions** block for production jobs
- **Use service principals** in production targets
- **Restrict access** via workspace permissions

### Environment Targets
```yaml
targets:
  dev:
    mode: development
    default: true
    # Smaller clusters, paused schedules
    workspace:
      host: ${DATABRICKS_HOST}

  staging:
    mode: development
    # Medium clusters, test schedules

  prod:
    mode: production
    # Full clusters, active schedules
    run_as:
      service_principal_name: sp-production
```

---

## Cluster Configuration

### Decision Tree
```
Is it a notebook task?
├─ Yes → Consider serverless (no cluster config needed)
└─ No (Python/Wheel/SQL) → Need cluster config

Need cluster config?
├─ User has preferred cluster ID → Fetch config, create job_cluster
├─ User wants serverless → Use environment_key + environments
└─ No preference → Suggest serverless or small cluster
```

### Recommended Configurations

**Standard ETL:**
```yaml
new_cluster:
  spark_version: "14.3.x-scala2.12"
  node_type_id: "i3.xlarge"
  num_workers: 2
```

**ML Workloads:**
```yaml
new_cluster:
  spark_version: "14.3.x-ml-scala2.12"
  node_type_id: "i3.2xlarge"
  num_workers: 4
```

**Serverless:**
```yaml
tasks:
  - task_key: process
    notebook_task:
      notebook_path: ./notebook.py
    # No job_cluster_key = serverless
```

---

## Common Workflows

### Workflow 1: Notebook → Bundle
1. Analyze notebook(s) with `analyze_notebook` tool
2. Determine cluster requirements from analysis
3. Generate bundle with appropriate pattern
4. Validate with `databricks bundle validate`
5. Deploy with `databricks bundle deploy -t dev`

### Workflow 2: Existing Job → Bundle
1. Use `generate_bundle_from_job` tool
2. Review generated configuration
3. Validate bundle
4. Deploy alongside or replace original job

### Workflow 3: DLT Pipeline → Bundle
1. Export pipeline configuration
2. Extract source notebooks
3. Create bundle with DLT resource
4. Use serverless configuration
5. Validate and deploy

---

## Validation Commands

```bash
# Validate bundle
databricks bundle validate

# Validate specific target
databricks bundle validate -t prod

# Deploy to development
databricks bundle deploy -t dev

# Deploy to production
databricks bundle deploy -t prod

# Run job
databricks bundle run -t dev main_job
```

---

## Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| Missing workspace host | Add `host: ${DATABRICKS_HOST}` under targets.TARGET.workspace |
| Invalid spark_version | Use format like `"14.3.x-scala2.12"` (with quotes) |
| Task without cluster | Add `job_cluster_key` or use serverless |
| YAML syntax error | Check indentation (2 spaces, no tabs) |
| Missing permissions | Add `permissions` block for shared jobs |

---

## MCP Tools Reference

| Tool | Purpose |
|------|---------|
| `analyze_notebook` | Extract patterns, libraries, widgets from notebook |
| `generate_bundle` | Create bundle context for YAML generation |
| `generate_bundle_from_job` | Convert existing job to bundle |
| `validate_bundle` | Run bundle validation |
| `upload_bundle` | Upload to workspace |
| `run_bundle_command` | Execute validate/deploy/run |
