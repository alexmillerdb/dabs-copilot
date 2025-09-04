# Phase 2 Project Plan: DAB Generation Tools
## MCP Server Enhancement for Databricks Asset Bundle Generation

### 📋 Executive Summary

Phase 2 extends the working MCP server (9 operational tools) to add intelligent DAB (Databricks Asset Bundle) generation capabilities. This phase focuses on analyzing existing Databricks assets (notebooks, jobs) and generating production-ready bundle configurations with comprehensive test scaffolding.

**Duration**: 1 week (Week 3 of 4-week hackathon)  
**Approach**: Test-Driven Development (TDD) with incremental feature delivery  
**Goal**: Enable natural language DAB generation through Claude Code CLI

---

## 🎯 Phase 2 Objectives

### Primary Goals
1. **Analyze** existing Databricks notebooks and jobs to understand structure and dependencies
2. **Generate** valid DAB configurations from analyzed resources
3. **Create** unit test scaffolds for generated bundles
4. **Validate** generated configurations for correctness and best practices

### Success Criteria
- [ ] 4 new MCP tools operational and tested
- [ ] Generate valid `databricks.yml` from existing notebooks/jobs
- [ ] Create deployable bundles with proper resource definitions
- [ ] Unit test coverage > 90% for all new tools
- [ ] Integration with Claude Code CLI maintained

---

## 🛠️ Tool Specifications

### Tool 1: `analyze_notebook`
**Purpose**: Deep analysis of notebook content, dependencies, and patterns

**Input Parameters**:
```python
{
    "notebook_path": str,           # Path to notebook in workspace
    "include_dependencies": bool,   # Analyze imports and libraries
    "include_data_sources": bool,   # Extract table/file references
    "detect_patterns": bool          # Identify ETL/ML/reporting patterns
}
```

**Output Structure**:
```json
{
    "success": true,
    "data": {
        "notebook_info": {
            "path": "/Users/alex/etl_pipeline.py",
            "language": "PYTHON",
            "size_bytes": 15234,
            "last_modified": "2025-09-04T10:30:00Z"
        },
        "dependencies": {
            "imports": ["pandas", "pyspark.sql", "delta"],
            "databricks_libraries": ["databricks-sdk"],
            "custom_modules": ["utils.data_quality"]
        },
        "data_sources": {
            "input_tables": ["main.raw.sales", "main.raw.customers"],
            "output_tables": ["main.silver.sales_aggregated"],
            "file_paths": ["/mnt/data/configs/mapping.json"]
        },
        "patterns": {
            "type": "ETL",
            "stages": ["ingestion", "transformation", "aggregation"],
            "estimated_complexity": "medium"
        },
        "parameters": {
            "widgets": ["date", "environment"],
            "config_references": ["spark.sql.shuffle.partitions"]
        },
        "recommendations": {
            "job_type": "scheduled_batch",
            "cluster_size": "small",
            "suggested_schedule": "0 2 * * *"
        }
    },
    "timestamp": "2025-09-04T14:30:00Z"
}
```

### Tool 2: `generate_bundle`
**Purpose**: Create complete DAB configuration from analysis

**Input Parameters**:
```python
{
    "bundle_name": str,              # Name for the bundle
    "resources": List[str],          # Paths to notebooks/jobs to include
    "target_environment": str,       # dev/staging/prod
    "include_tests": bool,           # Generate test configurations
    "output_path": str               # Where to save bundle files
}
```

**Output Structure**:
```json
{
    "success": true,
    "data": {
        "bundle_path": "/generated/my-etl-bundle",
        "files_created": [
            "databricks.yml",
            "resources/etl_job.yml",
            "resources/cluster_config.yml",
            "tests/test_etl_pipeline.py"
        ],
        "configuration": {
            "bundle_name": "com.company.etl_pipeline",
            "targets": ["dev", "staging", "prod"],
            "resources_count": 3,
            "tests_count": 5
        },
        "validation_status": "PASSED",
        "deployment_ready": true
    },
    "timestamp": "2025-09-04T14:35:00Z"
}
```

### Tool 3: `validate_bundle`
**Purpose**: Validate generated or existing bundle configurations

**Input Parameters**:
```python
{
    "bundle_path": str,              # Path to bundle root directory
    "target": str,                   # Target environment to validate
    "check_best_practices": bool,   # Apply best practice rules
    "check_security": bool           # Security policy validation
}
```

**Output Structure**:
```json
{
    "success": true,
    "data": {
        "validation_passed": true,
        "errors": [],
        "warnings": [
            {
                "type": "naming_convention",
                "resource": "etl_job",
                "message": "Job name should include environment prefix"
            }
        ],
        "best_practices": {
            "score": 85,
            "suggestions": [
                "Add retry policy to job configuration",
                "Consider using job clusters instead of all-purpose"
            ]
        },
        "security_checks": {
            "passed": true,
            "issues": []
        }
    },
    "timestamp": "2025-09-04T14:40:00Z"
}
```

### Tool 4: `create_tests`
**Purpose**: Generate unit and integration test scaffolds

**Input Parameters**:
```python
{
    "resource_type": str,            # notebook/job/pipeline
    "resource_path": str,            # Path to resource
    "test_framework": str,           # pytest/unittest
    "include_mocks": bool,           # Generate mock configurations
    "include_fixtures": bool         # Create test fixtures
}
```

**Output Structure**:
```json
{
    "success": true,
    "data": {
        "tests_created": [
            "test_notebook_execution.py",
            "test_data_quality.py",
            "test_job_configuration.py"
        ],
        "test_count": 12,
        "framework": "pytest",
        "mocks_generated": [
            "mock_spark_session.py",
            "mock_dbutils.py"
        ],
        "fixtures": [
            "sample_input_data.json",
            "expected_output.parquet"
        ],
        "coverage_estimate": "75%"
    },
    "timestamp": "2025-09-04T14:45:00Z"
}
```

---

## 🧪 TDD Test Specifications

### Test Categories

#### 1. Unit Tests (Per Tool)
Each tool will have comprehensive unit tests covering:

**Test Structure Example for `analyze_notebook`**:
```python
# tests/test_analyze_notebook.py

class TestAnalyzeNotebook:
    """Test suite for analyze_notebook tool"""
    
    def test_analyze_python_notebook(self):
        """Test analysis of Python notebook with imports and data sources"""
        # Given: A Python notebook with pandas, spark imports and table refs
        # When: analyze_notebook is called with all flags enabled
        # Then: Should extract all dependencies and data sources correctly
    
    def test_analyze_sql_notebook(self):
        """Test analysis of SQL notebook with CTEs and joins"""
        # Given: SQL notebook with complex queries
        # When: analyze_notebook is called
        # Then: Should identify input/output tables correctly
    
    def test_pattern_detection_etl(self):
        """Test ETL pattern detection in notebook"""
        # Given: Notebook with read -> transform -> write pattern
        # When: analyze_notebook with detect_patterns=True
        # Then: Should identify as ETL with correct stages
    
    def test_parameter_extraction(self):
        """Test widget and parameter extraction"""
        # Given: Notebook with dbutils.widgets.text() calls
        # When: analyze_notebook is called
        # Then: Should extract all widget definitions
    
    def test_error_handling_invalid_path(self):
        """Test handling of invalid notebook path"""
        # Given: Non-existent notebook path
        # When: analyze_notebook is called
        # Then: Should return error response with clear message
```

**Test Structure Example for `generate_bundle`**:
```python
# tests/test_generate_bundle.py

class TestGenerateBundle:
    """Test suite for generate_bundle tool"""
    
    def test_generate_simple_bundle(self):
        """Test generation of basic bundle with single notebook"""
        # Given: Analysis results from single notebook
        # When: generate_bundle is called
        # Then: Should create valid databricks.yml and resource files
    
    def test_generate_multi_resource_bundle(self):
        """Test bundle with multiple notebooks and jobs"""
        # Given: Multiple analyzed resources
        # When: generate_bundle is called
        # Then: Should create bundle with proper dependencies
    
    def test_environment_targeting(self):
        """Test target environment configuration"""
        # Given: Bundle request for dev/staging/prod
        # When: generate_bundle with different targets
        # Then: Should create appropriate target configurations
    
    def test_test_generation_flag(self):
        """Test optional test file generation"""
        # Given: Bundle request with include_tests=True
        # When: generate_bundle is called
        # Then: Should create test files alongside bundle
    
    def test_yaml_validity(self):
        """Test generated YAML is valid and parseable"""
        # Given: Generated bundle files
        # When: YAML files are parsed
        # Then: Should be valid YAML with correct schema
```

#### 2. Integration Tests
End-to-end workflow tests:

```python
# tests/test_integration_workflow.py

class TestDABGenerationWorkflow:
    """Integration tests for complete DAB generation workflow"""
    
    def test_notebook_to_bundle_workflow(self):
        """Test complete flow from notebook to deployable bundle"""
        # Step 1: Export notebook using existing tool
        # Step 2: Analyze notebook
        # Step 3: Generate bundle
        # Step 4: Validate bundle
        # Step 5: Create tests
        # Assertion: Complete, deployable bundle created
    
    def test_job_to_bundle_workflow(self):
        """Test converting existing job to bundle"""
        # Step 1: Get job configuration
        # Step 2: Analyze job structure
        # Step 3: Generate bundle from job
        # Step 4: Validate against original job
        # Assertion: Bundle matches job configuration
    
    def test_multi_notebook_dependency_workflow(self):
        """Test bundle generation for interconnected notebooks"""
        # Step 1: Analyze multiple related notebooks
        # Step 2: Map dependencies
        # Step 3: Generate bundle with proper ordering
        # Step 4: Validate dependency chain
        # Assertion: Dependencies correctly represented
```

#### 3. Validation Tests
Configuration and output validation:

```python
# tests/test_validation.py

class TestBundleValidation:
    """Test bundle validation logic"""
    
    def test_schema_validation(self):
        """Test bundle conforms to DAB schema"""
        # Given: Generated bundle configuration
        # When: Validated against official schema
        # Then: Should pass all schema checks
    
    def test_security_validation(self):
        """Test security best practices"""
        # Given: Bundle with various configurations
        # When: Security checks are run
        # Then: Should flag any security issues
    
    def test_naming_conventions(self):
        """Test resource naming standards"""
        # Given: Bundle with resources
        # When: Naming convention checks run
        # Then: Should validate or suggest improvements
```

#### 4. Performance Tests
```python
# tests/test_performance.py

class TestPerformance:
    """Performance testing for analysis tools"""
    
    def test_large_notebook_analysis(self):
        """Test analysis speed for large notebooks"""
        # Given: 1000+ line notebook
        # When: analyze_notebook is called
        # Then: Should complete in < 5 seconds
    
    def test_concurrent_analysis(self):
        """Test multiple simultaneous analyses"""
        # Given: 10 notebooks to analyze
        # When: Analyzed concurrently
        # Then: Should handle without errors
```

---

## 📅 Implementation Timeline

### Day 1-2: Foundation & Test Setup
**Monday-Tuesday (Week 3)**

#### Tasks:
- [ ] Create test infrastructure and fixtures
- [ ] Write comprehensive test cases for all 4 tools
- [ ] Set up test data (sample notebooks, job configs)
- [ ] Create mock Databricks client for testing
- [ ] Implement base response structures

#### Deliverables:
- Complete test suite (failing tests)
- Test fixtures and mock data
- CI/CD test pipeline configuration

### Day 3-4: Core Tool Implementation
**Wednesday-Thursday**

#### Tasks:
- [ ] Implement `analyze_notebook` tool
  - [ ] AST parsing for Python notebooks
  - [ ] SQL query parsing
  - [ ] Pattern detection algorithms
  - [ ] Dependency extraction
  
- [ ] Implement `generate_bundle` tool
  - [ ] YAML template engine
  - [ ] Resource mapping logic
  - [ ] Multi-environment support
  - [ ] File generation system

#### Deliverables:
- Working analysis tool with passing tests
- Bundle generation with basic templates
- 80% test coverage achieved

### Day 5: Advanced Features & Validation
**Friday**

#### Tasks:
- [ ] Implement `validate_bundle` tool
  - [ ] Schema validation
  - [ ] Best practice rules engine
  - [ ] Security policy checks
  
- [ ] Implement `create_tests` tool
  - [ ] Test template generation
  - [ ] Mock service creation
  - [ ] Fixture generation

#### Deliverables:
- All 4 tools operational
- Validation framework complete
- Test generation working

### Day 6-7: Integration & Polish
**Weekend (if needed)**

#### Tasks:
- [ ] End-to-end integration testing
- [ ] Performance optimization
- [ ] Documentation updates
- [ ] Claude Code CLI integration testing
- [ ] Bug fixes and refinements

#### Deliverables:
- Fully integrated Phase 2 tools
- Updated documentation
- Demo-ready implementation

---

## 🏗️ Technical Architecture

### Component Structure
```
mcp/
├── server/
│   ├── tools.py                    # Existing 9 tools
│   ├── tools_dab.py                # NEW: 4 DAB generation tools
│   ├── services/
│   │   ├── databricks_service.py   # Existing
│   │   ├── analysis_service.py     # NEW: Notebook/job analysis logic
│   │   ├── generation_service.py   # NEW: Bundle generation logic
│   │   └── validation_service.py   # NEW: Validation and testing logic
│   └── templates/                   # NEW: DAB templates
│       ├── bundle_base.yaml.j2
│       ├── job_resource.yaml.j2
│       ├── pipeline_resource.yaml.j2
│       └── test_template.py.j2
├── tests/
│   ├── test_tools.py               # Existing
│   ├── test_analyze_notebook.py    # NEW
│   ├── test_generate_bundle.py     # NEW
│   ├── test_validate_bundle.py     # NEW
│   ├── test_create_tests.py        # NEW
│   ├── test_integration.py         # NEW
│   └── fixtures/                   # NEW: Test data
│       ├── sample_notebooks/
│       ├── sample_jobs/
│       └── expected_outputs/
└── utils/                          # NEW: Shared utilities
    ├── ast_parser.py              # Python AST analysis
    ├── sql_parser.py              # SQL parsing
    ├── pattern_detector.py        # Pattern recognition
    └── yaml_generator.py          # YAML generation helpers
```

### Key Dependencies
```python
# New dependencies for requirements.txt
pyyaml>=6.0          # YAML generation and parsing
jinja2>=3.1          # Template engine for bundle generation
sqlparse>=0.4        # SQL parsing for notebook analysis
astunparse>=1.6      # Python AST manipulation
jsonschema>=4.0      # Schema validation
pytest>=7.0          # Testing framework
pytest-asyncio>=0.21 # Async test support
pytest-mock>=3.10    # Mocking support
black>=23.0          # Code formatting
ruff>=0.1            # Linting
```

### Design Patterns

#### 1. Service Layer Pattern
Separate business logic from MCP tool definitions:
```python
# services/analysis_service.py
class NotebookAnalysisService:
    def analyze_python_code(self, content: str) -> Dict
    def extract_dependencies(self, ast_tree: ast.Module) -> List[str]
    def detect_patterns(self, ast_tree: ast.Module) -> Dict
    def extract_data_sources(self, content: str) -> Dict

# tools_dab.py uses the service
@mcp.tool()
async def analyze_notebook(...) -> str:
    service = NotebookAnalysisService()
    result = await service.analyze(...)
    return create_success_response(result)
```

#### 2. Template Pattern
Flexible YAML generation using Jinja2:
```python
# services/generation_service.py
class BundleGenerationService:
    def __init__(self):
        self.template_env = Environment(loader=FileSystemLoader('templates'))
    
    def generate_bundle_yaml(self, config: Dict) -> str:
        template = self.template_env.get_template('bundle_base.yaml.j2')
        return template.render(config)
```

#### 3. Strategy Pattern
Different analysis strategies for different notebook types:
```python
# utils/pattern_detector.py
class PatternDetector:
    strategies = {
        'python': PythonPatternStrategy(),
        'sql': SQLPatternStrategy(),
        'scala': ScalaPatternStrategy()
    }
    
    def detect(self, content: str, language: str) -> Dict:
        strategy = self.strategies.get(language)
        return strategy.analyze(content)
```

---

## 🚀 Implementation Guidelines

### Code Quality Standards

1. **Test Coverage**: Minimum 90% coverage for new code
2. **Type Hints**: All functions must have type annotations
3. **Documentation**: Docstrings for all public methods
4. **Linting**: Pass ruff and black formatting checks
5. **Async/Await**: Maintain async patterns for MCP tools

### Error Handling Strategy

```python
# Consistent error handling pattern
try:
    # Tool logic here
    result = await perform_operation()
    return create_success_response(result)
except ValidationError as e:
    logger.warning(f"Validation error: {e}")
    return create_error_response(f"Invalid input: {str(e)}")
except DatabricksError as e:
    logger.error(f"Databricks API error: {e}")
    return create_error_response(f"Workspace error: {str(e)}")
except Exception as e:
    logger.exception("Unexpected error in tool")
    return create_error_response("An unexpected error occurred")
```

### Testing Best Practices

1. **Arrange-Act-Assert**: Clear test structure
2. **One Assertion Per Test**: Focused test cases
3. **Mock External Dependencies**: No real API calls in tests
4. **Fixture Reuse**: Shared test data fixtures
5. **Parametrized Tests**: Cover multiple scenarios efficiently

### Performance Considerations

1. **Caching**: Cache analysis results for repeated requests
2. **Async Operations**: Non-blocking I/O for all tools
3. **Lazy Loading**: Load templates and parsers on demand
4. **Batch Processing**: Handle multiple resources efficiently
5. **Progress Reporting**: Stream progress for long operations

---

## 📊 Success Metrics

### Quantitative Metrics
- [ ] 4 new tools fully implemented and tested
- [ ] >90% test coverage for new code
- [ ] <5 second response time for analysis operations
- [ ] <10 second bundle generation time
- [ ] 100% of generated bundles pass validation

### Qualitative Metrics
- [ ] Natural language DAB generation via Claude
- [ ] Generated bundles follow Databricks best practices
- [ ] Clear, actionable error messages
- [ ] Comprehensive test scaffolding
- [ ] Maintainable, well-documented code

### Demo Scenarios
1. **Simple ETL Pipeline**: Convert notebook to scheduled job bundle
2. **ML Training Workflow**: Multi-stage pipeline with experiments
3. **Data Quality Pipeline**: Bundle with integrated testing
4. **Migration Scenario**: Convert existing jobs to bundles

---

## 🔄 Risk Management

### Technical Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Complex AST parsing | High | Use established libraries, incremental parsing |
| YAML generation errors | Medium | Schema validation, extensive testing |
| Performance issues | Medium | Implement caching, async operations |
| Integration complexity | Low | Maintain Phase 1 patterns, isolated testing |

### Schedule Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Test creation time | Medium | Use test generators, shared fixtures |
| Complex notebook patterns | Medium | Start with common patterns, iterate |
| Validation complexity | Low | Leverage Databricks CLI validation |

---

## 📝 Documentation Requirements

### Developer Documentation
- [ ] API documentation for all new tools
- [ ] Service layer architecture guide
- [ ] Template customization guide
- [ ] Testing strategy documentation

### User Documentation
- [ ] Tool usage examples in README
- [ ] Common workflow tutorials
- [ ] Troubleshooting guide
- [ ] Best practices guide

### Code Documentation
- [ ] Inline comments for complex logic
- [ ] Docstrings with examples
- [ ] Type hints throughout
- [ ] Architecture decision records

---

## 🎯 Definition of Done

A tool is considered complete when:

1. **Functionality**: Tool performs intended function correctly
2. **Testing**: >90% test coverage with all tests passing
3. **Documentation**: Complete docstrings and usage examples
4. **Integration**: Works with Claude Code CLI
5. **Performance**: Meets response time requirements
6. **Error Handling**: Graceful failure with clear messages
7. **Code Quality**: Passes linting and formatting checks
8. **Review**: Code reviewed and approved

---

## 📋 Next Steps

### Immediate Actions (Before Starting)
1. Review and approve this project plan
2. Set up development environment with new dependencies
3. Create test fixtures from real Databricks notebooks
4. Establish CI/CD pipeline for automated testing

### Day 1 Kickoff
1. Morning standup to align on approach
2. Create all test files with failing tests
3. Set up service layer structure
4. Begin implementation following TDD

### Daily Routine
1. Morning: Review previous day's work
2. Implementation: Follow TDD cycle (Red-Green-Refactor)
3. Testing: Run full test suite before commits
4. Evening: Update progress tracking

This comprehensive plan ensures Phase 2 delivers robust, well-tested DAB generation capabilities while maintaining the high standards established in Phase 1.