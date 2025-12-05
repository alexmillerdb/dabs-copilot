# ML/MLOps Patterns

Complete patterns for ML training, serving, and monitoring using Databricks Asset Bundles.

---

## ML Training + Serving Project Pattern

### Directory Structure

```
ml-project/
├── databricks.yml
├── resources/
│   ├── jobs.yml
│   ├── ml_resources.yml
│   └── schemas.yml
├── src/
│   ├── training/
│   │   ├── train.py
│   │   └── evaluate.py
│   ├── inference/
│   │   └── batch_inference.py
│   └── feature_engineering/
│       └── features.py
└── tests/
```

### databricks.yml

```yaml
bundle:
  name: ml-project

include:
  - resources/*.yml

variables:
  catalog:
    description: Unity Catalog name
    default: main
  schema:
    description: Target schema
    default: ml_data
  experiment_path:
    description: MLflow experiment path
    default: /Shared/ml-project
  model_name:
    description: Registered model name

targets:
  dev:
    mode: development
    default: true
    variables:
      catalog: dev_catalog
      experiment_path: /Users/${workspace.current_user.userName}/ml-project
      model_name: ${var.catalog}.${var.schema}.ml_model_dev

  prod:
    mode: production
    variables:
      catalog: prod_catalog
      model_name: ${var.catalog}.${var.schema}.ml_model
    run_as:
      service_principal_name: sp-ml-prod
```

### resources/jobs.yml

```yaml
resources:
  jobs:
    # Training Pipeline
    training_pipeline:
      name: ${bundle.name}-training-${bundle.target}
      description: "ML training pipeline"

      job_clusters:
        - job_cluster_key: ml_cluster
          new_cluster:
            spark_version: "15.4.x-ml-scala2.12"
            node_type_id: "i3.2xlarge"
            num_workers: 4
            spark_conf:
              spark.databricks.delta.preview.enabled: "true"

      tasks:
        - task_key: feature_engineering
          job_cluster_key: ml_cluster
          notebook_task:
            notebook_path: ./src/feature_engineering/features.py
            base_parameters:
              catalog: ${var.catalog}
              schema: ${var.schema}

        - task_key: train_model
          job_cluster_key: ml_cluster
          depends_on:
            - task_key: feature_engineering
          notebook_task:
            notebook_path: ./src/training/train.py
            base_parameters:
              catalog: ${var.catalog}
              schema: ${var.schema}
              experiment_path: ${var.experiment_path}
              model_name: ${var.model_name}

        - task_key: evaluate_model
          job_cluster_key: ml_cluster
          depends_on:
            - task_key: train_model
          notebook_task:
            notebook_path: ./src/training/evaluate.py
            base_parameters:
              model_name: ${var.model_name}

      # File arrival trigger
      trigger:
        file_arrival:
          url: /Volumes/${var.catalog}/${var.schema}/input/training_data

    # Batch Inference Job
    batch_inference:
      name: ${bundle.name}-inference-${bundle.target}
      description: "Batch inference job"

      tasks:
        - task_key: run_inference
          notebook_task:
            notebook_path: ./src/inference/batch_inference.py
            base_parameters:
              catalog: ${var.catalog}
              schema: ${var.schema}
              model_name: ${var.model_name}

      schedule:
        quartz_cron_expression: '0 0 * * * ?'  # hourly
        timezone_id: UTC
```

### resources/ml_resources.yml

```yaml
resources:
  # MLflow Experiments
  experiments:
    training_experiment:
      name: ${var.experiment_path}
      permissions:
        - level: CAN_MANAGE
          group_name: ml-engineers
        - level: CAN_READ
          group_name: data-scientists

  # Registered Models
  registered_models:
    main_model:
      name: ${var.model_name}
      comment: "Production model for ${bundle.name}"
      permissions:
        - level: CAN_MANAGE
          group_name: ml-engineers

  # Model Serving Endpoint
  model_serving_endpoints:
    prediction_api:
      name: ${bundle.name}-api-${bundle.target}
      config:
        served_entities:
          - entity_name: ${var.model_name}
            entity_version: "1"
            workload_size: Small
            scale_to_zero_enabled: ${bundle.target == "dev"}
        auto_capture_config:
          catalog_name: ${var.catalog}
          schema_name: ${var.schema}
          table_name_prefix: inference_logs

  # Quality Monitor
  quality_monitors:
    inference_monitor:
      table_name: ${var.catalog}.${var.schema}.inference_logs
      output_schema_name: ${var.catalog}.${var.schema}
      inference_log:
        problem_type: PROBLEM_TYPE_REGRESSION
        prediction_col: prediction
        timestamp_col: timestamp
```

---

## MLflow Experiment Configuration

```yaml
resources:
  experiments:
    my_experiment:
      name: /Shared/${bundle.name}/${var.environment}/training
      permissions:
        - level: CAN_MANAGE
          group_name: data-scientists
        - level: CAN_READ
          group_name: ml-engineers
      description: MLflow experiment for tracking runs
```

---

## Registered Model Configuration

```yaml
resources:
  registered_models:
    my_model:
      name: ${var.catalog}.${var.schema}.${bundle.name}_model
      comment: "Main prediction model for ${bundle.name}"
      permissions:
        - level: CAN_MANAGE
          group_name: ml-engineers
        - level: CAN_READ
          group_name: data-scientists
```

---

## Model Serving Endpoint Configuration

```yaml
resources:
  model_serving_endpoints:
    my_endpoint:
      name: ${bundle.name}-${bundle.target}-endpoint
      config:
        served_entities:
          - entity_name: ${var.catalog}.${var.schema}.${bundle.name}_model
            entity_version: "1"
            workload_size: Small  # Small, Medium, Large
            scale_to_zero_enabled: true
        auto_capture_config:
          catalog_name: ${var.catalog}
          schema_name: ${var.schema}
          table_name_prefix: ${bundle.name}_inference_logs
        traffic_config:
          routes:
            - served_model_name: ${bundle.name}_model-1
              traffic_percentage: 100
```

---

## Quality Monitor Configuration

```yaml
resources:
  quality_monitors:
    model_monitor:
      table_name: ${var.catalog}.${var.schema}.${bundle.name}_inference_logs
      output_schema_name: ${var.catalog}.${var.schema}
      slicing_exprs:
        - "model_version"
        - "request_date"
      inference_log:
        problem_type: PROBLEM_TYPE_CLASSIFICATION  # or PROBLEM_TYPE_REGRESSION
        prediction_col: "prediction"
        label_col: "label"
        model_id_col: "model_id"
        timestamp_col: "timestamp"
```

---

## ML Best Practices

1. **ML Runtime**: Use `spark_version: "15.4.x-ml-scala2.12"` for ML workloads
2. **Experiment Paths**: Use user-scoped paths in dev, shared paths in prod
3. **Model Naming**: Use Unity Catalog 3-level naming: `catalog.schema.model_name`
4. **Scale to Zero**: Enable in dev to reduce costs, consider keeping warm in prod
5. **Inference Logging**: Configure `auto_capture_config` to log predictions for monitoring
6. **Quality Monitors**: Set up monitors to detect data drift and model degradation
7. **Triggers**: Use `file_arrival` trigger for automated retraining on new data
8. **Permissions**: ML engineers manage, data scientists read
