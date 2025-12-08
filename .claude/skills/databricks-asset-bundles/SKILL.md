---
name: databricks-asset-bundles
description: >-
  Use when generating, validating, or deploying Databricks Asset Bundles (DABs).
  Provides patterns, best practices, and YAML templates for bundle configuration.
  Triggers: databricks.yml, bundle validate, bundle deploy, job clusters,
  DLT/Lakeflow pipelines, MLflow experiments, model serving endpoints,
  Unity Catalog schemas/volumes, Databricks Apps, serverless compute.
  Workload types: ETL, ML/MLOps, SQL analytics, streaming, custom apps, multi-team projects.
  Emphasizes modular structure with resources/ folder organization.
---

# Databricks Asset Bundles (DABs) Skill

Generate, validate, and deploy Databricks Asset Bundles across all workload types.

---

## Detailed Patterns by Use Case

| Use Case | Reference File | Key Resources |
|----------|----------------|---------------|
| ETL/Data Engineering | [references/etl.md](references/etl.md) | jobs, schemas, volumes |
| ML/MLOps | [references/ml.md](references/ml.md) | experiments, models, endpoints, monitors |
| DLT Pipelines | [references/dlt.md](references/dlt.md) | pipelines, orchestrator jobs |
| Databricks Apps | [references/apps.md](references/apps.md) | apps, resource bindings, Flask/Gradio |
| Multi-Team Projects | [references/multi-team.md](references/multi-team.md) | nested includes, shared resources |

---

## Bundle File Organization

### When to Use Single vs Multi-File

| Project Size | Recommendation |
|--------------|----------------|
| 1 job, < 3 tasks | Single file |
| 1-2 jobs, < 5 tasks | Single or multi-file |
| 3+ jobs OR multiple resource types | Multi-file |
| ML projects with models/experiments | Multi-file |
| Team projects | Multi-file |

### Multi-File Structure

```
my-bundle/
├── databricks.yml           # Bundle metadata, variables, includes, targets
├── resources/               # Resource definitions
│   ├── jobs.yml
│   ├── pipelines.yml
│   └── ml_resources.yml
├── src/                     # Source code
└── tests/
```

---

## Core databricks.yml Template

```yaml
bundle:
  name: my-project

include:
  - resources/*.yml

variables:
  catalog:
    description: Unity Catalog name
    default: main
  schema:
    description: Target schema
    default: default

targets:
  dev:
    mode: development
    default: true
    variables:
      catalog: dev_catalog

  prod:
    mode: production
    variables:
      catalog: prod_catalog
    run_as:
      service_principal_name: sp-production
```

---

## Single-File Patterns

### Simple Job

```yaml
bundle:
  name: simple-job

resources:
  jobs:
    main_job:
      name: ${bundle.name}-${bundle.target}
      tasks:
        - task_key: process
          notebook_task:
            notebook_path: ./src/notebook.py

targets:
  dev:
    mode: development
    default: true
```

### Simple DLT Pipeline

```yaml
bundle:
  name: simple-dlt

resources:
  pipelines:
    main_pipeline:
      name: ${bundle.name}-${bundle.target}
      catalog: ${var.catalog}
      target: ${var.schema}
      serverless: true
      development: ${bundle.target == "dev"}
      libraries:
        - notebook:
            path: ./src/pipeline.py

targets:
  dev:
    default: true
```

---

## Supported Resource Types

| Resource | Description | Key Use Cases |
|----------|-------------|---------------|
| `jobs` | Workflow orchestration | ETL, ML training, batch inference |
| `pipelines` | Lakeflow Declarative Pipelines | Streaming, medallion architecture |
| `experiments` | MLflow experiments | ML experiment tracking |
| `registered_models` | Unity Catalog models | Model registry |
| `model_serving_endpoints` | Model serving | Real-time inference |
| `quality_monitors` | Lakehouse monitoring | Data/model quality |
| `schemas` | Unity Catalog schemas | Data organization |
| `volumes` | Unity Catalog volumes | File storage |
| `clusters` | Compute clusters | Shared compute |
| `dashboards` | AI/BI dashboards | Analytics visualization |
| `apps` | Custom web applications | Dashboards, job managers |
| `secret_scopes` | Secret management | Credentials storage |

---

## Task Types Reference

| Task Type | Key | Use Case |
|-----------|-----|----------|
| Notebook | `notebook_task` | Python/SQL/R notebooks |
| Python Script | `spark_python_task` | Python files (.py) |
| Python Wheel | `python_wheel_task` | Packaged Python |
| SQL | `sql_task` | SQL files, queries |
| dbt | `dbt_task` | dbt transformations |
| Pipeline | `pipeline_task` | DLT pipeline refresh |
| Run Job | `run_job_task` | Orchestrate other jobs |
| Condition | `condition_task` | Branching logic |
| For Each | `for_each_task` | Parallel iterations |

---

## Cluster Configuration

### Serverless (Recommended)

```yaml
# For notebooks - omit cluster config
tasks:
  - task_key: notebook_task
    notebook_task:
      notebook_path: ./notebook.py

# For Python/dbt - use environment_key
tasks:
  - task_key: python_task
    spark_python_task:
      python_file: ./main.py
    environment_key: default
environments:
  - environment_key: default
    spec:
      dependencies:
        - pandas>=2.0.0
```

### Job Cluster

```yaml
job_clusters:
  - job_cluster_key: main
    new_cluster:
      spark_version: "15.4.x-scala2.12"
      node_type_id: "i3.xlarge"
      num_workers: 4
tasks:
  - task_key: my_task
    job_cluster_key: main
```

### ML Runtime Cluster

```yaml
job_clusters:
  - job_cluster_key: ml
    new_cluster:
      spark_version: "15.4.x-ml-scala2.12"
      node_type_id: "i3.2xlarge"
      num_workers: 4
```

---

## Include Patterns

```yaml
# Basic
include:
  - resources/*.yml

# Recursive (multi-team)
include:
  - resources/**/*.yml

# Selective
include:
  - resources/jobs.yml
  - resources/pipelines.yml
```

---

## Resource File Naming Conventions

| Resource Type | Recommended Filename |
|---------------|---------------------|
| Jobs | `jobs.yml` |
| Pipelines | `pipelines.yml` |
| ML Resources | `ml_resources.yml` |
| Schemas | `schemas.yml` |
| Volumes | `volumes.yml` |
| Dashboards | `dashboards.yml` |
| Apps | `apps.yml` |

---

## CLI Commands

```bash
# Validate bundle
databricks bundle validate
databricks bundle validate -t prod

# Deploy to target
databricks bundle deploy -t dev

# Run a job
databricks bundle run -t dev main_job

# Generate from existing job
databricks bundle generate job --existing-job-id 123456

# Destroy resources
databricks bundle destroy -t dev
```

---

## Best Practices

### File Organization
- Use `resources/` folder for all resource definitions
- One file per resource type (or per team)
- Keep `databricks.yml` minimal

### Variables
```yaml
variables:
  catalog:
    description: Unity Catalog name  # Always add descriptions
    default: main
  warehouse_id:
    lookup:
      warehouse: my-warehouse  # Auto-lookup by name
```

### Security
```yaml
# Use secrets, not hardcoded values
spark_conf:
  api_key: ${secrets.my_scope.api_key}

# Add permissions for production
permissions:
  - level: CAN_MANAGE
    service_principal_name: sp-production
```

### Naming Conventions
- **Bundle name**: `descriptive-kebab-case`
- **Job name**: `${bundle.name}-${bundle.target}`
- **Resource keys**: `snake_case`
- **Task keys**: `snake_case`

---

## Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| Resources not found | Check `include:` paths match file locations |
| Duplicate resource keys | Ensure unique keys across all included files |
| Missing workspace host | Add `host:` under `workspace` or target |
| Invalid spark_version | Use format like `"15.4.x-scala2.12"` (with quotes) |
| YAML syntax error | Check indentation (2 spaces, no tabs) |

---

## References

- [Bundle Configuration Examples](https://docs.databricks.com/aws/en/dev-tools/bundles/examples)
- [Bundle Resources Reference](https://docs.databricks.com/aws/en/dev-tools/bundles/resources)
- [Task Types Reference](https://docs.databricks.com/aws/en/dev-tools/bundles/job-task-types)
- [Bundle Examples Repository](https://github.com/databricks/bundle-examples)
