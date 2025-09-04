# Notebook Content Export & Parsing Strategy
## Phase 2 MCP Server - Code Analysis Approach

### 📋 Current Implementation Analysis

#### Existing `export_notebook` Tool
The current implementation in `/mcp/server/tools.py` provides:

```python
export_notebook(path: str, format: str) -> str
```

**Supported Formats:**
- **SOURCE**: Raw source code (base64 decoded to UTF-8)
- **HTML**: HTML representation
- **JUPYTER**: Jupyter notebook format (.ipynb)
- **DBC**: Databricks archive format

**Current Behavior:**
1. Exports notebook from workspace using Databricks SDK
2. Base64 decodes SOURCE format content
3. Returns raw content as string in response

### 📊 Content Format Analysis

#### 1. Databricks Notebook Formats

##### SOURCE Format (Primary for Analysis)
When exported as SOURCE, Databricks notebooks contain:
```python
# Databricks notebook source
# MAGIC %md
# MAGIC # Title Here

# COMMAND ----------

# Python code cell
import pandas as pd
df = spark.read.table("catalog.schema.table")

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT * FROM catalog.schema.table

# COMMAND ----------

# MAGIC %scala
# MAGIC val df = spark.table("catalog.schema.table")
```

**Key Markers:**
- `# Databricks notebook source` - Header identifier
- `# COMMAND ----------` - Cell separator
- `# MAGIC %<language>` - Magic commands for non-default languages
- `# MAGIC %md` - Markdown cells
- `# MAGIC %sql` - SQL cells in Python notebooks
- `# MAGIC %scala` - Scala cells in Python notebooks
- `# MAGIC %r` - R cells in Python notebooks

##### JUPYTER Format (.ipynb)
JSON structure with cells array:
```json
{
  "cells": [
    {
      "cell_type": "code",
      "source": ["import pandas as pd\n", "df = spark.read..."],
      "metadata": {"language": "python"},
      "execution_count": null,
      "outputs": []
    },
    {
      "cell_type": "markdown",
      "source": ["# Title\n", "Description..."],
      "metadata": {}
    }
  ],
  "metadata": {
    "language_info": {"name": "python"},
    "kernelspec": {"name": "python3"}
  }
}
```

#### 2. SQL File Formats

##### Pure SQL Files
```sql
-- Databricks SQL file
-- Can contain multiple statements
USE CATALOG main;
USE SCHEMA default;

CREATE OR REPLACE TABLE sales AS
SELECT * FROM raw.sales
WHERE date > '2024-01-01';

-- Multiple CTEs and complex queries
WITH customer_metrics AS (
  SELECT customer_id, SUM(amount) as total
  FROM sales
  GROUP BY customer_id
)
SELECT * FROM customer_metrics;
```

##### SQL Notebooks
- Exported as SOURCE with `# MAGIC %sql` prefixes
- Or as pure SQL if notebook default language is SQL

#### 3. Other Language Formats

##### Scala Notebooks
```scala
// Databricks notebook source
import org.apache.spark.sql.SparkSession
val df = spark.read.table("catalog.schema.table")
df.show()
```

##### R Notebooks
```r
# Databricks notebook source
library(SparkR)
df <- sql("SELECT * FROM catalog.schema.table")
display(df)
```

### 🔍 Parsing Strategy for Phase 2

#### 1. Multi-Format Parser Architecture

```python
class NotebookParser:
    """Base parser for different notebook formats"""
    
    def parse(self, content: str, format: str = "SOURCE") -> NotebookContent:
        """Parse notebook content based on format"""
        if format == "SOURCE":
            return self._parse_source_format(content)
        elif format == "JUPYTER":
            return self._parse_jupyter_format(content)
        # Add other formats as needed
    
    def _parse_source_format(self, content: str) -> NotebookContent:
        """Parse Databricks SOURCE format"""
        cells = self._split_cells(content)
        return NotebookContent(
            cells=[self._parse_cell(cell) for cell in cells],
            language=self._detect_primary_language(content)
        )
    
    def _split_cells(self, content: str) -> List[str]:
        """Split notebook into cells by COMMAND separator"""
        return content.split("# COMMAND ----------")
    
    def _parse_cell(self, cell_content: str) -> Cell:
        """Parse individual cell content"""
        if "# MAGIC %sql" in cell_content:
            return SQLCell(content=self._extract_sql(cell_content))
        elif "# MAGIC %md" in cell_content:
            return MarkdownCell(content=self._extract_markdown(cell_content))
        elif "# MAGIC %scala" in cell_content:
            return ScalaCell(content=self._extract_scala(cell_content))
        else:
            return PythonCell(content=cell_content.strip())
```

#### 2. Content Extraction Pipeline

```python
class ContentExtractor:
    """Extract meaningful information from parsed notebooks"""
    
    def extract_dependencies(self, notebook: NotebookContent) -> Dependencies:
        """Extract all dependencies from notebook"""
        deps = Dependencies()
        
        for cell in notebook.cells:
            if isinstance(cell, PythonCell):
                deps.python_imports.extend(self._extract_python_imports(cell))
            elif isinstance(cell, SQLCell):
                deps.sql_tables.extend(self._extract_sql_tables(cell))
            elif isinstance(cell, ScalaCell):
                deps.scala_imports.extend(self._extract_scala_imports(cell))
        
        return deps
    
    def extract_data_sources(self, notebook: NotebookContent) -> DataSources:
        """Extract input/output data sources"""
        sources = DataSources()
        
        for cell in notebook.cells:
            # Extract table references
            sources.input_tables.extend(self._find_read_tables(cell))
            sources.output_tables.extend(self._find_write_tables(cell))
            
            # Extract file paths
            sources.input_files.extend(self._find_read_files(cell))
            sources.output_files.extend(self._find_write_files(cell))
        
        return sources
    
    def detect_patterns(self, notebook: NotebookContent) -> WorkflowPattern:
        """Detect ETL/ML/Analytics patterns"""
        # Analyze cell progression and operations
        has_read = any(self._is_read_operation(cell) for cell in notebook.cells)
        has_transform = any(self._is_transform_operation(cell) for cell in notebook.cells)
        has_write = any(self._is_write_operation(cell) for cell in notebook.cells)
        has_ml = any(self._is_ml_operation(cell) for cell in notebook.cells)
        
        if has_ml:
            return WorkflowPattern.ML_TRAINING
        elif has_read and has_transform and has_write:
            return WorkflowPattern.ETL
        elif has_read and not has_write:
            return WorkflowPattern.ANALYTICS
        else:
            return WorkflowPattern.UNKNOWN
```

#### 3. Language-Specific Parsers

##### Python Parser (using AST)
```python
import ast

class PythonAnalyzer:
    """Analyze Python code using AST"""
    
    def analyze(self, code: str) -> PythonAnalysis:
        try:
            tree = ast.parse(code)
            return PythonAnalysis(
                imports=self._extract_imports(tree),
                functions=self._extract_functions(tree),
                classes=self._extract_classes(tree),
                spark_operations=self._extract_spark_ops(tree),
                dbutils_calls=self._extract_dbutils(tree)
            )
        except SyntaxError as e:
            # Handle syntax errors gracefully
            return PythonAnalysis(error=str(e))
    
    def _extract_imports(self, tree: ast.Module) -> List[str]:
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                imports.extend(f"{module}.{alias.name}" for alias in node.names)
        return imports
    
    def _extract_spark_ops(self, tree: ast.Module) -> List[SparkOperation]:
        ops = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if self._is_spark_read(node):
                    ops.append(SparkOperation(type="read", details=self._extract_call_details(node)))
                elif self._is_spark_write(node):
                    ops.append(SparkOperation(type="write", details=self._extract_call_details(node)))
        return ops
```

##### SQL Parser
```python
import sqlparse
from sqlparse.sql import IdentifierList, Identifier
from sqlparse.tokens import Keyword, DML

class SQLAnalyzer:
    """Analyze SQL queries"""
    
    def analyze(self, sql: str) -> SQLAnalysis:
        parsed = sqlparse.parse(sql)
        
        analysis = SQLAnalysis()
        for statement in parsed:
            analysis.tables.extend(self._extract_tables(statement))
            analysis.operations.append(self._identify_operation(statement))
            analysis.ctes.extend(self._extract_ctes(statement))
        
        return analysis
    
    def _extract_tables(self, statement) -> List[str]:
        """Extract table references from SQL"""
        tables = []
        from_seen = False
        
        for token in statement.flatten():
            if token.ttype is Keyword and token.value.upper() in ('FROM', 'JOIN'):
                from_seen = True
            elif from_seen and token.ttype is None:
                if self._is_table_name(token.value):
                    tables.append(token.value)
                    from_seen = False
        
        return tables
    
    def _identify_operation(self, statement) -> str:
        """Identify SQL operation type"""
        for token in statement.tokens:
            if token.ttype is DML:
                return token.value.upper()
        return "UNKNOWN"
```

### 🎯 Phase 2 Implementation Approach

#### Step 1: Export Enhancement
```python
@mcp.tool()
async def export_notebook_enhanced(
    path: str,
    format: str = "SOURCE",
    include_metadata: bool = True,
    parse_content: bool = False
) -> str:
    """Enhanced notebook export with optional parsing"""
    
    # Use existing export_notebook to get content
    raw_content = await export_notebook(path, format)
    
    result = {
        "path": path,
        "format": format,
        "content": raw_content
    }
    
    if include_metadata:
        # Add notebook metadata from workspace API
        result["metadata"] = await get_notebook_metadata(path)
    
    if parse_content:
        # Parse content based on format
        parser = NotebookParser()
        parsed = parser.parse(raw_content, format)
        result["parsed"] = parsed.to_dict()
    
    return create_success_response(result)
```

#### Step 2: Analysis Tool Integration
```python
@mcp.tool()
async def analyze_notebook(
    notebook_path: str,
    include_dependencies: bool = True,
    include_data_sources: bool = True,
    detect_patterns: bool = True
) -> str:
    """Analyze notebook content deeply"""
    
    # Export notebook in SOURCE format for analysis
    export_result = await export_notebook(notebook_path, "SOURCE")
    content = export_result["data"]["content"]
    
    # Parse notebook
    parser = NotebookParser()
    notebook = parser.parse(content)
    
    # Extract information
    extractor = ContentExtractor()
    
    analysis = {
        "notebook_info": {
            "path": notebook_path,
            "language": notebook.language,
            "cell_count": len(notebook.cells)
        }
    }
    
    if include_dependencies:
        analysis["dependencies"] = extractor.extract_dependencies(notebook)
    
    if include_data_sources:
        analysis["data_sources"] = extractor.extract_data_sources(notebook)
    
    if detect_patterns:
        analysis["patterns"] = extractor.detect_patterns(notebook)
    
    return create_success_response(analysis)
```

### 📈 Benefits of This Approach

1. **Format Flexibility**: Handle multiple export formats (SOURCE, JUPYTER, etc.)
2. **Language Support**: Parse Python, SQL, Scala, R in mixed notebooks
3. **Deep Analysis**: Extract imports, dependencies, data sources automatically
4. **Pattern Detection**: Identify ETL, ML, analytics workflows
5. **Incremental Enhancement**: Build on existing export_notebook tool
6. **Error Resilience**: Handle syntax errors and malformed content gracefully

### 🔧 Technical Considerations

#### Performance
- Cache parsed notebooks for repeated analysis
- Stream large notebook content
- Parallelize cell parsing for large notebooks

#### Accuracy
- Handle Databricks-specific constructs (widgets, dbutils)
- Parse magic commands correctly
- Extract both explicit and implicit dependencies

#### Extensibility
- Plugin architecture for new languages
- Custom pattern detectors
- Configurable extraction rules

### 📊 Example Analysis Output

For a typical ETL notebook:
```json
{
  "notebook_info": {
    "path": "/Users/alex/etl_pipeline",
    "language": "PYTHON",
    "cell_count": 8,
    "has_widgets": true,
    "mixed_languages": ["python", "sql"]
  },
  "dependencies": {
    "python_imports": ["pandas", "pyspark.sql", "delta"],
    "databricks_libs": ["databricks-sdk"],
    "sql_tables": ["main.raw.sales", "main.silver.sales_clean"]
  },
  "data_sources": {
    "input_tables": ["main.raw.sales", "main.raw.customers"],
    "output_tables": ["main.silver.sales_aggregated"],
    "file_reads": ["/mnt/configs/mapping.json"],
    "file_writes": ["/mnt/output/report.parquet"]
  },
  "patterns": {
    "type": "ETL",
    "stages": ["read", "validate", "transform", "aggregate", "write"],
    "complexity": "medium",
    "estimated_runtime": "15-30 minutes"
  },
  "parameters": {
    "widgets": ["start_date", "end_date", "environment"],
    "spark_configs": ["spark.sql.adaptive.enabled", "spark.sql.shuffle.partitions"]
  }
}
```

This comprehensive strategy ensures we can effectively analyze any Databricks notebook or SQL file to generate appropriate DAB configurations in Phase 2.