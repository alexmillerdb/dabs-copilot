# Databricks Asset Bundle Patterns

This document provides common patterns for generating Databricks Asset Bundles (DABs). Use these as reference when generating bundle configurations based on notebook analysis.

## 1. Simple ETL Job Pattern

**Use when:** Single notebook or simple pipeline with basic dependencies

```yaml
bundle:
  name: simple-etl
  description: Simple ETL pipeline with single notebook

workspace:
  host: ${workspace.host}
  root_path: /Workspace/Users/${workspace.current_user.userName}/.bundle/${bundle.name}/${bundle.target}

variables:
  catalog:
    description: Unity Catalog catalog name
    default: ${bundle.target}
  warehouse_id:
    description: SQL warehouse for data processing
    default: ${var.databricks_warehouse_id}

resources:
  jobs:
    etl_job:
      name: ${bundle.name}-${bundle.target}
      description: Simple ETL job from notebook analysis

      job_clusters:
        - job_cluster_key: main_cluster
          new_cluster:
            spark_version: "13.3.x-scala2.12"
            node_type_id: "i3.xlarge"
            num_workers: 2
            spark_conf:
              spark.sql.adaptive.enabled: "true"
              spark.sql.adaptive.coalescePartitions.enabled: "true"

      tasks:
        - task_key: etl_process
          notebook_task:
            notebook_path: ./notebooks/main_etl.py
            base_parameters:
              catalog: ${var.catalog}
              warehouse_id: ${var.warehouse_id}
          job_cluster_key: main_cluster
          timeout_seconds: 3600

      email_notifications:
        on_failure:
          - ${workspace.current_user.userName}

targets:
  dev:
    mode: development
    default: true
    workspace:
      host: ${workspace.host}
    variables:
      catalog: dev_catalog

  prod:
    mode: production
    workspace:
      host: ${workspace.host}
    variables:
      catalog: main
```

## 2. Multi-Stage ETL Pipeline Pattern

**Use when:** Multiple notebooks with dependencies, extract-transform-load stages

```yaml
bundle:
  name: multi-stage-etl
  description: Multi-stage ETL pipeline with task dependencies

workspace:
  host: ${workspace.host}
  root_path: /Workspace/Users/${workspace.current_user.userName}/.bundle/${bundle.name}/${bundle.target}

variables:
  catalog:
    description: Unity Catalog catalog name
    default: ${bundle.target}
  source_schema:
    description: Source data schema
    default: raw
  target_schema:
    description: Target data schema
    default: silver

resources:
  jobs:
    etl_pipeline:
      name: ${bundle.name}-pipeline-${bundle.target}
      description: Multi-stage ETL pipeline

      job_clusters:
        - job_cluster_key: etl_cluster
          new_cluster:
            spark_version: "13.3.x-scala2.12"
            node_type_id: "i3.xlarge"
            num_workers: 4
            spark_conf:
              spark.sql.adaptive.enabled: "true"
              spark.databricks.delta.optimizeWrite.enabled: "true"

      tasks:
        - task_key: extract_data
          notebook_task:
            notebook_path: ./notebooks/01_extract.py
            base_parameters:
              catalog: ${var.catalog}
              source_schema: ${var.source_schema}
          job_cluster_key: etl_cluster

        - task_key: transform_data
          depends_on:
            - task_key: extract_data
          notebook_task:
            notebook_path: ./notebooks/02_transform.py
            base_parameters:
              catalog: ${var.catalog}
              source_schema: ${var.source_schema}
              target_schema: ${var.target_schema}
          job_cluster_key: etl_cluster

        - task_key: load_data
          depends_on:
            - task_key: transform_data
          notebook_task:
            notebook_path: ./notebooks/03_load.py
            base_parameters:
              catalog: ${var.catalog}
              target_schema: ${var.target_schema}
          job_cluster_key: etl_cluster

        - task_key: data_quality_check
          depends_on:
            - task_key: load_data
          notebook_task:
            notebook_path: ./notebooks/04_quality_check.py
            base_parameters:
              catalog: ${var.catalog}
              target_schema: ${var.target_schema}
          job_cluster_key: etl_cluster

      schedule:
        quartz_cron_expression: "0 2 * * *" # Daily at 2 AM
        timezone_id: "UTC"

      email_notifications:
        on_failure:
          - ${workspace.current_user.userName}
        on_success:
          - data-team@company.com

targets:
  dev:
    mode: development
    default: true
    variables:
      catalog: dev_catalog
      source_schema: raw_dev
      target_schema: silver_dev

  prod:
    mode: production
    variables:
      catalog: main
      source_schema: raw
      target_schema: silver
```

## 3. ML Training Pipeline Pattern

**Use when:** Machine learning workflow with training, evaluation, and model registration

```yaml
bundle:
  name: ml-training-pipeline
  description: ML model training and registration pipeline

workspace:
  host: ${workspace.host}
  root_path: /Workspace/Users/${workspace.current_user.userName}/.bundle/${bundle.name}/${bundle.target}

variables:
  catalog:
    description: Unity Catalog catalog name
    default: ${bundle.target}
  model_name:
    description: MLflow model name
    default: customer_churn_model
  experiment_name:
    description: MLflow experiment name
    default: /Users/${workspace.current_user.userName}/${bundle.name}

resources:
  jobs:
    ml_training_job:
      name: ${var.model_name}-training-${bundle.target}
      description: ML model training pipeline

      job_clusters:
        - job_cluster_key: ml_cluster
          new_cluster:
            spark_version: "14.3.x-ml-scala2.12"
            node_type_id: "i3.2xlarge"
            num_workers: 4
            spark_conf:
              spark.sql.execution.arrow.pyspark.enabled: "true"
              spark.databricks.delta.preview.enabled: "true"

      tasks:
        - task_key: data_preparation
          notebook_task:
            notebook_path: ./notebooks/01_data_prep.py
            base_parameters:
              catalog: ${var.catalog}
              experiment_name: ${var.experiment_name}
          job_cluster_key: ml_cluster

        - task_key: feature_engineering
          depends_on:
            - task_key: data_preparation
          notebook_task:
            notebook_path: ./notebooks/02_feature_engineering.py
            base_parameters:
              catalog: ${var.catalog}
              experiment_name: ${var.experiment_name}
          job_cluster_key: ml_cluster

        - task_key: model_training
          depends_on:
            - task_key: feature_engineering
          notebook_task:
            notebook_path: ./notebooks/03_model_training.py
            base_parameters:
              catalog: ${var.catalog}
              model_name: ${var.model_name}
              experiment_name: ${var.experiment_name}
          job_cluster_key: ml_cluster

        - task_key: model_evaluation
          depends_on:
            - task_key: model_training
          notebook_task:
            notebook_path: ./notebooks/04_model_evaluation.py
            base_parameters:
              catalog: ${var.catalog}
              model_name: ${var.model_name}
              experiment_name: ${var.experiment_name}
          job_cluster_key: ml_cluster

        - task_key: model_registration
          depends_on:
            - task_key: model_evaluation
          notebook_task:
            notebook_path: ./notebooks/05_model_registration.py
            base_parameters:
              catalog: ${var.catalog}
              model_name: ${var.model_name}
              experiment_name: ${var.experiment_name}
              stage: ${bundle.target}
          job_cluster_key: ml_cluster

  model_serving_endpoints:
    churn_model_endpoint:
      name: ${var.model_name}-${bundle.target}
      config:
        served_models:
          - model_name: ${var.catalog}.${var.model_name}
            model_version: latest
            workload_size: Small
            scale_to_zero_enabled: true

targets:
  dev:
    mode: development
    default: true
    variables:
      catalog: dev_catalog
      model_name: customer_churn_model_dev

  prod:
    mode: production
    variables:
      catalog: main
      model_name: customer_churn_model
```

## 4. Streaming Job Pattern

**Use when:** Real-time data processing with structured streaming

```yaml
bundle:
  name: streaming-pipeline
  description: Real-time streaming data pipeline

workspace:
  host: ${workspace.host}
  root_path: /Workspace/Users/${workspace.current_user.userName}/.bundle/${bundle.name}/${bundle.target}

variables:
  catalog:
    description: Unity Catalog catalog name
    default: ${bundle.target}
  checkpoint_path:
    description: Streaming checkpoint location
    default: /tmp/checkpoints/${bundle.name}

resources:
  jobs:
    streaming_job:
      name: ${bundle.name}-stream-${bundle.target}
      description: Real-time streaming job
      
      job_clusters:
        - job_cluster_key: streaming_cluster
          new_cluster:
            spark_version: "13.3.x-scala2.12"
            node_type_id: "i3.xlarge"
            num_workers: 2
            enable_elastic_disk: true
            spark_conf:
              spark.sql.streaming.metricsEnabled: "true"
              spark.sql.streaming.stateStore.stateSchemaCheck: "false"

      tasks:
        - task_key: streaming_process
          notebook_task:
            notebook_path: ./notebooks/streaming_processor.py
            base_parameters:
              catalog: ${var.catalog}
              checkpoint_path: ${var.checkpoint_path}
          job_cluster_key: streaming_cluster

      # Streaming jobs should not have schedules - they run continuously
      max_concurrent_runs: 1

targets:
  dev:
    mode: development
    default: true
    variables:
      catalog: dev_catalog
      checkpoint_path: /tmp/checkpoints/streaming_dev

  prod:
    mode: production
    variables:
      catalog: main
      checkpoint_path: /dbfs/checkpoints/streaming_prod
```

## 5. Complex Multi-Resource Pattern

**Use when:** Multiple jobs, pipelines, and resources with dependencies

```yaml
bundle:
  name: complex-data-platform
  description: Complex data platform with multiple resources

workspace:
  host: ${workspace.host}
  root_path: /Workspace/Users/${workspace.current_user.userName}/.bundle/${bundle.name}/${bundle.target}

variables:
  catalog:
    description: Unity Catalog catalog name
    default: ${bundle.target}
  environment:
    description: Environment name
    default: ${bundle.target}

resources:
  # Data ingestion job
  jobs:
    ingestion_job:
      name: data-ingestion-${var.environment}
      job_clusters:
        - job_cluster_key: ingestion_cluster
          new_cluster:
            spark_version: "13.3.x-scala2.12"
            node_type_id: "i3.large"
            num_workers: 2
      tasks:
        - task_key: ingest_data
          notebook_task:
            notebook_path: ./notebooks/ingestion/ingest_data.py

    # Processing job that depends on ingestion
    processing_job:
      name: data-processing-${var.environment}
      job_clusters:
        - job_cluster_key: processing_cluster
          new_cluster:
            spark_version: "13.3.x-scala2.12"
            node_type_id: "i3.xlarge"
            num_workers: 4
      tasks:
        - task_key: process_data
          notebook_task:
            notebook_path: ./notebooks/processing/process_data.py

  # Delta Live Tables pipeline
  pipelines:
    bronze_silver_pipeline:
      name: bronze-silver-${var.environment}
      target: ${var.catalog}.bronze_silver
      libraries:
        - notebook:
            path: ./notebooks/dlt/bronze_tables.py
        - notebook:
            path: ./notebooks/dlt/silver_tables.py
      clusters:
        - label: default
          spark_conf:
            spark.databricks.delta.preview.enabled: "true"
          node_type_id: "i3.xlarge"
          num_workers: 2

  # Model serving endpoint
  model_serving_endpoints:
    ml_model_endpoint:
      name: ml-model-${var.environment}
      config:
        served_models:
          - model_name: ${var.catalog}.ml_model
            model_version: latest
            workload_size: Small

targets:
  dev:
    mode: development
    default: true
    variables:
      catalog: dev_catalog
      environment: dev

  staging:
    mode: development
    variables:
      catalog: staging_catalog
      environment: staging

  prod:
    mode: production
    variables:
      catalog: main
      environment: prod
```

## Pattern Selection Guidelines

### Based on Workflow Type Detection:

- **Single notebook, simple dependencies** → Use Simple ETL Job Pattern
- **Multiple stages, clear dependencies** → Use Multi-Stage ETL Pipeline Pattern
- **MLflow imports, model training** → Use ML Training Pipeline Pattern
- **Streaming operations detected** → Use Streaming Job Pattern
- **Complex dependencies, multiple resource types** → Use Complex Multi-Resource Pattern

### Based on Analysis Results:

- **Dependencies < 5** → Simple pattern
- **Dependencies 5-15** → Multi-stage pattern
- **MLflow/ML libraries detected** → ML pattern
- **Streaming operations** → Streaming pattern
- **Multiple notebook types** → Complex pattern

### Customization Guidelines:

1. **Always adapt the pattern** - Don't copy exactly, modify based on analysis
2. **Include detected parameters** - Use actual widget parameters found
3. **Match cluster size to data size** - Reference cluster configuration guide
4. **Add Unity Catalog tables** - Include actual tables from analysis
5. **Set appropriate schedules** - Based on workflow type and complexity
6. **Include error notifications** - Always add email notifications
7. **Environment-specific variables** - Adapt for dev/staging/prod

## Common Modifications:

- **Add custom Docker images** if detected in notebook
- **Include GPU clusters** for ML workloads with deep learning
- **Add retry policies** for production workflows  
- **Include monitoring and alerting** for critical pipelines
- **Add data quality checks** for ETL workflows
- **Include model endpoints** for ML training jobs