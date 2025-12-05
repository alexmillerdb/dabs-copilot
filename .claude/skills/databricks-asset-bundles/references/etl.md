# ETL/Data Engineering Patterns

Complete patterns for ETL workloads using Databricks Asset Bundles.

---

## Multi-Stage ETL Project Pattern

### Directory Structure

```
etl-pipeline/
├── databricks.yml
├── resources/
│   ├── jobs.yml
│   └── schemas.yml
├── src/
│   └── notebooks/
│       ├── 01_extract.py
│       ├── 02_transform.py
│       └── 03_load.py
└── tests/
```

### databricks.yml

```yaml
bundle:
  name: etl-pipeline

include:
  - resources/*.yml

variables:
  catalog:
    description: Unity Catalog name
    default: main
  schema:
    description: Target schema
    default: etl_data
  source_path:
    description: Source data path
    default: /Volumes/main/raw/input

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
      service_principal_name: sp-etl-prod
```

### resources/jobs.yml

```yaml
resources:
  jobs:
    etl_job:
      name: ${bundle.name}-${bundle.target}
      description: "ETL pipeline: extract → transform → load"

      # Shared job cluster for all tasks
      job_clusters:
        - job_cluster_key: etl_cluster
          new_cluster:
            spark_version: "15.4.x-scala2.12"
            node_type_id: "i3.xlarge"
            num_workers: 4
            spark_conf:
              spark.sql.adaptive.enabled: "true"

      # Email notifications
      email_notifications:
        on_failure:
          - data-team@company.com
        on_success:
          - data-team@company.com

      # Task definitions
      tasks:
        - task_key: extract
          job_cluster_key: etl_cluster
          notebook_task:
            notebook_path: ./src/notebooks/01_extract.py
            base_parameters:
              catalog: ${var.catalog}
              schema: ${var.schema}
              source_path: ${var.source_path}
          timeout_seconds: 3600

        - task_key: transform
          job_cluster_key: etl_cluster
          depends_on:
            - task_key: extract
          notebook_task:
            notebook_path: ./src/notebooks/02_transform.py
            base_parameters:
              catalog: ${var.catalog}
              schema: ${var.schema}

        - task_key: load
          job_cluster_key: etl_cluster
          depends_on:
            - task_key: transform
          notebook_task:
            notebook_path: ./src/notebooks/03_load.py
            base_parameters:
              catalog: ${var.catalog}
              schema: ${var.schema}

      # Schedule (paused in dev)
      schedule:
        quartz_cron_expression: '0 0 6 * * ?'
        timezone_id: America/New_York
        pause_status: ${bundle.target == "prod" ? "UNPAUSED" : "PAUSED"}

      # Permissions
      permissions:
        - level: CAN_MANAGE
          group_name: data-engineers
        - level: CAN_VIEW
          group_name: data-analysts
```

### resources/schemas.yml

```yaml
resources:
  schemas:
    etl_schema:
      name: ${var.schema}
      catalog_name: ${var.catalog}
      comment: "ETL pipeline data schema"
      grants:
        - principal: data-engineers
          privileges:
            - ALL_PRIVILEGES
```

---

## Volume Configuration

```yaml
# resources/volumes.yml
resources:
  volumes:
    # Input data volume
    input_volume:
      name: input_data
      catalog_name: ${var.catalog}
      schema_name: ${bundle.name}_${bundle.target}
      volume_type: MANAGED
      comment: "Input data for ${bundle.name}"
      grants:
        - principal: data-engineers
          privileges:
            - READ_VOLUME
            - WRITE_VOLUME

    # Output/artifacts volume
    output_volume:
      name: output_data
      catalog_name: ${var.catalog}
      schema_name: ${bundle.name}_${bundle.target}
      volume_type: MANAGED
      comment: "Output data and artifacts"

    # Checkpoints volume (for streaming)
    checkpoints_volume:
      name: checkpoints
      catalog_name: ${var.catalog}
      schema_name: ${bundle.name}_${bundle.target}
      volume_type: MANAGED
      comment: "Streaming checkpoints"
```

---

## Data Quality Job Pattern

```yaml
resources:
  jobs:
    data_quality:
      name: ${bundle.name}-dq-${bundle.target}
      description: Data quality checks
      tasks:
        - task_key: run_quality_checks
          notebook_task:
            notebook_path: ./src/notebooks/quality_checks.py
            base_parameters:
              catalog: ${var.catalog}
              schema: ${var.schema}
```

---

## ETL Best Practices

1. **Job Clusters**: Use shared `job_clusters` for multi-task ETL jobs to reduce startup time
2. **Notifications**: Configure `email_notifications` for on_failure at minimum
3. **Schedules**: Use `pause_status` conditional on target to avoid dev jobs running on schedule
4. **Timeouts**: Set `timeout_seconds` on long-running tasks
5. **Dependencies**: Use `depends_on` to create task DAGs
6. **Parameters**: Pass catalog/schema via `base_parameters` for environment flexibility
7. **Permissions**: Grant `CAN_MANAGE` to owners, `CAN_VIEW` to stakeholders
