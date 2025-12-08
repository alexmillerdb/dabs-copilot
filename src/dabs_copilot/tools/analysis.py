"""
Enhanced Notebook Analysis Module

Provides comprehensive deterministic analysis for Databricks notebooks, Python files,
and SQL files. Extracts dependencies, data sources, and patterns using AST parsing,
sqlparse, and regex patterns.

Used by sdk_tools.py analyze_notebook to provide enriched analysis results.
"""

import ast
import re
from typing import Any

try:
    import sqlparse

    HAS_SQLPARSE = True
except ImportError:
    HAS_SQLPARSE = False

# Databricks-specific regex patterns for feature detection
DATABRICKS_PATTERNS = {
    "widgets": r"dbutils\.widgets\.(text|dropdown|combobox|multiselect)\s*\([^)]+\)",
    "notebook_run": r'dbutils\.notebook\.run\s*\(["\']([^"\']+)',
    "spark_session": r"spark\.(sql|read|write|table|createDataFrame)",
    "delta_operations": r"(delta|DeltaTable)\.(create|load|merge|update|delete)",
    "mlflow_tracking": r"mlflow\.(start_run|log_param|log_metric|log_model)",
    "unity_catalog": r"(main|hive_metastore|[a-zA-Z_]+)\.[a-zA-Z_]+\.[a-zA-Z_]+",
    "dbfs_paths": r"/(?:mnt|dbfs|FileStore)/[a-zA-Z0-9_/\-\.]+",
    "cluster_config": r'spark\.conf\.(set|get)\s*\(["\']([^"\']+)',
    "magic_commands": r"^%\s*(python|sql|scala|r|sh|md)\s*$",
}

# ETL workflow patterns
ETL_PATTERNS = {
    "read": ["spark.read", "spark.sql", "spark.table", "pd.read_"],
    "transform": ["withColumn", "select", "filter", "groupBy", "agg", "join"],
    "write": ["write.", ".save(", "saveAsTable", "insertInto", "to_csv", "to_parquet"],
}

# ML workflow patterns (includes traditional ML and AI agents/LLM applications)
ML_PATTERNS = {
    "training": ["fit", "train", "MLlib", "sklearn", "tensorflow", "torch", "model.fit"],
    "evaluation": ["evaluate", "score", "predict", "accuracy_score", "f1_score"],
    "model_ops": ["register_model", "log_model", "save_model", "load_model"],
    # AI Agent / LLM Application patterns
    "llm_frameworks": [
        "langchain",
        "llama_index",
        "openai",
        "anthropic",
        "ChatCompletion",
        "LLMChain",
        "AgentExecutor",
        "langchain_core",
        "langchain_community",
        "transformers",
        "huggingface_hub",
    ],
    "agent_patterns": [
        "create_agent",
        "agent.invoke",
        "chain.invoke",
        "chain.run",
        "ChatModel",
        "PromptTemplate",
        "ChatPromptTemplate",
    ],
    "genai_databricks": [
        "databricks_langchain",
        "databricks_genai",
        "mlflow.deployments",
        "serving_endpoint",
        "foundation_model",
        "FoundationModelClient",
    ],
}

# Standard library modules for categorization
STANDARD_LIBRARY = {
    "os",
    "sys",
    "json",
    "datetime",
    "logging",
    "pathlib",
    "collections",
    "itertools",
    "re",
    "math",
    "random",
    "functools",
    "typing",
    "time",
    "io",
    "abc",
    "copy",
    "dataclasses",
    "enum",
    "hashlib",
    "uuid",
    "contextlib",
    "traceback",
    "warnings",
    "inspect",
    "ast",
    "textwrap",
    "string",
    "struct",
    "pickle",
    "csv",
    "tempfile",
    "shutil",
    "glob",
    "fnmatch",
    "urllib",
    "http",
    "html",
    "xml",
    "email",
    "base64",
    "subprocess",
    "threading",
    "multiprocessing",
    "queue",
    "asyncio",
    "concurrent",
    "socket",
    "ssl",
    "select",
    "signal",
    "unittest",
    "doctest",
    "pdb",
    "profile",
    "timeit",
    "argparse",
    "getopt",
    "configparser",
}

# Databricks-specific modules
DATABRICKS_MODULES = {"pyspark", "databricks", "dbutils", "delta", "mlflow", "dlt"}


def analyze_content(content: str, file_type: str) -> dict[str, Any]:
    """
    Main entry point for content analysis.

    Args:
        content: File content to analyze
        file_type: Type of file (python, sql, notebook, mixed_notebook)

    Returns:
        Analysis results with dependencies, data_sources, databricks_features,
        workflow_type, and detection_confidence
    """
    result = {
        "dependencies": {"standard_library": [], "third_party": [], "databricks": [], "local": []},
        "data_sources": {"input_tables": [], "output_tables": [], "file_paths": []},
        "databricks_features": {
            "widgets": [],
            "notebook_calls": [],
            "cluster_configs": [],
            "magic_commands": [],
        },
        "workflow_type": "etl",
        "detection_confidence": 0.5,
    }

    # Route to appropriate analyzer based on file type
    if file_type in ("python", "python_notebook"):
        analysis = _analyze_python(content)
    elif file_type in ("sql", "sql_notebook"):
        analysis = _analyze_sql(content)
    elif file_type == "mixed_notebook":
        analysis = _analyze_mixed_notebook(content)
    else:
        # Try to detect type from content
        if "import " in content or "from " in content or "def " in content:
            analysis = _analyze_python(content)
        elif "SELECT" in content.upper() or "CREATE TABLE" in content.upper():
            analysis = _analyze_sql(content)
        else:
            analysis = _analyze_python(content)  # Default to Python

    # Merge analysis results
    if "dependencies" in analysis:
        result["dependencies"] = analysis["dependencies"]
    if "data_sources" in analysis:
        result["data_sources"] = analysis["data_sources"]

    # Extract Databricks features
    result["databricks_features"] = _extract_databricks_features(content)

    # Detect workflow pattern and confidence
    workflow_type, confidence = _detect_workflow_pattern(content)
    result["workflow_type"] = workflow_type
    result["detection_confidence"] = confidence

    return result


def _analyze_python(content: str) -> dict[str, Any]:
    """
    Analyze Python code using AST parsing with regex fallback.

    Args:
        content: Python source code

    Returns:
        Dict with dependencies and data_sources
    """
    result = {
        "dependencies": {"standard_library": [], "third_party": [], "databricks": [], "local": []},
        "data_sources": {"input_tables": [], "output_tables": [], "file_paths": []},
    }

    try:
        # Parse AST for accurate import extraction
        tree = ast.parse(content)
        result["dependencies"] = _extract_dependencies_from_ast(tree)
    except SyntaxError:
        # Fall back to regex-based extraction
        result["dependencies"] = _extract_dependencies_regex(content)

    # Extract data sources using regex
    result["data_sources"] = _extract_data_sources(content)

    return result


def _analyze_sql(content: str) -> dict[str, Any]:
    """
    Analyze SQL code for table references.

    Args:
        content: SQL source code

    Returns:
        Dict with data_sources
    """
    result = {
        "dependencies": {"standard_library": [], "third_party": [], "databricks": [], "local": []},
        "data_sources": {"input_tables": [], "output_tables": [], "file_paths": []},
    }

    tables_input = set()
    tables_output = set()

    # Use sqlparse if available
    if HAS_SQLPARSE:
        try:
            parsed = sqlparse.parse(content)
            for statement in parsed:
                statement_type = statement.get_type()

                if statement_type in ["SELECT", "DELETE", "UPDATE"]:
                    tables_input.update(_extract_sql_tables(str(statement), "FROM"))
                    tables_input.update(_extract_sql_tables(str(statement), "JOIN"))

                if statement_type in ["INSERT", "CREATE", "MERGE"]:
                    tables_output.update(_extract_sql_tables(str(statement), "INTO|TABLE"))
        except Exception:
            pass  # Fall through to regex

    # Always use regex for comprehensive coverage
    from_pattern = (
        r"(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)"
    )
    for match in re.finditer(from_pattern, content, re.IGNORECASE | re.MULTILINE):
        table = match.group(1)
        if table.upper() not in ("SELECT", "WHERE", "AND", "OR", "AS"):
            tables_input.add(table)

    write_pattern = r"(?:CREATE\s+(?:OR\s+REPLACE\s+)?TABLE|INSERT\s+INTO|MERGE\s+INTO)\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)"
    for match in re.finditer(write_pattern, content, re.IGNORECASE | re.MULTILINE):
        tables_output.add(match.group(1))

    result["data_sources"]["input_tables"] = list(tables_input)
    result["data_sources"]["output_tables"] = list(tables_output)

    return result


def _analyze_mixed_notebook(content: str) -> dict[str, Any]:
    """
    Analyze notebooks with mixed languages (Python, SQL).

    Args:
        content: Notebook content

    Returns:
        Merged analysis from all cells
    """
    result = {
        "dependencies": {"standard_library": [], "third_party": [], "databricks": [], "local": []},
        "data_sources": {"input_tables": [], "output_tables": [], "file_paths": []},
    }

    cells = _split_notebook_cells(content)

    for cell in cells:
        language = cell.get("language", "python")

        if language == "python":
            cell_analysis = _analyze_python(cell["content"])
        elif language == "sql":
            cell_analysis = _analyze_sql(cell["content"])
        else:
            continue

        # Merge dependencies
        for key in result["dependencies"]:
            result["dependencies"][key].extend(cell_analysis.get("dependencies", {}).get(key, []))

        # Merge data sources
        for key in result["data_sources"]:
            values = cell_analysis.get("data_sources", {}).get(key, [])
            if isinstance(values, list):
                result["data_sources"][key].extend(values)

    # Deduplicate
    for key in result["dependencies"]:
        result["dependencies"][key] = list(set(result["dependencies"][key]))
    for key in result["data_sources"]:
        result["data_sources"][key] = list(set(result["data_sources"][key]))

    return result


def _extract_dependencies_from_ast(tree: ast.Module) -> dict[str, list[str]]:
    """
    Extract and categorize imports from AST.

    Args:
        tree: Parsed AST module

    Returns:
        Categorized dependencies
    """
    deps: dict[str, list[str]] = {
        "standard_library": [],
        "third_party": [],
        "databricks": [],
        "local": [],
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                _categorize_import(alias.name, deps)
        elif isinstance(node, ast.ImportFrom):
            if node.level > 0:
                # Relative import
                module_name = "." * node.level
                if node.module:
                    module_name += node.module
                deps["local"].append(module_name)
            elif node.module:
                _categorize_import(node.module, deps)

    # Remove duplicates
    for key in deps:
        deps[key] = list(set(deps[key]))

    return deps


def _extract_dependencies_regex(content: str) -> dict[str, list[str]]:
    """
    Extract dependencies using regex when AST parsing fails.

    Args:
        content: Source code

    Returns:
        Categorized dependencies
    """
    deps: dict[str, list[str]] = {
        "standard_library": [],
        "third_party": [],
        "databricks": [],
        "local": [],
    }

    # Match import statements
    import_pattern = r"^\s*(?:from\s+([^\s]+)\s+)?import\s+([^\s,]+)"
    for match in re.finditer(import_pattern, content, re.MULTILINE):
        module = match.group(1) or match.group(2).split(",")[0].strip()
        if module:
            _categorize_import(module, deps)

    return deps


def _categorize_import(module_name: str, deps: dict[str, list[str]]) -> None:
    """
    Categorize an import into the appropriate dependency category.

    Args:
        module_name: Module name to categorize
        deps: Dependencies dict to update
    """
    if module_name.startswith("."):
        deps["local"].append(module_name)
        return

    base_module = module_name.split(".")[0]

    if base_module in DATABRICKS_MODULES:
        deps["databricks"].append(base_module)
    elif base_module in STANDARD_LIBRARY:
        deps["standard_library"].append(base_module)
    else:
        deps["third_party"].append(base_module)


def _extract_data_sources(content: str) -> dict[str, list[str]]:
    """
    Extract table references and file paths from content.

    Args:
        content: Source code

    Returns:
        Data sources with input_tables, output_tables, file_paths
    """
    sources: dict[str, list[str]] = {
        "input_tables": [],
        "output_tables": [],
        "file_paths": [],
    }

    # spark.table() / spark.read.table()
    spark_table_pattern = r'spark\.(?:table|read\.table)\s*\(\s*["\']([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*){0,2})["\']'
    for match in re.finditer(spark_table_pattern, content):
        sources["input_tables"].append(match.group(1))

    # SQL FROM/JOIN clauses (but not Python import statements)
    # Look for FROM/JOIN that are not preceded by "import" on the same line
    for line in content.splitlines():
        # Skip import statements
        if line.strip().startswith(("from ", "import ")):
            continue
        sql_from_pattern = (
            r"(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*){0,2})"
        )
        for match in re.finditer(sql_from_pattern, line, re.IGNORECASE):
            table = match.group(1)
            if table.upper() not in ("SELECT", "WHERE", "AND", "OR", "AS", "ON"):
                sources["input_tables"].append(table)

    # Write operations
    write_pattern = r'(?:saveAsTable|INSERT\s+INTO|CREATE\s+(?:OR\s+REPLACE\s+)?TABLE)\s*\(?\s*["\']?([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*){0,2})'
    for match in re.finditer(write_pattern, content, re.IGNORECASE):
        sources["output_tables"].append(match.group(1))

    # DBFS paths
    dbfs_pattern = r'["\'](/(?:mnt|dbfs|FileStore)/[^"\']+)["\']'
    for match in re.finditer(dbfs_pattern, content):
        sources["file_paths"].append(match.group(1))

    # Deduplicate
    for key in sources:
        sources[key] = list(set(sources[key]))

    return sources


def _extract_databricks_features(content: str) -> dict[str, Any]:
    """
    Extract Databricks-specific features from content.

    Args:
        content: Source code

    Returns:
        Features dict with widgets, notebook_calls, cluster_configs, magic_commands
    """
    features: dict[str, Any] = {
        "widgets": [],
        "notebook_calls": [],
        "cluster_configs": [],
        "magic_commands": [],
    }

    # Extract widgets with parameters
    widget_pattern = r'dbutils\.widgets\.(text|dropdown|combobox|multiselect)\s*\(\s*["\']([^"\']+)["\'](?:\s*,\s*["\']([^"\']+)["\'])?'
    for match in re.finditer(widget_pattern, content):
        features["widgets"].append(
            {"name": match.group(2), "type": match.group(1), "default": match.group(3)}
        )

    # Extract notebook calls
    notebook_run_pattern = r'dbutils\.notebook\.run\s*\(["\']([^"\']+)'
    features["notebook_calls"] = re.findall(notebook_run_pattern, content)

    # Extract cluster configs
    config_pattern = r'spark\.conf\.set\s*\(["\']([^"\']+)["\']'
    features["cluster_configs"] = re.findall(config_pattern, content)

    # Extract magic commands
    magic_pattern = r"^#\s*MAGIC\s+%(\w+)"
    features["magic_commands"] = list(set(re.findall(magic_pattern, content, re.MULTILINE)))

    return features


def _detect_workflow_pattern(content: str) -> tuple[str, float]:
    """
    Detect the primary workflow pattern and confidence score.

    Args:
        content: Source code

    Returns:
        Tuple of (workflow_type, confidence)
    """
    content_lower = content.lower()

    # Check for DLT first
    if "@dlt." in content or "import dlt" in content or "dlt.read" in content_lower:
        return ("dlt", 0.95)

    # Check for visualization/reporting patterns (high priority)
    viz_keywords = [
        "matplotlib",
        "plotly",
        "seaborn",
        "display(",
        ".plot(",
        "plt.",
        "sns.",
        "fig",
        "bokeh",
        "altair",
    ]
    if any(viz in content_lower for viz in viz_keywords):
        return ("reporting", 0.9)

    # Check for ML patterns
    ml_score = 0
    has_model_training = False
    for stage, keywords in ML_PATTERNS.items():
        for keyword in keywords:
            if keyword.lower() in content_lower:
                ml_score += 1
                if stage in ("training", "llm_frameworks", "agent_patterns", "genai_databricks"):
                    has_model_training = True
                break

    # Check for ETL patterns
    etl_score = 0
    for stage, keywords in ETL_PATTERNS.items():
        if any(keyword.lower() in content_lower for keyword in keywords):
            etl_score += 1

    # Determine primary pattern
    if has_model_training and ml_score >= 2:
        confidence = min(ml_score / 3.0, 1.0)
        return ("ml", confidence)
    elif etl_score >= 2:
        confidence = min(etl_score / 3.0, 1.0)
        return ("etl", confidence)
    elif "CREATE TABLE" in content.upper() or "CREATE VIEW" in content.upper():
        return ("ddl", 0.8)
    elif etl_score >= 1:
        return ("etl", 0.5)

    # Default
    return ("etl", 0.3)


def _split_notebook_cells(content: str) -> list[dict[str, Any]]:
    """
    Split Databricks notebook content into cells.

    Args:
        content: Notebook content

    Returns:
        List of cell dicts with content and language
    """
    cells = []
    current_cell: list[str] = []
    current_language = "python"

    for line in content.splitlines():
        # Check for cell separator
        if "# COMMAND ----------" in line or "-- COMMAND ----------" in line:
            if current_cell:
                cells.append({"content": "\n".join(current_cell), "language": current_language})
                current_cell = []
        # Check for magic commands
        elif line.strip().startswith("# MAGIC %"):
            match = re.match(r"# MAGIC %(\w+)", line)
            if match:
                current_language = match.group(1)
            # Strip magic prefix
            current_cell.append(line.replace("# MAGIC ", ""))
        else:
            current_cell.append(line)

    # Add last cell
    if current_cell:
        cells.append({"content": "\n".join(current_cell), "language": current_language})

    return cells


def _extract_sql_tables(statement: str, keywords: str) -> list[str]:
    """
    Extract table names from SQL statement.

    Args:
        statement: SQL statement
        keywords: Keywords to match (e.g., "FROM", "JOIN")

    Returns:
        List of table names
    """
    tables = []
    pattern = rf"(?:{keywords})\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:TABLE\s+)?([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)"

    for match in re.finditer(pattern, statement, re.IGNORECASE):
        table_name = match.group(1)
        if table_name.upper() not in (
            "TABLE",
            "INTO",
            "FROM",
            "JOIN",
            "WHERE",
            "AS",
            "SELECT",
        ):
            tables.append(table_name)

    return tables


def calculate_complexity_score(analysis: dict[str, Any]) -> tuple[float, list[str]]:
    """
    Calculate complexity score for hybrid analysis decision.

    A score >= 0.5 indicates the notebook would benefit from semantic LLM analysis.

    Args:
        analysis: Analysis result from analyze_content

    Returns:
        Tuple of (score 0-1, list of complexity factors)
    """
    score = 0.0
    factors: list[str] = []

    dependencies = analysis.get("dependencies", {})
    data_sources = analysis.get("data_sources", {})
    features = analysis.get("databricks_features", {})
    confidence = analysis.get("detection_confidence", 1.0)

    # Multiple dependency categories used
    dep_categories_used = sum(1 for v in dependencies.values() if v)
    if dep_categories_used >= 3:
        score += 0.2
        factors.append("multiple_dependency_types")

    # High total dependency count
    total_deps = sum(len(v) for v in dependencies.values())
    if total_deps > 10:
        score += 0.2
        factors.append("high_dependency_count")

    # Multiple data sources
    input_tables = len(data_sources.get("input_tables", []))
    output_tables = len(data_sources.get("output_tables", []))
    if input_tables > 3 or output_tables > 2:
        score += 0.2
        factors.append("multiple_data_sources")

    # Calls other notebooks
    if features.get("notebook_calls"):
        score += 0.2
        factors.append("notebook_dependencies")

    # Low confidence in workflow detection
    if confidence < 0.7:
        score += 0.3
        factors.append("low_detection_confidence")

    # Multiple widgets (complex parameterization)
    if len(features.get("widgets", [])) > 3:
        score += 0.1
        factors.append("complex_parameterization")

    # Mixed language notebook
    if features.get("magic_commands"):
        score += 0.1
        factors.append("mixed_languages")

    return (min(score, 1.0), factors)
