# DLT/Lakeflow Pipeline Patterns

Complete patterns for Lakeflow Declarative Pipelines (DLT) using Databricks Asset Bundles.

---

## DLT Medallion Architecture Pattern

### Directory Structure

```
dlt-pipeline/
├── databricks.yml
├── resources/
│   ├── pipelines.yml
│   ├── jobs.yml
│   └── schemas.yml
├── src/
│   └── dlt/
│       ├── bronze.py
│       ├── silver.py
│       └── gold.py
└── tests/
```

### databricks.yml

```yaml
bundle:
  name: dlt-pipeline

include:
  - resources/*.yml

variables:
  catalog:
    description: Unity Catalog name
    default: main
  bronze_schema:
    description: Bronze layer schema
    default: bronze
  silver_schema:
    description: Silver layer schema
    default: silver
  gold_schema:
    description: Gold layer schema
    default: gold

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
      service_principal_name: sp-dlt-prod
```

### resources/pipelines.yml

```yaml
resources:
  pipelines:
    # Bronze Layer
    bronze_pipeline:
      name: ${bundle.name}-bronze-${bundle.target}
      catalog: ${var.catalog}
      target: ${var.bronze_schema}
      serverless: true
      continuous: false
      development: ${bundle.target == "dev"}
      photon: true
      channel: CURRENT
      libraries:
        - notebook:
            path: ./src/dlt/bronze.py
      configuration:
        source_catalog: ${var.catalog}
        target_schema: ${var.bronze_schema}
      permissions:
        - level: CAN_MANAGE
          group_name: data-engineers

    # Silver Layer
    silver_pipeline:
      name: ${bundle.name}-silver-${bundle.target}
      catalog: ${var.catalog}
      target: ${var.silver_schema}
      serverless: true
      continuous: false
      development: ${bundle.target == "dev"}
      photon: true
      libraries:
        - notebook:
            path: ./src/dlt/silver.py
      configuration:
        bronze_schema: ${var.bronze_schema}
        silver_schema: ${var.silver_schema}

    # Gold Layer
    gold_pipeline:
      name: ${bundle.name}-gold-${bundle.target}
      catalog: ${var.catalog}
      target: ${var.gold_schema}
      serverless: true
      continuous: false
      development: ${bundle.target == "dev"}
      photon: true
      libraries:
        - notebook:
            path: ./src/dlt/gold.py
```

### resources/jobs.yml (Orchestrator)

```yaml
resources:
  jobs:
    # Orchestrator job to run all pipelines in sequence
    medallion_orchestrator:
      name: ${bundle.name}-orchestrator-${bundle.target}
      description: "Orchestrates medallion layer pipelines"

      tasks:
        - task_key: refresh_bronze
          pipeline_task:
            pipeline_id: ${resources.pipelines.bronze_pipeline.id}
            full_refresh: false

        - task_key: refresh_silver
          depends_on:
            - task_key: refresh_bronze
          pipeline_task:
            pipeline_id: ${resources.pipelines.silver_pipeline.id}
            full_refresh: false

        - task_key: refresh_gold
          depends_on:
            - task_key: refresh_silver
          pipeline_task:
            pipeline_id: ${resources.pipelines.gold_pipeline.id}
            full_refresh: false

      schedule:
        quartz_cron_expression: '0 0 */2 * * ?'  # every 2 hours
        timezone_id: UTC
        pause_status: ${bundle.target == "prod" ? "UNPAUSED" : "PAUSED"}
```

---

## Single Pipeline Configuration

For simpler use cases with a single pipeline:

```yaml
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
```

---

## Streaming Pipeline Configuration

```yaml
resources:
  pipelines:
    streaming_pipeline:
      name: ${bundle.name}-streaming-${bundle.target}
      catalog: ${var.catalog}
      target: ${var.schema}_streaming
      serverless: true
      continuous: true  # Enable continuous mode for streaming
      development: ${bundle.target == "dev"}
      libraries:
        - notebook:
            path: ./src/dlt/streaming_ingest.py
```

---

## Pipeline with Multiple Libraries

```yaml
resources:
  pipelines:
    multi_lib_pipeline:
      name: ${bundle.name}-${bundle.target}
      catalog: ${var.catalog}
      target: ${var.schema}
      serverless: true
      libraries:
        - notebook:
            path: ./src/dlt/bronze.py
        - notebook:
            path: ./src/dlt/silver.py
        - notebook:
            path: ./src/dlt/gold.py
      configuration:
        catalog: ${var.catalog}
        schema: ${var.schema}
```

---

## Pipeline Task Reference in Jobs

```yaml
tasks:
  - task_key: run_pipeline
    pipeline_task:
      pipeline_id: ${resources.pipelines.my_pipeline.id}
      full_refresh: false  # Incremental refresh (default)

  - task_key: full_refresh_pipeline
    pipeline_task:
      pipeline_id: ${resources.pipelines.my_pipeline.id}
      full_refresh: true  # Full refresh - reprocess all data
```

---

## DLT Configuration Options

| Option | Values | Description |
|--------|--------|-------------|
| `serverless` | true/false | Use serverless compute |
| `continuous` | true/false | Run continuously for streaming |
| `development` | true/false | Development mode (relaxed data quality) |
| `photon` | true/false | Enable Photon acceleration |
| `channel` | CURRENT/PREVIEW | DLT runtime channel |

---

## DLT Best Practices

1. **Serverless**: Prefer `serverless: true` for cost efficiency
2. **Development Mode**: Set `development: ${bundle.target == "dev"}` to use relaxed mode in dev
3. **Photon**: Enable `photon: true` for performance on supported operations
4. **Continuous**: Only use `continuous: true` for real-time streaming workloads
5. **Configuration**: Pass variables via `configuration` block to DLT notebooks
6. **Orchestration**: Use a job with `pipeline_task` to orchestrate multi-layer pipelines
7. **Full Refresh**: Use `full_refresh: true` sparingly, prefer incremental
8. **Channel**: Use `CURRENT` for stability, `PREVIEW` to test new features
