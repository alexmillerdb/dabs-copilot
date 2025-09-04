"""
Test suite for analyze_notebook tool
Tests various file types and Databricks-specific patterns
"""

import sys
import os
import json
import pytest
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../server')))

from server.services.analysis_service import NotebookAnalysisService


class TestAnalyzeNotebook:
    """Test suite for notebook analysis functionality"""
    
    @pytest.fixture
    def analysis_service(self):
        """Create analysis service instance"""
        return NotebookAnalysisService()
    
    def test_analyze_python_file_with_databricks_features(self, analysis_service):
        """Test analysis of Python file with Databricks-specific features"""
        # Given: Python code with Databricks features
        content = """
import pandas as pd
from pyspark.sql import SparkSession
from delta.tables import DeltaTable
import mlflow

# Databricks widgets
dbutils.widgets.text("date", "2024-01-01", "Processing Date")
dbutils.widgets.dropdown("environment", "dev", ["dev", "staging", "prod"])

# Spark operations
spark = SparkSession.builder.appName("ETL Pipeline").getOrCreate()
df = spark.read.table("main.raw.sales_data")

# Data transformation
transformed_df = df.filter(df.amount > 0) \
    .groupBy("category") \
    .agg({"amount": "sum"})

# Write to Unity Catalog
transformed_df.write \
    .mode("overwrite") \
    .saveAsTable("main.silver.sales_summary")

# MLflow tracking
mlflow.start_run()
mlflow.log_param("date", dbutils.widgets.get("date"))
mlflow.end_run()

# Call another notebook
dbutils.notebook.run("/Users/shared/utils/data_quality", 60, {"table": "sales_summary"})
"""
        
        # When: Analyzing the content
        result = analysis_service.analyze_file(
            file_path="test_etl.py",
            content=content,
            file_type="python",
            include_dependencies=True,
            include_data_sources=True,
            detect_patterns=True
        )
        
        # Then: Should extract all Databricks features correctly
        assert result["file_info"]["type"] == "python"
        
        # Check dependencies
        assert "pyspark" in result["dependencies"]["databricks"]
        assert "delta" in result["dependencies"]["databricks"]
        assert "mlflow" in result["dependencies"]["databricks"]
        assert "pandas" in result["dependencies"]["third_party"]
        
        # Check data sources
        assert "main.raw.sales_data" in result["data_sources"]["input_tables"]
        assert "main.silver.sales_summary" in result["data_sources"]["output_tables"]
        
        # Check Databricks features
        assert "widgets" in result["databricks_features"]
        assert "spark_session" in result["databricks_features"]
        assert "mlflow_tracking" in result["databricks_features"]
        assert "notebook_run" in result["databricks_features"]
        
        # Check widget parameters
        widget_params = result["databricks_features"].get("widget_params", [])
        assert len(widget_params) == 2
        assert any(w["name"] == "date" for w in widget_params)
        assert any(w["name"] == "environment" for w in widget_params)
        
        # Check notebook dependencies
        assert result["databricks_features"].get("calls_other_notebooks") == True
        assert "/Users/shared/utils/data_quality" in result["databricks_features"].get("notebook_dependencies", [])
        
        # Check pattern detection
        assert result["patterns"]["workflow_type"] == "ETL"
        assert "read" in result["patterns"]["stages"]
        assert "transform" in result["patterns"]["stages"]
        assert "write" in result["patterns"]["stages"]
        
        # Check recommendations
        assert result["recommendations"]["job_type"] == "scheduled_batch"
        assert result["recommendations"]["requires_unity_catalog"] == True
        assert len(result["recommendations"]["parameters"]) > 0
    
    def test_analyze_sql_file(self, analysis_service):
        """Test analysis of SQL file with Unity Catalog tables"""
        # Given: SQL code with UC tables
        content = """
-- Create silver table from bronze data
CREATE OR REPLACE TABLE main.silver.customer_metrics AS
SELECT 
    customer_id,
    COUNT(*) as transaction_count,
    SUM(amount) as total_spent,
    AVG(amount) as avg_transaction
FROM main.bronze.transactions t
JOIN main.bronze.customers c ON t.customer_id = c.id
WHERE transaction_date >= '2024-01-01'
GROUP BY customer_id;

-- Update gold layer
MERGE INTO main.gold.customer_summary target
USING main.silver.customer_metrics source
ON target.customer_id = source.customer_id
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *;
"""
        
        # When: Analyzing SQL content
        result = analysis_service.analyze_file(
            file_path="transform.sql",
            content=content,
            file_type="sql",
            include_dependencies=True,
            include_data_sources=True,
            detect_patterns=True
        )
        
        # Then: Should identify SQL operations and tables
        assert result["file_info"]["type"] == "sql"
        
        # Check data sources
        input_tables = result["data_sources"]["input_tables"]
        output_tables = result["data_sources"]["output_tables"]
        
        assert "main.bronze.transactions" in input_tables or "main.bronze.transactions" in str(input_tables)
        assert "main.bronze.customers" in input_tables or "main.bronze.customers" in str(input_tables)
        assert "main.silver.customer_metrics" in output_tables or "main.silver.customer_metrics" in str(output_tables)
        
        # Check Unity Catalog detection
        assert "unity_catalog" in result["databricks_features"]
        
        # Check pattern - should detect as ETL
        assert result["patterns"]["workflow_type"] == "ETL"
    
    def test_analyze_databricks_notebook_with_magic_commands(self, analysis_service):
        """Test analysis of Databricks notebook with magic commands"""
        # Given: Databricks notebook content
        content = """# Databricks notebook source
# MAGIC %md
# MAGIC # Data Processing Pipeline

# COMMAND ----------

# MAGIC %python
import pandas as pd
from pyspark.sql.functions import col, sum

# COMMAND ----------

# MAGIC %sql
CREATE WIDGET TEXT database DEFAULT "main"

# COMMAND ----------

# MAGIC %python
database = dbutils.widgets.get("database")
df = spark.table(f"{database}.raw.events")

# COMMAND ----------

# MAGIC %sql
SELECT COUNT(*) as event_count
FROM main.raw.events
WHERE event_date = current_date()

# COMMAND ----------

# MAGIC %python
# Process and save
processed_df = df.filter(col("status") == "active")
processed_df.write.mode("overwrite").saveAsTable(f"{database}.processed.events")
"""
        
        # When: Analyzing notebook content
        result = analysis_service.analyze_file(
            file_path="pipeline.py",
            content=content,
            file_type=None,  # Auto-detect
            include_dependencies=True,
            include_data_sources=True,
            detect_patterns=True
        )
        
        # Then: Should handle mixed languages correctly
        assert "notebook" in result["file_info"]["type"]
        
        # Check magic commands detection
        assert "magic_commands" in result["databricks_features"]
        
        # Check dependencies from Python cells
        assert "pandas" in str(result["dependencies"])
        assert "pyspark" in str(result["dependencies"])
        
        # Check widgets
        assert "widgets" in result["databricks_features"]
        
        # Check pattern detection
        assert result["patterns"]["workflow_type"] in ["ETL", "unknown"]
    
    def test_ml_pattern_detection(self, analysis_service):
        """Test ML workflow pattern detection"""
        # Given: ML training code
        content = """
import mlflow
import mlflow.sklearn
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
import pandas as pd

# Load data
df = spark.table("main.ml.training_data").toPandas()

# Prepare features
X = df.drop("target", axis=1)
y = df["target"]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

# Train model
with mlflow.start_run():
    model = RandomForestClassifier(n_estimators=100)
    model.fit(X_train, y_train)
    
    # Evaluate
    score = model.score(X_test, y_test)
    
    # Log metrics and model
    mlflow.log_param("n_estimators", 100)
    mlflow.log_metric("accuracy", score)
    mlflow.sklearn.log_model(model, "random_forest_model")
    
    # Register model
    mlflow.register_model("runs:/latest/random_forest_model", "customer_churn_model")
"""
        
        # When: Analyzing ML code
        result = analysis_service.analyze_file(
            file_path="ml_training.py",
            content=content,
            file_type="python",
            detect_patterns=True
        )
        
        # Then: Should detect ML pattern
        assert result["patterns"]["workflow_type"] == "ML"
        assert "training" in result["patterns"]["stages"]
        assert "evaluation" in result["patterns"]["stages"]
        
        # Check ML-specific recommendations
        assert result["recommendations"]["job_type"] == "ml_training"
        assert "ml" in result["recommendations"]["cluster_config"]["spark_version"]
    
    def test_reporting_pattern_detection(self, analysis_service):
        """Test reporting/visualization pattern detection"""
        # Given: Reporting code
        content = """
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

# Load data
df = spark.sql("SELECT * FROM main.analytics.daily_metrics").toPandas()

# Create visualizations
plt.figure(figsize=(12, 6))
sns.lineplot(data=df, x='date', y='revenue')
plt.title('Daily Revenue Trend')
display(plt.show())

# Generate summary statistics
summary = df.groupby('category').agg({'revenue': 'sum', 'orders': 'count'})
display(summary)
"""
        
        # When: Analyzing reporting code
        result = analysis_service.analyze_file(
            file_path="daily_report.py",
            content=content,
            detect_patterns=True
        )
        
        # Then: Should detect reporting pattern
        assert result["patterns"]["workflow_type"] == "reporting"
        assert "visualization" in result["patterns"]["stages"]
        
        # Check reporting recommendations
        assert result["recommendations"]["job_type"] == "scheduled_report"
        assert result["recommendations"]["schedule"] is not None
    
    def test_dependency_extraction_complex(self, analysis_service):
        """Test complex dependency extraction"""
        # Given: Code with various import styles
        content = """
# Standard library
import os
import sys
from datetime import datetime, timedelta
from collections import defaultdict

# Third party
import numpy as np
import pandas as pd
from scipy import stats

# Databricks/Spark
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import *
from delta.tables import DeltaTable
import databricks.feature_store as fs

# Local imports
from .utils import helper_function
from ..config import settings
"""
        
        # When: Extracting dependencies
        result = analysis_service.analyze_file(
            file_path="complex_deps.py",
            content=content,
            include_dependencies=True
        )
        
        # Then: Should categorize correctly
        deps = result["dependencies"]
        
        assert "os" in deps["standard_library"]
        assert "datetime" in deps["standard_library"]
        assert "numpy" in deps["third_party"]
        assert "pandas" in deps["third_party"]
        assert "pyspark" in deps["databricks"]
        assert "delta" in deps["databricks"]
        assert "databricks" in deps["databricks"]
        assert ".utils" in deps["local"] or "utils" in str(deps["local"])
    
    def test_cluster_configuration_recommendations(self, analysis_service):
        """Test cluster configuration recommendations based on workload"""
        # Given: Heavy processing code
        content = """
from pyspark.sql import functions as F

# Large scale aggregation
df = spark.read.parquet("/mnt/data/billions_of_rows")

# Heavy transformations
result = df.groupBy("key1", "key2", "key3") \
    .agg(
        F.sum("value").alias("total"),
        F.avg("value").alias("average"),
        F.stddev("value").alias("std_dev"),
        F.collect_list("details").alias("all_details")
    ) \
    .filter(F.col("total") > 1000000)
    
# Repartition for performance
result = result.repartition(200, "key1")

# Write with optimization
result.write \
    .partitionBy("key1") \
    .mode("overwrite") \
    .option("optimizeWrite", "true") \
    .saveAsTable("main.gold.aggregated_results")
"""
        
        # When: Analyzing for recommendations
        result = analysis_service.analyze_file(
            file_path="heavy_etl.py",
            content=content,
            detect_patterns=True
        )
        
        # Then: Should recommend appropriate cluster
        recommendations = result["recommendations"]
        assert recommendations["job_type"] == "scheduled_batch"
        assert "cluster_config" in recommendations
        assert recommendations["cluster_config"]["num_workers"] >= 2  # Should suggest multiple workers
    
    def test_error_handling_invalid_python(self, analysis_service):
        """Test handling of invalid Python syntax"""
        # Given: Invalid Python code
        content = """
def broken_function(
    # Missing closing parenthesis
    print("This won't parse"
    
import pandas as pd
"""
        
        # When: Analyzing invalid code
        result = analysis_service.analyze_file(
            file_path="invalid.py",
            content=content,
            file_type="python",
            include_dependencies=True
        )
        
        # Then: Should still extract what it can using regex
        # Should fall back to regex extraction
        assert "pandas" in str(result["dependencies"])
    
    def test_unity_catalog_three_part_names(self, analysis_service):
        """Test detection of Unity Catalog three-part naming"""
        # Given: Code with various UC table references
        content = """
# Different ways to reference UC tables
df1 = spark.table("main.bronze.raw_events")
df2 = spark.sql("SELECT * FROM hive_metastore.default.legacy_table")
df3 = spark.read.table("custom_catalog.analytics.fact_sales")

# Write operations
df1.write.saveAsTable("main.silver.processed_events")
spark.sql("INSERT INTO main.gold.summary SELECT * FROM main.silver.processed_events")
"""
        
        # When: Extracting data sources
        result = analysis_service.analyze_file(
            file_path="uc_tables.py",
            content=content,
            include_data_sources=True
        )
        
        # Then: Should identify all UC tables
        sources = result["data_sources"]
        all_tables = sources.get("input_tables", []) + sources.get("output_tables", [])
        
        assert any("main.bronze.raw_events" in str(table) for table in all_tables)
        assert any("hive_metastore.default.legacy_table" in str(table) for table in all_tables)
        assert any("custom_catalog.analytics.fact_sales" in str(table) for table in all_tables)
        
        # Should mark as requiring Unity Catalog
        assert result["recommendations"].get("requires_unity_catalog") == True
    
    def test_notebook_run_dependencies(self, analysis_service):
        """Test extraction of notebook-to-notebook dependencies"""
        # Given: Code with multiple notebook calls
        content = """
# Setup notebooks
dbutils.notebook.run("/Shared/setup/init_environment", 0)
dbutils.notebook.run("./utils/helper_functions", 60, {"mode": "prod"})

# Main processing
result = dbutils.notebook.run("/Users/data_team/etl/extract_data", 
                             timeout_seconds=3600,
                             arguments={"date": "2024-01-01"})

# Conditional execution
if result == "success":
    dbutils.notebook.run("../reporting/generate_report", 1800)
"""
        
        # When: Extracting notebook dependencies
        result = analysis_service.analyze_file(
            file_path="orchestrator.py",
            content=content,
            include_dependencies=True
        )
        
        # Then: Should find all notebook references
        features = result["databricks_features"]
        assert features.get("calls_other_notebooks") == True
        
        notebook_deps = features.get("notebook_dependencies", [])
        assert len(notebook_deps) >= 4
        assert "/Shared/setup/init_environment" in notebook_deps
        assert "./utils/helper_functions" in notebook_deps
        assert "/Users/data_team/etl/extract_data" in notebook_deps


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])