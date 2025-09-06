# Databricks Cluster Configuration Guidelines

This document provides guidelines for selecting appropriate cluster configurations based on workload analysis and data characteristics.

## Cluster Selection Matrix

### Based on Workload Type

#### ETL Workloads
```yaml
job_clusters:
  - job_cluster_key: etl_cluster
    new_cluster:
      spark_version: "13.3.x-scala2.12"
      node_type_id: "i3.xlarge"        # 4 cores, 30GB RAM
      num_workers: 2-8                 # Scale based on data size
      spark_conf:
        spark.sql.adaptive.enabled: "true"
        spark.sql.adaptive.coalescePartitions.enabled: "true"
        spark.sql.adaptive.skewJoin.enabled: "true"
        spark.databricks.delta.optimizeWrite.enabled: "true"
```

**Use when:** Data transformation, aggregation, joins, standard SQL operations

#### ML Training Workloads
```yaml
job_clusters:
  - job_cluster_key: ml_cluster
    new_cluster:
      spark_version: "14.3.x-ml-scala2.12"  # ML runtime
      node_type_id: "i3.2xlarge"            # 8 cores, 60GB RAM
      num_workers: 4-12
      spark_conf:
        spark.sql.execution.arrow.pyspark.enabled: "true"
        spark.databricks.ml.automl.enabled: "true"
        spark.sql.adaptive.enabled: "true"
```

**Use when:** MLflow imports detected, scikit-learn, pandas ML operations

#### ML Training with GPU
```yaml
job_clusters:
  - job_cluster_key: gpu_ml_cluster
    new_cluster:
      spark_version: "14.3.x-gpu-ml-scala2.12"
      node_type_id: "g4dn.xlarge"           # GPU instance
      num_workers: 2-4
      spark_conf:
        spark.sql.execution.arrow.pyspark.enabled: "true"
        spark.task.resource.gpu.amount: "1"
```

**Use when:** TensorFlow, PyTorch, deep learning libraries detected

#### Streaming Workloads
```yaml
job_clusters:
  - job_cluster_key: streaming_cluster
    new_cluster:
      spark_version: "13.3.x-scala2.12"
      node_type_id: "i3.xlarge"
      num_workers: 2-6
      enable_elastic_disk: true
      spark_conf:
        spark.sql.streaming.metricsEnabled: "true"
        spark.sql.streaming.stateStore.stateSchemaCheck: "false"
        spark.sql.streaming.checkpointLocation.cloud.enabled: "true"
```

**Use when:** Streaming operations, real-time processing detected

#### Data Science/Analytics
```yaml
job_clusters:
  - job_cluster_key: analytics_cluster
    new_cluster:
      spark_version: "13.3.x-scala2.12"
      node_type_id: "i3.large"              # 2 cores, 15GB RAM
      num_workers: 1-4
      spark_conf:
        spark.sql.execution.arrow.pyspark.enabled: "true"
        spark.sql.adaptive.enabled: "true"
```

**Use when:** Exploratory analysis, reporting, visualization

## Node Type Selection Guide

### Based on Data Size and Complexity

#### Small Data (< 10GB)
```yaml
node_type_id: "i3.large"    # 2 cores, 15GB RAM
num_workers: 1-2
```

#### Medium Data (10GB - 100GB)
```yaml
node_type_id: "i3.xlarge"   # 4 cores, 30GB RAM
num_workers: 2-8
```

#### Large Data (100GB - 1TB)
```yaml
node_type_id: "i3.2xlarge"  # 8 cores, 60GB RAM
num_workers: 4-16
```

#### Very Large Data (> 1TB)
```yaml
node_type_id: "i3.4xlarge"  # 16 cores, 122GB RAM
num_workers: 8-32
```

### Memory-Intensive Workloads
```yaml
# For large datasets that need to fit in memory
node_type_id: "r5.2xlarge"  # 8 cores, 64GB RAM
node_type_id: "r5.4xlarge"  # 16 cores, 128GB RAM
node_type_id: "r5.8xlarge"  # 32 cores, 256GB RAM
```

### Compute-Intensive Workloads
```yaml
# For CPU-heavy transformations
node_type_id: "c5.2xlarge"  # 8 cores, 16GB RAM
node_type_id: "c5.4xlarge"  # 16 cores, 32GB RAM
node_type_id: "c5.9xlarge"  # 36 cores, 72GB RAM
```

## Spark Configuration by Workload

### ETL Optimizations
```yaml
spark_conf:
  spark.sql.adaptive.enabled: "true"
  spark.sql.adaptive.coalescePartitions.enabled: "true"
  spark.sql.adaptive.skewJoin.enabled: "true"
  spark.databricks.delta.optimizeWrite.enabled: "true"
  spark.databricks.delta.autoCompact.enabled: "true"
  spark.sql.adaptive.advisoryPartitionSizeInBytes: "128MB"
```

### ML Workload Optimizations
```yaml
spark_conf:
  spark.sql.execution.arrow.pyspark.enabled: "true"
  spark.sql.execution.arrow.maxRecordsPerBatch: "10000"
  spark.databricks.ml.automl.enabled: "true"
  spark.sql.adaptive.enabled: "true"
  spark.serializer: "org.apache.spark.serializer.KryoSerializer"
```

### Streaming Optimizations
```yaml
spark_conf:
  spark.sql.streaming.metricsEnabled: "true"
  spark.sql.streaming.stateStore.stateSchemaCheck: "false"
  spark.sql.streaming.checkpointLocation.cloud.enabled: "true"
  spark.sql.streaming.continuous.enabled: "true"
  spark.sql.streaming.ui.enabled: "true"
```

### Large Dataset Optimizations
```yaml
spark_conf:
  spark.sql.adaptive.enabled: "true"
  spark.sql.adaptive.maxShuffleHashJoinLocalMapThreshold: "200MB"
  spark.sql.adaptive.advisoryPartitionSizeInBytes: "256MB"
  spark.sql.adaptive.coalescePartitions.enabled: "true"
  spark.databricks.delta.optimizeWrite.enabled: "true"
  spark.databricks.photon.enabled: "true"  # If available
```

## Decision Matrix

### Use this logic to determine cluster configuration:

```python
def select_cluster_config(analysis_result):
    # Data size estimation
    data_size = estimate_data_size(analysis_result)
    
    # Workload type detection
    workflow_type = analysis_result.get('patterns', {}).get('workflow_type')
    
    # Dependencies analysis
    has_ml_libs = any('mlflow' in dep or 'sklearn' in dep 
                     for dep in analysis_result.get('dependencies', {}).get('imports', []))
    
    has_gpu_libs = any('tensorflow' in dep or 'torch' in dep 
                      for dep in analysis_result.get('dependencies', {}).get('imports', []))
    
    has_streaming = 'streaming' in str(analysis_result.get('databricks_features', {}))
    
    # Configuration selection logic
    if has_gpu_libs:
        return gpu_ml_config()
    elif has_ml_libs or workflow_type == 'ML':
        return ml_config(data_size)
    elif has_streaming or workflow_type == 'streaming':
        return streaming_config(data_size)
    elif workflow_type == 'ETL':
        return etl_config(data_size)
    else:
        return analytics_config(data_size)
```

## Environment-Specific Adjustments

### Development Environment
```yaml
# Smaller, cheaper clusters for dev
job_clusters:
  - job_cluster_key: dev_cluster
    new_cluster:
      node_type_id: "i3.large"      # Smaller nodes
      num_workers: 1-2               # Fewer workers
      spot_bid_price_percent: 50     # Use spot instances
```

### Staging Environment
```yaml
# Medium-sized clusters for testing
job_clusters:
  - job_cluster_key: staging_cluster
    new_cluster:
      node_type_id: "i3.xlarge"     # Medium nodes
      num_workers: 2-4               # Moderate workers
      spot_bid_price_percent: 70     # Some spot instances
```

### Production Environment
```yaml
# Full-sized, reliable clusters
job_clusters:
  - job_cluster_key: prod_cluster
    new_cluster:
      node_type_id: "i3.2xlarge"    # Larger nodes
      num_workers: 4-16              # More workers
      # No spot instances for reliability
      spark_conf:
        # Production optimizations
        spark.databricks.delta.optimizeWrite.enabled: "true"
        spark.databricks.adaptive.localShuffleReader.enabled: "true"
```

## Custom Configurations

### Docker Images
```yaml
# When custom libraries detected
new_cluster:
  spark_version: "13.3.x-scala2.12"
  node_type_id: "i3.xlarge"
  num_workers: 4
  docker_image:
    url: "my-registry.com/custom-env:latest"
    basic_auth:
      username: ${secrets.docker_username}
      password: ${secrets.docker_password}
```

### Init Scripts
```yaml
# When custom setup required
new_cluster:
  spark_version: "13.3.x-scala2.12"
  node_type_id: "i3.xlarge"
  num_workers: 4
  init_scripts:
    - dbfs:
        destination: "dbfs:/init_scripts/setup_environment.sh"
```

### Custom Libraries
```yaml
# When specific versions needed
new_cluster:
  spark_version: "13.3.x-scala2.12"
  node_type_id: "i3.xlarge"
  num_workers: 4
  libraries:
    - pypi:
        package: "pandas==1.5.3"
    - pypi:
        package: "scikit-learn==1.2.2"
    - maven:
        coordinates: "org.apache.spark:spark-avro_2.12:3.4.0"
```

## Cost Optimization Guidelines

### Use Spot Instances (Non-Production)
```yaml
spot_bid_price_percent: 50  # 50% of on-demand price
```

### Auto-Termination
```yaml
autotermination_minutes: 30  # Terminate after 30 minutes idle
```

### Right-Sizing
- Start with smaller clusters and scale up based on actual performance
- Monitor cluster utilization and adjust accordingly
- Use adaptive query execution to optimize resource usage

### Reserved Instances
- For production workloads with predictable usage
- Can save 20-60% on compute costs
- Plan capacity based on historical usage patterns