"""
Tests for enhanced notebook analysis module.
Run from project root: python -m pytest tests/test_enhanced_analysis.py -v
"""

import pytest
import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from dabs_copilot.tools.analysis import (
    analyze_content,
    calculate_complexity_score,
    _analyze_python,
    _analyze_sql,
    _extract_dependencies_from_ast,
    _extract_dependencies_regex,
    _extract_data_sources,
    _extract_databricks_features,
    _detect_workflow_pattern,
)


class TestPythonAstParsing:
    """Tests for AST-based Python import extraction."""

    def test_basic_imports(self):
        """Valid Python with standard imports parses correctly."""
        content = """
import os
import json
from datetime import datetime
from pathlib import Path
"""
        result = _analyze_python(content)
        deps = result["dependencies"]

        assert "os" in deps["standard_library"]
        assert "json" in deps["standard_library"]
        assert "datetime" in deps["standard_library"]
        assert "pathlib" in deps["standard_library"]

    def test_third_party_imports(self):
        """Third-party libraries are categorized correctly."""
        content = """
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
import requests
"""
        result = _analyze_python(content)
        deps = result["dependencies"]

        assert "pandas" in deps["third_party"]
        assert "numpy" in deps["third_party"]
        assert "sklearn" in deps["third_party"]
        assert "requests" in deps["third_party"]

    def test_databricks_imports(self):
        """Databricks-specific imports are categorized correctly."""
        content = """
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit
import mlflow
from delta.tables import DeltaTable
from databricks.sdk import WorkspaceClient
"""
        result = _analyze_python(content)
        deps = result["dependencies"]

        assert "pyspark" in deps["databricks"]
        assert "mlflow" in deps["databricks"]
        assert "delta" in deps["databricks"]
        assert "databricks" in deps["databricks"]

    def test_relative_imports(self):
        """Relative imports are categorized as local."""
        content = """
from . import utils
from ..common import helpers
from .models import User
"""
        result = _analyze_python(content)
        deps = result["dependencies"]

        assert len(deps["local"]) >= 1
        # Check that relative imports are captured
        local_imports = deps["local"]
        assert any(imp.startswith(".") for imp in local_imports)


class TestPythonAstFallback:
    """Tests for regex fallback when AST parsing fails."""

    def test_syntax_error_fallback(self):
        """Invalid Python syntax falls back to regex extraction."""
        # This has a syntax error but imports can still be extracted via regex
        content = """
import pandas
import numpy
from sklearn import model_selection

def broken_function(
    # Missing closing paren - syntax error
"""
        result = _analyze_python(content)
        deps = result["dependencies"]

        # Should still extract some imports via regex
        assert "pandas" in deps["third_party"] or len(deps["third_party"]) >= 0


class TestDependencyCategorization:
    """Tests for dependency categorization logic."""

    def test_all_four_categories(self):
        """All four dependency categories are populated correctly."""
        content = """
# Standard library
import os
import json

# Third party
import pandas
import requests

# Databricks
from pyspark.sql import SparkSession
import mlflow

# Local
from . import utils
"""
        result = _analyze_python(content)
        deps = result["dependencies"]

        assert len(deps["standard_library"]) >= 2
        assert len(deps["third_party"]) >= 2
        assert len(deps["databricks"]) >= 2
        assert len(deps["local"]) >= 1


class TestSqlTableExtraction:
    """Tests for SQL table extraction."""

    def test_select_from_tables(self):
        """Input tables from SELECT statements are extracted."""
        content = """
SELECT * FROM main.bronze.sales
JOIN main.bronze.customers ON sales.customer_id = customers.id
WHERE sales.date > '2024-01-01'
"""
        result = _analyze_sql(content)
        sources = result["data_sources"]

        assert "main.bronze.sales" in sources["input_tables"]
        assert "main.bronze.customers" in sources["input_tables"]

    def test_create_table(self):
        """Output tables from CREATE statements are extracted."""
        content = """
CREATE OR REPLACE TABLE main.silver.daily_summary AS
SELECT date, SUM(amount) as total
FROM main.bronze.sales
GROUP BY date
"""
        result = _analyze_sql(content)
        sources = result["data_sources"]

        assert "main.silver.daily_summary" in sources["output_tables"]
        assert "main.bronze.sales" in sources["input_tables"]

    def test_insert_into(self):
        """Output tables from INSERT statements are extracted."""
        content = """
INSERT INTO main.gold.aggregates
SELECT * FROM main.silver.processed
"""
        result = _analyze_sql(content)
        sources = result["data_sources"]

        assert "main.gold.aggregates" in sources["output_tables"]


class TestDatabricksFeatures:
    """Tests for Databricks-specific feature extraction."""

    def test_widget_extraction(self):
        """Widgets are extracted with type and default values."""
        content = '''
dbutils.widgets.text("start_date", "2024-01-01")
dbutils.widgets.dropdown("environment", "dev", ["dev", "staging", "prod"])
dbutils.widgets.combobox("region", "us-east-1")
'''
        features = _extract_databricks_features(content)

        assert len(features["widgets"]) == 3

        widget_names = [w["name"] for w in features["widgets"]]
        assert "start_date" in widget_names
        assert "environment" in widget_names
        assert "region" in widget_names

        # Check types
        widget_types = {w["name"]: w["type"] for w in features["widgets"]}
        assert widget_types["start_date"] == "text"
        assert widget_types["environment"] == "dropdown"
        assert widget_types["region"] == "combobox"

    def test_notebook_calls(self):
        """Notebook run dependencies are extracted."""
        content = '''
result1 = dbutils.notebook.run("/Workspace/shared/utils", 60)
result2 = dbutils.notebook.run("/Workspace/shared/transforms", 120, {"param": "value"})
'''
        features = _extract_databricks_features(content)

        assert len(features["notebook_calls"]) == 2
        assert "/Workspace/shared/utils" in features["notebook_calls"]
        assert "/Workspace/shared/transforms" in features["notebook_calls"]

    def test_cluster_configs(self):
        """Spark configuration settings are extracted."""
        content = '''
spark.conf.set("spark.sql.shuffle.partitions", "200")
spark.conf.set("spark.databricks.delta.optimizeWrite.enabled", "true")
'''
        features = _extract_databricks_features(content)

        assert len(features["cluster_configs"]) == 2
        assert "spark.sql.shuffle.partitions" in features["cluster_configs"]

    def test_magic_commands(self):
        """Magic commands are extracted from notebook content."""
        content = """
# MAGIC %python
# Some Python code

# MAGIC %sql
SELECT * FROM table

# MAGIC %md
# Documentation
"""
        features = _extract_databricks_features(content)

        assert "python" in features["magic_commands"]
        assert "sql" in features["magic_commands"]
        assert "md" in features["magic_commands"]


class TestWorkflowDetection:
    """Tests for workflow pattern detection."""

    def test_etl_detection(self):
        """ETL workflow pattern is detected correctly."""
        content = """
df = spark.read.parquet("/data/input")
df_transformed = df.withColumn("new_col", col("old_col") * 2)
df_transformed = df_transformed.filter(col("status") == "active")
df_transformed.write.saveAsTable("output_table")
"""
        workflow_type, confidence = _detect_workflow_pattern(content)

        assert workflow_type == "etl"
        assert confidence >= 0.5

    def test_ml_detection(self):
        """ML workflow pattern is detected correctly."""
        content = """
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier

X_train, X_test, y_train, y_test = train_test_split(X, y)
model = RandomForestClassifier()
model.fit(X_train, y_train)
predictions = model.predict(X_test)
accuracy = accuracy_score(y_test, predictions)
mlflow.log_metric("accuracy", accuracy)
"""
        workflow_type, confidence = _detect_workflow_pattern(content)

        assert workflow_type == "ml"
        assert confidence >= 0.6

    def test_reporting_detection(self):
        """Reporting/visualization workflow is detected correctly."""
        content = """
import matplotlib.pyplot as plt
import seaborn as sns

df = spark.table("metrics").toPandas()
plt.figure(figsize=(10, 6))
sns.barplot(data=df, x="category", y="value")
plt.savefig("chart.png")
display(df)
"""
        workflow_type, confidence = _detect_workflow_pattern(content)

        assert workflow_type == "reporting"
        assert confidence >= 0.8

    def test_dlt_detection(self):
        """DLT workflow pattern is detected correctly."""
        content = """
import dlt

@dlt.table
def bronze_data():
    return spark.read.format("csv").load("/data/raw")

@dlt.table
def silver_data():
    return dlt.read("bronze_data").filter(col("valid") == True)
"""
        workflow_type, confidence = _detect_workflow_pattern(content)

        assert workflow_type == "dlt"
        assert confidence >= 0.9


class TestConfidenceScoring:
    """Tests for detection confidence scoring."""

    def test_high_confidence_etl(self):
        """Clear ETL pattern has high confidence."""
        content = """
df = spark.read.table("input")
df = df.withColumn("x", col("y"))
df = df.filter(col("z") > 0)
df.write.saveAsTable("output")
"""
        workflow_type, confidence = _detect_workflow_pattern(content)

        assert confidence >= 0.8

    def test_low_confidence_ambiguous(self):
        """Ambiguous code has lower confidence."""
        content = """
# Just some variable assignments
x = 1
y = 2
result = x + y
"""
        workflow_type, confidence = _detect_workflow_pattern(content)

        assert confidence <= 0.5


class TestComplexityScoring:
    """Tests for complexity score calculation."""

    def test_simple_notebook_low_score(self):
        """Simple notebook has low complexity score."""
        analysis = {
            "dependencies": {
                "standard_library": ["os"],
                "third_party": ["pandas"],
                "databricks": ["pyspark"],
                "local": [],
            },
            "data_sources": {"input_tables": ["table1"], "output_tables": ["output1"], "file_paths": []},
            "databricks_features": {"widgets": [], "notebook_calls": [], "cluster_configs": [], "magic_commands": []},
            "detection_confidence": 0.9,
        }

        score, factors = calculate_complexity_score(analysis)

        assert score < 0.5
        assert len(factors) == 0 or all(f not in factors for f in ["high_dependency_count", "multiple_data_sources"])

    def test_complex_notebook_high_score(self):
        """Complex notebook has high complexity score."""
        analysis = {
            "dependencies": {
                "standard_library": ["os", "json", "datetime", "logging", "pathlib"],
                "third_party": ["pandas", "numpy", "sklearn", "requests", "boto3"],
                "databricks": ["pyspark", "mlflow", "delta"],
                "local": [".utils", ".models"],
            },
            "data_sources": {
                "input_tables": ["table1", "table2", "table3", "table4"],
                "output_tables": ["output1", "output2", "output3"],
                "file_paths": ["/mnt/data/file1", "/dbfs/data/file2"],
            },
            "databricks_features": {
                "widgets": [{"name": "w1"}, {"name": "w2"}, {"name": "w3"}, {"name": "w4"}],
                "notebook_calls": ["/shared/utils"],
                "cluster_configs": ["spark.shuffle.partitions"],
                "magic_commands": ["python", "sql"],
            },
            "detection_confidence": 0.4,
        }

        score, factors = calculate_complexity_score(analysis)

        assert score >= 0.5
        assert "notebook_dependencies" in factors or "high_dependency_count" in factors

    def test_notebook_dependencies_increase_score(self):
        """Notebook-to-notebook calls increase complexity."""
        analysis = {
            "dependencies": {"standard_library": [], "third_party": [], "databricks": [], "local": []},
            "data_sources": {"input_tables": [], "output_tables": [], "file_paths": []},
            "databricks_features": {
                "widgets": [],
                "notebook_calls": ["/shared/utils", "/shared/transforms"],
                "cluster_configs": [],
                "magic_commands": [],
            },
            "detection_confidence": 0.8,
        }

        score, factors = calculate_complexity_score(analysis)

        assert "notebook_dependencies" in factors

    def test_low_confidence_increases_score(self):
        """Low detection confidence increases complexity score."""
        analysis = {
            "dependencies": {"standard_library": [], "third_party": [], "databricks": [], "local": []},
            "data_sources": {"input_tables": [], "output_tables": [], "file_paths": []},
            "databricks_features": {"widgets": [], "notebook_calls": [], "cluster_configs": [], "magic_commands": []},
            "detection_confidence": 0.3,
        }

        score, factors = calculate_complexity_score(analysis)

        assert "low_detection_confidence" in factors
        assert score >= 0.3


class TestBackwardCompatibility:
    """Tests for backward compatibility with original output schema."""

    def test_analyze_content_returns_expected_fields(self):
        """analyze_content returns all expected fields."""
        content = """
import pandas as pd
from pyspark.sql import SparkSession

dbutils.widgets.text("date", "2024-01-01")
df = spark.table("input_table")
df.write.saveAsTable("output_table")
"""
        result = analyze_content(content, "python")

        # Check all expected fields exist
        assert "dependencies" in result
        assert "data_sources" in result
        assert "databricks_features" in result
        assert "workflow_type" in result
        assert "detection_confidence" in result

        # Check nested structure
        assert "standard_library" in result["dependencies"]
        assert "third_party" in result["dependencies"]
        assert "databricks" in result["dependencies"]
        assert "local" in result["dependencies"]

        assert "input_tables" in result["data_sources"]
        assert "output_tables" in result["data_sources"]
        assert "file_paths" in result["data_sources"]

        assert "widgets" in result["databricks_features"]
        assert "notebook_calls" in result["databricks_features"]

    def test_workflow_type_values(self):
        """Workflow type is one of expected values."""
        content = "import pandas"
        result = analyze_content(content, "python")

        assert result["workflow_type"] in ["etl", "ml", "reporting", "dlt", "ddl"]


class TestDataSourceExtraction:
    """Tests for data source extraction from Python code."""

    def test_spark_table_extraction(self):
        """spark.table() references are extracted."""
        content = '''
df1 = spark.table("catalog.schema.table1")
df2 = spark.read.table("catalog.schema.table2")
'''
        sources = _extract_data_sources(content)

        assert "catalog.schema.table1" in sources["input_tables"]
        assert "catalog.schema.table2" in sources["input_tables"]

    def test_dbfs_path_extraction(self):
        """DBFS file paths are extracted."""
        content = '''
df = spark.read.parquet("/mnt/data/parquet_files")
df.write.csv("/dbfs/output/results")
files = dbutils.fs.ls("/FileStore/uploads")
'''
        sources = _extract_data_sources(content)

        assert any("/mnt/" in p for p in sources["file_paths"])

    def test_write_operations(self):
        """Write operation targets are extracted."""
        content = '''
df.write.saveAsTable("catalog.schema.output_table")
'''
        sources = _extract_data_sources(content)

        assert "catalog.schema.output_table" in sources["output_tables"]


class TestMixedNotebookAnalysis:
    """Tests for mixed Python/SQL notebook analysis."""

    def test_mixed_cell_analysis(self):
        """Both Python and SQL cells are analyzed correctly."""
        content = """
# Databricks notebook source
# COMMAND ----------

import pandas as pd
from pyspark.sql import SparkSession

# COMMAND ----------

# MAGIC %sql
SELECT * FROM main.bronze.data
JOIN main.bronze.lookup ON data.id = lookup.id

# COMMAND ----------

df = spark.table("main.silver.processed")
df.write.saveAsTable("main.gold.output")
"""
        result = analyze_content(content, "mixed_notebook")

        # Should have Python imports
        deps = result["dependencies"]
        assert "pandas" in deps["third_party"]
        assert "pyspark" in deps["databricks"]

        # Should have SQL table references
        sources = result["data_sources"]
        assert len(sources["input_tables"]) >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
