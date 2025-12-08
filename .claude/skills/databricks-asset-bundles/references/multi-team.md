# Multi-Team Project Patterns

Patterns for organizing large-scale, multi-team Databricks Asset Bundles.

---

## Multi-Team Directory Structure

```
enterprise-platform/
├── databricks.yml
├── resources/
│   ├── team_data_eng/
│   │   ├── jobs.yml
│   │   └── pipelines.yml
│   ├── team_data_sci/
│   │   ├── jobs.yml
│   │   └── ml_resources.yml
│   └── shared/
│       ├── schemas.yml
│       └── volumes.yml
├── src/
│   ├── data_eng/
│   └── data_sci/
└── README.md
```

---

## databricks.yml

```yaml
bundle:
  name: enterprise-platform

# Include all resource files recursively
include:
  - resources/**/*.yml

variables:
  catalog:
    default: main
  environment:
    default: dev

targets:
  dev:
    mode: development
    default: true

  staging:
    mode: development
    workspace:
      host: https://staging.cloud.databricks.com

  prod:
    mode: production
    workspace:
      host: https://prod.cloud.databricks.com
    run_as:
      service_principal_name: sp-enterprise-prod
```

---

## Team-Specific Resource Files

### resources/team_data_eng/jobs.yml

```yaml
# Data Engineering Team Jobs
resources:
  jobs:
    ingestion_job:
      name: ${bundle.name}-ingestion-${bundle.target}
      description: "Data ingestion pipeline"

      job_clusters:
        - job_cluster_key: etl_cluster
          new_cluster:
            spark_version: "15.4.x-scala2.12"
            node_type_id: "i3.xlarge"
            num_workers: 4

      tasks:
        - task_key: ingest
          job_cluster_key: etl_cluster
          notebook_task:
            notebook_path: ./src/data_eng/ingest.py

      permissions:
        - level: CAN_MANAGE
          group_name: data-engineers
        - level: CAN_VIEW
          group_name: data-scientists
```

### resources/team_data_sci/ml_resources.yml

```yaml
# Data Science Team ML Resources
resources:
  experiments:
    ds_experiment:
      name: /Shared/${bundle.name}/data-science
      permissions:
        - level: CAN_MANAGE
          group_name: data-scientists

  registered_models:
    ds_model:
      name: ${var.catalog}.ml_models.prediction_model
      permissions:
        - level: CAN_MANAGE
          group_name: data-scientists
        - level: CAN_READ
          group_name: ml-engineers
```

---

## Shared Resources

### resources/shared/schemas.yml

```yaml
# Shared schemas across teams
resources:
  schemas:
    raw_data:
      name: raw
      catalog_name: ${var.catalog}
      comment: "Raw data landing zone"
      grants:
        - principal: data-engineers
          privileges: [ALL_PRIVILEGES]
        - principal: data-scientists
          privileges: [USE_SCHEMA, SELECT]

    processed_data:
      name: processed
      catalog_name: ${var.catalog}
      comment: "Processed data for analytics"
      grants:
        - principal: data-engineers
          privileges: [ALL_PRIVILEGES]
        - principal: data-scientists
          privileges: [USE_SCHEMA, SELECT]
        - principal: data-analysts
          privileges: [USE_SCHEMA, SELECT]
```

### resources/shared/volumes.yml

```yaml
# Shared volumes across teams
resources:
  volumes:
    shared_input:
      name: shared_input
      catalog_name: ${var.catalog}
      schema_name: raw
      volume_type: MANAGED
      grants:
        - principal: data-engineers
          privileges: [READ_VOLUME, WRITE_VOLUME]
        - principal: data-scientists
          privileges: [READ_VOLUME]

    shared_output:
      name: shared_output
      catalog_name: ${var.catalog}
      schema_name: processed
      volume_type: MANAGED
```

---

## Include Patterns

### Recursive Include (All Teams)

```yaml
include:
  - resources/**/*.yml
```

### Selective Include (Specific Teams)

```yaml
include:
  - resources/team_data_eng/*.yml
  - resources/shared/*.yml
```

### Environment-Specific Include

```yaml
include:
  - resources/common/*.yml
  - resources/${bundle.target}/*.yml  # Target-specific configs
```

---

## Cross-Team Permissions

```yaml
permissions:
  # Team ownership
  - level: CAN_MANAGE
    group_name: data-engineers

  # Cross-team visibility
  - level: CAN_VIEW
    group_name: data-scientists

  # Service account for automation
  - level: CAN_MANAGE_RUN
    service_principal_name: sp-automation
```

---

## Multi-Workspace Deployment

```yaml
targets:
  dev:
    mode: development
    default: true
    workspace:
      host: https://dev.cloud.databricks.com

  staging:
    mode: development
    workspace:
      host: https://staging.cloud.databricks.com

  prod-us:
    mode: production
    workspace:
      host: https://prod-us.cloud.databricks.com
    run_as:
      service_principal_name: sp-prod-us

  prod-eu:
    mode: production
    workspace:
      host: https://prod-eu.cloud.databricks.com
    run_as:
      service_principal_name: sp-prod-eu
```

---

## Multi-Team Best Practices

1. **Directory Structure**: Organize resources by team under `resources/team_name/`
2. **Shared Resources**: Keep shared schemas/volumes in `resources/shared/`
3. **Recursive Include**: Use `resources/**/*.yml` to include all team files
4. **Unique Keys**: Ensure resource keys are unique across all included files
5. **Permissions**: Grant team ownership and cross-team view access
6. **Service Principals**: Use `run_as` for production deployments
7. **Multi-Workspace**: Define separate targets for different workspaces/regions
8. **Code Reviews**: Separate resource files make PRs easier to review
