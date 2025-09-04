"""
Databricks Notebook Analysis Service
Handles parsing and analysis of notebooks, Python files, and SQL files
to extract Databricks-specific patterns and generate DAB configurations.
"""

import ast
import json
import re
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import sqlparse
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class NotebookAnalysisService:
    """Service for analyzing Databricks notebooks and code files"""
    
    DATABRICKS_PATTERNS = {
        'widgets': r'dbutils\.widgets\.(text|dropdown|combobox|multiselect)\s*\([^)]+\)',
        'notebook_run': r'dbutils\.notebook\.run\s*\(["\']([^"\']+)',
        'spark_session': r'spark\.(sql|read|write|table|createDataFrame)',
        'delta_operations': r'(delta|DeltaTable)\.(create|load|merge|update|delete)',
        'mlflow_tracking': r'mlflow\.(start_run|log_param|log_metric|log_model)',
        'unity_catalog': r'(main|hive_metastore|[a-zA-Z_]+)\.[a-zA-Z_]+\.[a-zA-Z_]+',
        'dbfs_paths': r'/(?:mnt|dbfs|FileStore)/[a-zA-Z0-9_/\-\.]+',
        'cluster_config': r'spark\.conf\.(set|get)\s*\(["\']([^"\']+)',
        'magic_commands': r'^%\s*(python|sql|scala|r|sh|md)\s*$'
    }
    
    ETL_PATTERNS = {
        'read': ['spark.read', 'spark.sql', 'spark.table', 'pd.read_'],
        'transform': ['withColumn', 'select', 'filter', 'groupBy', 'agg', 'join'],
        'write': ['write.', '.save(', 'saveAsTable', 'insertInto', 'to_csv', 'to_parquet']
    }
    
    ML_PATTERNS = {
        'training': ['fit', 'train', 'MLlib', 'sklearn', 'tensorflow', 'torch', 'model.fit'],
        'evaluation': ['evaluate', 'score', 'predict', 'accuracy_score', 'f1_score'],
        'model_ops': ['register_model', 'log_model', 'save_model', 'load_model']
    }

    def __init__(self):
        self.analysis_cache = {}
    
    def analyze_file(self, 
                     file_path: str, 
                     content: str,
                     file_type: Optional[str] = None,
                     include_dependencies: bool = True,
                     include_data_sources: bool = True,
                     detect_patterns: bool = True) -> Dict[str, Any]:
        """
        Analyze a file (notebook, .py, .sql) for Databricks patterns
        
        Args:
            file_path: Path to the file
            content: File content
            file_type: Type of file (python, sql, notebook)
            include_dependencies: Extract imports and dependencies
            include_data_sources: Extract table and file references
            detect_patterns: Identify ETL/ML patterns
            
        Returns:
            Analysis results with Databricks-specific insights
        """
        try:
            # Detect file type if not provided
            if not file_type:
                file_type = self._detect_file_type(file_path, content)
            
            # Initialize result structure
            result = {
                "file_info": {
                    "path": file_path,
                    "type": file_type,
                    "size_bytes": len(content),
                    "last_analyzed": datetime.now().isoformat()
                },
                "databricks_features": {},
                "dependencies": {},
                "data_sources": {},
                "patterns": {},
                "parameters": {},
                "recommendations": {}
            }
            
            # Route to appropriate analyzer
            if file_type == 'python' or file_type == 'python_notebook':
                analysis = self._analyze_python(content, include_dependencies, include_data_sources)
            elif file_type == 'sql' or file_type == 'sql_notebook':
                analysis = self._analyze_sql(content, include_data_sources)
            elif file_type == 'mixed_notebook':
                analysis = self._analyze_mixed_notebook(content, include_dependencies, include_data_sources)
            else:
                analysis = self._analyze_generic(content)
            
            # Merge analysis results
            result.update(analysis)
            
            # Detect patterns if requested
            if detect_patterns:
                result["patterns"] = self._detect_workflow_patterns(content, file_type)
            
            # Extract Databricks-specific features
            result["databricks_features"] = self._extract_databricks_features(content)
            
            # Generate recommendations
            result["recommendations"] = self._generate_recommendations(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {e}")
            raise
    
    def _detect_file_type(self, file_path: str, content: str) -> str:
        """Detect the type of file based on extension and content"""
        path = Path(file_path)
        extension = path.suffix.lower()
        
        # Check for Databricks notebook markers
        if '# Databricks notebook source' in content or '# MAGIC' in content:
            # Check dominant language in notebook
            if '# COMMAND' in content or '# MAGIC %python' in content:
                return 'python_notebook'
            elif '# MAGIC %sql' in content or '-- COMMAND' in content:
                return 'sql_notebook'
            else:
                return 'mixed_notebook'
        
        # Regular files
        if extension == '.py':
            return 'python'
        elif extension == '.sql':
            return 'sql'
        elif extension in ['.ipynb']:
            return 'jupyter_notebook'
        
        # Check content for clues
        if 'import ' in content or 'from ' in content or 'def ' in content:
            return 'python'
        elif 'SELECT' in content.upper() or 'CREATE TABLE' in content.upper():
            return 'sql'
        
        return 'unknown'
    
    def _analyze_python(self, content: str, include_deps: bool, include_data: bool) -> Dict:
        """Analyze Python code for imports, functions, and Databricks patterns"""
        result = {
            "dependencies": {},
            "data_sources": {},
            "functions": [],
            "classes": []
        }
        
        try:
            # Parse AST
            tree = ast.parse(content)
            
            if include_deps:
                result["dependencies"] = self._extract_python_dependencies(tree)
            
            # Extract function and class definitions
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    result["functions"].append({
                        "name": node.name,
                        "args": [arg.arg for arg in node.args.args],
                        "lineno": node.lineno
                    })
                elif isinstance(node, ast.ClassDef):
                    result["classes"].append({
                        "name": node.name,
                        "lineno": node.lineno
                    })
            
        except SyntaxError as e:
            logger.warning(f"Python syntax error: {e}")
            # Fall back to regex-based extraction
            result["dependencies"] = self._extract_dependencies_regex(content)
        
        if include_data:
            result["data_sources"] = self._extract_data_sources(content)
        
        return result
    
    def _analyze_sql(self, content: str, include_data: bool) -> Dict:
        """Analyze SQL code for tables, views, and operations"""
        result = {
            "data_sources": {},
            "sql_operations": []
        }
        
        if include_data:
            # Parse SQL to extract tables
            tables_input = set()
            tables_output = set()
            
            # Use both sqlparse and regex for comprehensive extraction
            # First try sqlparse
            parsed = sqlparse.parse(content)
            for statement in parsed:
                statement_type = statement.get_type()
                
                if statement_type in ['SELECT', 'DELETE', 'UPDATE']:
                    # Extract source tables
                    tables_input.update(self._extract_sql_tables(str(statement), 'FROM'))
                    tables_input.update(self._extract_sql_tables(str(statement), 'JOIN'))
                    
                if statement_type in ['INSERT', 'CREATE', 'MERGE']:
                    # Extract target tables
                    tables_output.update(self._extract_sql_tables(str(statement), 'INTO|TABLE'))
                
                result["sql_operations"].append({
                    "type": statement_type,
                    "statement": str(statement)[:200]  # First 200 chars
                })
            
            # Also use direct regex for better coverage
            # Find all table references in FROM and JOIN clauses
            from_pattern = r'(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)'
            for match in re.finditer(from_pattern, content, re.IGNORECASE | re.MULTILINE):
                tables_input.add(match.group(1))
            
            # Find all table references in CREATE/INSERT/MERGE
            write_pattern = r'(?:CREATE\s+(?:OR\s+REPLACE\s+)?TABLE|INSERT\s+INTO|MERGE\s+INTO)\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)'
            for match in re.finditer(write_pattern, content, re.IGNORECASE | re.MULTILINE):
                tables_output.add(match.group(1))
            
            result["data_sources"] = {
                "input_tables": list(tables_input),
                "output_tables": list(tables_output)
            }
        
        return result
    
    def _analyze_mixed_notebook(self, content: str, include_deps: bool, include_data: bool) -> Dict:
        """Analyze notebooks with mixed languages (Python, SQL, Scala)"""
        result = {
            "cells": [],
            "languages_used": set(),
            "dependencies": {},
            "data_sources": {}
        }
        
        # Split by cell markers
        cells = self._split_notebook_cells(content)
        
        for cell in cells:
            language = cell.get('language', 'python')
            result["languages_used"].add(language)
            
            if language == 'python':
                cell_analysis = self._analyze_python(cell['content'], include_deps, include_data)
            elif language == 'sql':
                cell_analysis = self._analyze_sql(cell['content'], include_data)
            else:
                cell_analysis = {}
            
            result["cells"].append({
                "language": language,
                "line_start": cell.get('line_start', 0),
                "analysis": cell_analysis
            })
            
            # Merge dependencies and data sources
            if include_deps and 'dependencies' in cell_analysis:
                for key, values in cell_analysis['dependencies'].items():
                    if key not in result['dependencies']:
                        result['dependencies'][key] = []
                    result['dependencies'][key].extend(values)
            
            if include_data and 'data_sources' in cell_analysis:
                for key, values in cell_analysis['data_sources'].items():
                    if key not in result['data_sources']:
                        result['data_sources'][key] = []
                    if isinstance(values, list):
                        result['data_sources'][key].extend(values)
        
        result["languages_used"] = list(result["languages_used"])
        return result
    
    def _analyze_generic(self, content: str) -> Dict:
        """Generic analysis for unknown file types"""
        return {
            "lines": len(content.splitlines()),
            "characters": len(content)
        }
    
    def _extract_python_dependencies(self, tree: ast.Module) -> Dict[str, List[str]]:
        """Extract Python imports from AST"""
        deps = {
            "standard_library": [],
            "third_party": [],
            "databricks": [],
            "local": []
        }
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self._categorize_import(alias.name, deps)
            elif isinstance(node, ast.ImportFrom):
                # Handle relative imports
                if node.level > 0:
                    # This is a relative import
                    module_name = '.' * node.level
                    if node.module:
                        module_name += node.module
                    deps["local"].append(module_name)
                elif node.module:
                    self._categorize_import(node.module, deps)
        
        # Remove duplicates
        for key in deps:
            deps[key] = list(set(deps[key]))
        
        return deps
    
    def _categorize_import(self, module_name: str, deps: Dict):
        """Categorize an import as standard, third-party, databricks, or local"""
        databricks_modules = ['pyspark', 'databricks', 'dbutils', 'delta', 'mlflow']
        standard_modules = ['os', 'sys', 'json', 'datetime', 'logging', 'pathlib', 
                          'collections', 'itertools', 're', 'math', 'random']
        
        # Handle relative imports first
        if module_name.startswith('.'):
            deps["local"].append(module_name)
            return
        
        base_module = module_name.split('.')[0]
        
        if base_module in databricks_modules:
            # Add both the full import and base module for databricks
            deps["databricks"].append(module_name)
            if base_module not in deps["databricks"]:
                deps["databricks"].append(base_module)
        elif base_module in standard_modules:
            deps["standard_library"].append(module_name)
        else:
            deps["third_party"].append(module_name)
    
    def _extract_dependencies_regex(self, content: str) -> Dict[str, List[str]]:
        """Extract dependencies using regex when AST parsing fails"""
        deps = {
            "standard_library": [],
            "third_party": [],
            "databricks": [],
            "local": []
        }
        
        # Find import statements
        import_pattern = r'^\s*(?:from\s+([^\s]+)\s+)?import\s+([^\s,]+(?:\s*,\s*[^\s,]+)*)'
        for match in re.finditer(import_pattern, content, re.MULTILINE):
            module = match.group(1) or match.group(2).split(',')[0].strip()
            self._categorize_import(module, deps)
        
        return deps
    
    def _extract_data_sources(self, content: str) -> Dict[str, List[str]]:
        """Extract table references and file paths"""
        sources = {
            "input_tables": [],
            "output_tables": [],
            "file_paths": [],
            "delta_tables": []
        }
        
        # Unity Catalog tables (catalog.schema.table) - improved patterns
        # Pattern for spark.table(), spark.read.table(), etc.
        spark_table_pattern = r'spark\.(?:table|read\.table)\s*\(\s*["\']([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*){1,2})["\']'
        for match in re.finditer(spark_table_pattern, content):
            sources["input_tables"].append(match.group(1))
        
        # Pattern for SQL queries
        sql_from_pattern = r'(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*){1,2})'
        for match in re.finditer(sql_from_pattern, content, re.IGNORECASE):
            sources["input_tables"].append(match.group(1))
        
        # Pattern for write operations
        write_pattern = r'(?:saveAsTable|INSERT INTO|CREATE OR REPLACE TABLE|CREATE TABLE)\s*\(?\s*["\']?([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*){1,2})'
        for match in re.finditer(write_pattern, content, re.IGNORECASE):
            sources["output_tables"].append(match.group(1))
        
        # DBFS paths
        dbfs_pattern = r'["\'](/(?:mnt|dbfs|FileStore)/[^"\']+)["\']'
        for match in re.finditer(dbfs_pattern, content):
            sources["file_paths"].append(match.group(1))
        
        # Delta table operations
        delta_pattern = r'delta\.tables\.DeltaTable\.(?:forPath|forName)\s*\([^)]+\)'
        sources["delta_tables"] = re.findall(delta_pattern, content)
        
        # Remove duplicates
        for key in sources:
            sources[key] = list(set(sources[key]))
        
        return sources
    
    def _extract_databricks_features(self, content: str) -> Dict[str, Any]:
        """Extract Databricks-specific features and patterns"""
        features = {}
        
        for feature_name, pattern in self.DATABRICKS_PATTERNS.items():
            matches = re.findall(pattern, content, re.MULTILINE | re.IGNORECASE)
            if matches:
                features[feature_name] = matches[:10]  # Limit to first 10 matches
        
        # Extract widget parameters specifically
        if 'widgets' in features:
            features['widget_params'] = self._parse_widget_params(content)
        
        # Check for notebook-specific features
        if 'dbutils.notebook.run' in content:
            features['calls_other_notebooks'] = True
            features['notebook_dependencies'] = re.findall(
                r'dbutils\.notebook\.run\s*\(["\']([^"\']+)', content
            )
        
        return features
    
    def _parse_widget_params(self, content: str) -> List[Dict]:
        """Parse widget definitions to extract parameter details"""
        params = []
        # Only match widget creation methods, not get()
        widget_pattern = r'dbutils\.widgets\.(text|dropdown|combobox|multiselect)\s*\(\s*["\']([^"\']+)["\'](?:\s*,\s*["\']([^"\']+)["\'])?'
        
        for match in re.finditer(widget_pattern, content):
            param = {
                "type": match.group(1),  # text, dropdown, etc.
                "name": match.group(2),
                "default": match.group(3) if match.group(3) else None
            }
            params.append(param)
        
        return params
    
    def _detect_workflow_patterns(self, content: str, file_type: str) -> Dict[str, Any]:
        """Detect ETL, ML, or other workflow patterns"""
        patterns = {
            "workflow_type": "unknown",
            "stages": [],
            "confidence": 0.0
        }
        
        content_lower = content.lower()
        
        # Check for visualization/reporting patterns first (highest priority)
        viz_keywords = ['matplotlib', 'plotly', 'seaborn', 'display(', '.plot(', 'plt.', 'sns.', 'fig']
        if any(viz in content_lower for viz in viz_keywords):
            patterns["workflow_type"] = "reporting"
            patterns["stages"] = ["visualization"]
            patterns["confidence"] = 0.9
            return patterns  # Return early if reporting detected
        
        # Check for ML patterns - look for actual model training/evaluation
        ml_score = 0
        ml_stages = []
        has_model_training = False
        for stage, keywords in self.ML_PATTERNS.items():
            stage_found = False
            for keyword in keywords:
                if keyword.lower() in content_lower:
                    stage_found = True
                    if stage == 'training':
                        has_model_training = True
                    break
            if stage_found:
                ml_score += 1
                ml_stages.append(stage)
        
        # Check for ETL patterns
        etl_score = 0
        etl_stages = []
        for stage, keywords in self.ETL_PATTERNS.items():
            if any(keyword.lower() in content_lower for keyword in keywords):
                etl_score += 1
                etl_stages.append(stage)
        
        # Determine primary pattern
        # ETL takes precedence unless there's actual model training
        if has_model_training and ml_score >= 2:
            patterns["workflow_type"] = "ML"
            patterns["stages"] = ml_stages
            patterns["confidence"] = min(ml_score / 3.0, 1.0)
        elif etl_score >= 2:
            patterns["workflow_type"] = "ETL"
            patterns["stages"] = etl_stages
            patterns["confidence"] = min(etl_score / 3.0, 1.0)
        elif 'CREATE TABLE' in content.upper() or 'CREATE VIEW' in content.upper():
            patterns["workflow_type"] = "DDL"
            patterns["stages"] = ["schema_definition"]
            patterns["confidence"] = 0.8
        # If only mlflow logging without model training, still consider it ETL
        elif etl_score >= 1 and not has_model_training:
            patterns["workflow_type"] = "ETL"
            patterns["stages"] = etl_stages
            patterns["confidence"] = min(etl_score / 3.0, 1.0)
        
        return patterns
    
    def _split_notebook_cells(self, content: str) -> List[Dict]:
        """Split Databricks notebook content into cells"""
        cells = []
        current_cell = []
        current_language = 'python'
        line_number = 0
        
        for line in content.splitlines():
            line_number += 1
            
            # Check for cell separator
            if '# COMMAND ----------' in line or '-- COMMAND ----------' in line:
                if current_cell:
                    cells.append({
                        'content': '\n'.join(current_cell),
                        'language': current_language,
                        'line_start': line_number - len(current_cell)
                    })
                    current_cell = []
            # Check for magic commands
            elif line.strip().startswith('# MAGIC %'):
                match = re.match(r'# MAGIC %(\w+)', line)
                if match:
                    current_language = match.group(1)
                current_cell.append(line.replace('# MAGIC ', ''))
            else:
                current_cell.append(line)
        
        # Add last cell
        if current_cell:
            cells.append({
                'content': '\n'.join(current_cell),
                'language': current_language,
                'line_start': line_number - len(current_cell)
            })
        
        return cells
    
    def _extract_sql_tables(self, statement: str, keywords: str) -> List[str]:
        """Extract table names from SQL statement"""
        tables = []
        # Improved pattern to handle various SQL table references
        pattern = rf'(?:{keywords})\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:TABLE\s+)?([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)'
        
        for match in re.finditer(pattern, statement, re.IGNORECASE):
            table_name = match.group(1)
            # Filter out SQL keywords that might be captured
            if table_name.upper() not in ['TABLE', 'INTO', 'FROM', 'JOIN', 'WHERE', 'AS', 'SELECT']:
                tables.append(table_name)
        
        return tables
    
    def _generate_recommendations(self, analysis: Dict) -> Dict[str, Any]:
        """Generate DAB configuration recommendations based on analysis"""
        recommendations = {
            "job_type": "batch",
            "cluster_config": {},
            "schedule": None,
            "libraries": [],
            "parameters": []
        }
        
        # Determine job type
        patterns = analysis.get("patterns", {})
        workflow_type = patterns.get("workflow_type", "unknown")
        
        if workflow_type == "ETL":
            recommendations["job_type"] = "scheduled_batch"
            recommendations["schedule"] = "0 2 * * *"  # Daily at 2 AM
            recommendations["cluster_config"] = {
                "spark_version": "13.3.x-scala2.12",
                "node_type_id": "i3.xlarge",
                "num_workers": 2
            }
        elif workflow_type == "ML":
            recommendations["job_type"] = "ml_training"
            recommendations["cluster_config"] = {
                "spark_version": "13.3.x-ml-scala2.12",
                "node_type_id": "g4dn.xlarge",
                "num_workers": 1
            }
            recommendations["libraries"].append({"pypi": {"package": "mlflow"}})
        elif workflow_type == "reporting":
            recommendations["job_type"] = "scheduled_report"
            recommendations["schedule"] = "0 8 * * 1-5"  # Weekdays at 8 AM
        
        # Add detected parameters
        databricks_features = analysis.get("databricks_features", {})
        if "widget_params" in databricks_features:
            for widget in databricks_features["widget_params"]:
                recommendations["parameters"].append({
                    "name": widget["name"],
                    "type": widget["type"],
                    "default": widget["default"]
                })
        
        # Add library recommendations
        deps = analysis.get("dependencies", {})
        if "third_party" in deps:
            for lib in deps["third_party"]:
                if lib not in ['pyspark', 'databricks']:  # Skip built-ins
                    recommendations["libraries"].append({"pypi": {"package": lib}})
        
        # Suggest Unity Catalog if tables are referenced
        data_sources = analysis.get("data_sources", {})
        if data_sources.get("input_tables") or data_sources.get("output_tables"):
            recommendations["requires_unity_catalog"] = True
        
        return recommendations