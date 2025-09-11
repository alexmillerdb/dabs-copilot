# Cluster Configs (Essential)

## Serverless Compute (Preferred)
- **Job (notebook task)**: Omit new_cluster/existing_cluster_id - serverless by default
- **Job (Python/wheel/dbt)**: Add environment_key and environments section
- **Pipeline (DLT)**: Add serverless: true to pipeline config

```yaml
# Notebook task - serverless by default
tasks:
  - task_key: process
    notebook_task:
      notebook_path: ./notebook.py
    # No cluster config needed

# Python/wheel task - needs environment
environments:
  my_env:
    dependencies:
      - "pandas>=1.5.0"
tasks:
  - task_key: process
    python_wheel_task:
      package_name: "my_package"
    environment_key: my_env

# DLT Pipeline
pipelines:
  my_pipeline:
    serverless: true
    libraries:
      - notebook: {path: ./dlt_notebook.py}
```

## Traditional Clusters (When Serverless Not Available)

### By Workload
- **ETL**: i3.xlarge, 2-8 workers, spark.sql.adaptive.enabled=true
- **ML**: i3.2xlarge, 4-12 workers, ML runtime 14.3.x-ml
- **GPU ML**: g4dn.xlarge, 1-4 workers, GPU runtime
- **Streaming**: i3.xlarge, 2-6 workers, enable_elastic_disk=true

### By Data Size
- **< 10GB**: i3.large, 1-2 workers
- **10-100GB**: i3.xlarge, 2-8 workers  
- **100GB-1TB**: i3.2xlarge, 4-16 workers
- **> 1TB**: i3.4xlarge, 8-32 workers

### Environment Sizing
```yaml
# Development
node_type_id: "i3.large"
num_workers: 1-2

# Production  
node_type_id: "i3.2xlarge"
num_workers: 4-16
```