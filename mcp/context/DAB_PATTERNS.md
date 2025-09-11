# DAB Patterns (Essential)

## Pattern Selection
- **Single notebook** → Simple ETL
- **Multiple notebooks with dependencies** → Multi-stage ETL  
- **MLflow detected** → ML Pipeline
- **Streaming operations** → Streaming Job

## 1. Simple ETL
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
            spark_version: "16.4.x-scala2.12"
            node_type_id: "i3.xlarge"
            num_workers: 2
      tasks:
        - task_key: process
          notebook_task:
            notebook_path: ./notebook.py
          job_cluster_key: main
```

## 2. Multi-stage ETL
```yaml
bundle:
  name: pipeline-etl
resources:
  jobs:
    pipeline:
      name: ${bundle.name}-${bundle.target}
      job_clusters:
        - job_cluster_key: main
          new_cluster:
            spark_version: "13.3.x-scala2.12"
            node_type_id: "i3.xlarge" 
            num_workers: 4
      tasks:
        - task_key: extract
          notebook_task:
            notebook_path: ./01_extract.py
        - task_key: transform
          depends_on: [{task_key: extract}]
          notebook_task:
            notebook_path: ./02_transform.py
```

## 3. ML Pipeline
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
      tasks:
        - task_key: train
          notebook_task:
            notebook_path: ./train.py
```

## Environment Targets
```yaml
targets:
  dev:
    mode: development
    default: true
  prod:
    mode: production
```