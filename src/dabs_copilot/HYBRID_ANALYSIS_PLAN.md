# Hybrid Notebook Analysis: Deterministic + LLM Approach

## Implementation Progress

| Step | Status | Description |
|------|--------|-------------|
| Step 1 | ✅ COMPLETE | Enhanced Deterministic Analysis |
| Step 2 | ✅ COMPLETE | Update Analyst Subagent Prompt |
| Step 3 | ✅ COMPLETE | Add Caching Infrastructure |
| Step 4 | ✅ COMPLETE | Enhanced Output Schema (done with Step 1) |
| Step 5 | ✅ COMPLETE | Tests (done with Step 1) |

### Steps 2 & 3 Completion Summary (2025-12-05)

**Step 2: Update Analyst Subagent Prompt**
- Added "Hybrid Analysis Mode" section to `DAB_ANALYST_PROMPT` in `prompts.py`
- Documents two-phase approach: deterministic (always) + semantic (conditional)
- Analyst checks `complexity_score` and provides semantic analysis when ≥ 0.5

**Step 3: Add Caching Infrastructure**
- Added disk-based caching to `sdk_tools.py`
- Cache location: `.cache/analysis/` (already in `.gitignore`)
- Cache key: `{filename}_{content_hash}_{mtime}`
- New fields in output: `cached` (bool), `cache_key` (str)
- Optional `skip_cache` parameter to force fresh analysis

---

### Step 1 Completion Summary (2025-12-05)

**Files Created/Modified:**
- `src/dabs_copilot/tools/analysis.py` (NEW) - 500+ lines of enhanced analysis logic
- `src/dabs_copilot/tools/sdk_tools.py` (MODIFIED) - Updated to use new analysis module
- `tests/test_enhanced_analysis.py` (NEW) - 29 comprehensive tests
- `pyproject.toml` (MODIFIED) - Added sqlparse dependency

**Features Implemented:**
- AST-based Python parsing with regex fallback
- SQL analysis with sqlparse
- Dependency categorization (standard_library, third_party, databricks, local)
- Data source extraction (input_tables, output_tables, file_paths)
- 9 Databricks-specific pattern detection
- Workflow type detection with confidence scoring
- Complexity scoring for hybrid analysis trigger
- Full backward compatibility with original output schema

**Test Results:** 29/29 tests passing

---

## Overview

Enhance the `analyze_notebook` functionality with a **hybrid approach** that combines:
1. **Tool-side (Deterministic)**: Fast, reliable extraction using AST parsing and regex patterns
2. **LLM-side (Semantic)**: Deep understanding of code intent, architecture, and complex relationships

This enables both quick analysis for simple tasks and comprehensive semantic analysis for complex multi-component workflows (ETL+ML, data pipelines with orchestration, etc.).

---

## Current State Analysis

### Existing Implementation
- **Old**: `sdk_tools.py:295-358` - Simple regex-based extraction
- **New**: `analysis_service.py` - Comprehensive deterministic analysis with:
  - AST parsing for Python
  - sqlparse for SQL
  - 9 Databricks-specific patterns
  - Workflow type detection with confidence scoring
  - Recommendation generation

### Gap Identified
The deterministic approach excels at **what** the code does but struggles with **why** and **how** components relate. For complex notebooks:
- Cannot understand business logic intent
- Misses architectural patterns (medallion, star schema)
- Cannot infer dependencies between separate files
- Struggles with mixed-intent notebooks (ETL + reporting + ML in one)

---

## Proposed Hybrid Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    analyze_notebook_hybrid()                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────┐    ┌──────────────────────────┐  │
│  │   DETERMINISTIC LAYER    │    │      LLM LAYER           │  │
│  │   (Always runs)          │    │   (On-demand)            │  │
│  ├──────────────────────────┤    ├──────────────────────────┤  │
│  │ • AST parsing            │    │ • Semantic understanding │  │
│  │ • Regex patterns         │    │ • Intent classification  │  │
│  │ • Import extraction      │    │ • Architecture detection │  │
│  │ • Widget detection       │    │ • Dependency inference   │  │
│  │ • Table extraction       │    │ • Quality assessment     │  │
│  │ • Workflow type (basic)  │    │ • Recommendations        │  │
│  └──────────────────────────┘    └──────────────────────────┘  │
│              │                              │                    │
│              ▼                              ▼                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   MERGED RESULT                           │  │
│  │  deterministic_analysis + semantic_analysis + confidence  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Design Decisions

### LLM Integration: Subagent-at-Agent-Level (Recommended)

**Rationale**: MCP tools cannot spawn subagents (Task tool is only available to the main agent). The cleanest approach is to:
1. Keep `analyze_notebook` tool as **fast deterministic-only**
2. Add **complexity_score** to the output
3. Let the **analyst subagent** provide semantic analysis when needed

This leverages your existing architecture (`agent.py:207-265`) without adding new API dependencies.

**How it works:**
```
User: "Analyze job 12345"
        │
        ▼
Main Agent → Spawns dab-analyst subagent
        │
        ▼
dab-analyst subagent:
  1. CALL analyze_notebook(path) → {deterministic + complexity_score}
  2. IF complexity_score > 0.5 OR deep analysis needed:
     - Read notebook content
     - Provide semantic analysis inline (agent's LLM reasoning)
  3. Return combined analysis
```

### Caching: Hash + Mtime Based (Disk Cache)

**Location**: `.cache/analysis/` in project root (added to `.gitignore`)

**Rationale**: Zero context impact, intelligent invalidation, persists across sessions.

**How agent.py "knows" about the cache:**
- The agent **doesn't** manage the cache - it's internal to the tool
- Agent calls `analyze_notebook(path)` and gets results
- Cache is transparent: fast return if cached, fresh analysis if not
- Agent can request `skip_cache=true` for forced fresh analysis

### Multi-file Analysis: Phase 2

Focus on single-file hybrid analysis first. Add `analyze_project` tool after validating the approach.

---

## Implementation Order

### Step 1: Enhance Deterministic Analysis ✅ COMPLETE
**Files**: `src/dabs_copilot/tools/analysis.py` (NEW), `sdk_tools.py` (MODIFIED)

1. Integrate patterns from `mcp/server/services/analysis_service.py`
2. Add complexity scoring to output
3. Add disk caching for deterministic results
4. Update `_analyze_notebook_impl()` to be more comprehensive

**Changes:**
```python
# Add to sdk_tools.py (project root)
CACHE_DIR = Path(".cache/analysis")  # Added to .gitignore

def _calculate_complexity_score(analysis: dict) -> float:
    """Score 0-1 based on code complexity."""
    score = 0.0
    # Multiple workflow patterns
    if len(analysis.get("detected_patterns", [])) > 1: score += 0.3
    # High dependency count
    if sum(len(v) for v in analysis.get("dependencies", {}).values()) > 10: score += 0.2
    # Multiple data sources
    if len(analysis.get("data_sources", {}).get("input_tables", [])) > 3: score += 0.2
    # Notebook-to-notebook calls
    if analysis.get("calls_other_notebooks"): score += 0.2
    # Low confidence detection
    if analysis.get("detection_confidence", 1.0) < 0.7: score += 0.3
    return min(score, 1.0)

# Update analyze_notebook tool to include complexity_score in output
```

### Step 2: Update Analyst Subagent Prompt (prompts.py)
**File**: `src/dabs_copilot/prompts.py`

Add hybrid analysis mode instructions:

```python
## Hybrid Analysis Mode

When analyzing notebooks:
1. CALL mcp__databricks-mcp__analyze_notebook for FAST deterministic extraction
   → Returns: imports, tables, widgets, workflow_type, complexity_score

2. Review complexity_score (0-1):
   - LOW (< 0.5): Deterministic is sufficient, report as-is
   - HIGH (≥ 0.5): Needs semantic analysis, continue to step 3

3. For HIGH complexity:
   a. Export/read the notebook content
   b. Provide YOUR semantic understanding:
      - Primary intent: What is this code trying to accomplish?
      - Architecture: Medallion? Star schema? Lambda? Custom?
      - Data flow: Source → transformations → destination
      - Quality concerns: Anti-patterns, hardcoded values, missing error handling
   c. Enhanced recommendations: Better cluster config, scheduling, parameters

4. Return unified analysis with both deterministic facts AND semantic insights
```

### Step 3: Add Caching Infrastructure (sdk_tools.py)
**File**: `src/dabs_copilot/tools/sdk_tools.py`

```python
import hashlib
import json
from pathlib import Path

CACHE_DIR = Path(".cache/analysis")

def _get_cache_key(file_path: str, content: str) -> str:
    """Generate cache key from file path and content hash."""
    try:
        mtime = int(os.path.getmtime(file_path))
    except OSError:
        mtime = 0  # Workspace paths don't have mtime
    content_hash = hashlib.sha256(content.encode()).hexdigest()[:12]
    name = Path(file_path).stem[:20]
    return f"{name}_{content_hash}_{mtime}"

def _load_from_cache(cache_key: str) -> dict | None:
    """Load cached analysis if exists."""
    cache_file = CACHE_DIR / f"{cache_key}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())
    return None

def _save_to_cache(cache_key: str, result: dict) -> None:
    """Save analysis to disk cache."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"{cache_key}.json"
    cache_file.write_text(json.dumps(result, indent=2))

# Update analyze_notebook to use cache
@tool("analyze_notebook", ...)
async def analyze_notebook(args: dict[str, Any]) -> dict[str, Any]:
    # Check cache first
    # Run analysis if miss
    # Cache result
    # Return with complexity_score
```

### Step 4: Enhanced Output Schema
**New fields in analyze_notebook response:**

```json
{
  "path": "/path/to/notebook.py",
  "file_type": "python",

  // Existing deterministic fields
  "libraries": ["pandas", "pyspark"],
  "widgets": [{"name": "date", "type": "text"}],
  "workflow_type": "ETL",
  "uses_spark": true,
  "uses_mlflow": false,

  // NEW: Enhanced deterministic fields
  "dependencies": {
    "databricks": ["pyspark", "delta"],
    "third_party": ["pandas"],
    "standard_library": ["logging"]
  },
  "data_sources": {
    "input_tables": ["main.bronze.sales"],
    "output_tables": ["main.silver.summary"]
  },
  "calls_other_notebooks": true,
  "notebook_calls": ["/Workspace/shared/utils"],

  // NEW: Complexity scoring
  "complexity_score": 0.65,
  "complexity_factors": ["multiple_data_sources", "notebook_calls", "mixed_patterns"],

  // NEW: Detection confidence
  "detection_confidence": 0.85,

  // Metadata
  "cached": false,
  "cache_key": "notebook_abc123_1701234567"
}
```

### Step 5: Tests
**File**: `tests/test_enhanced_analysis.py`

- Test complexity scoring with various notebooks
- Test caching behavior (hit/miss/invalidation)
- Test enhanced output schema
- Integration test with analyst subagent

---

## Files to Modify

| File | Action | Changes |
|------|--------|---------|
| `src/dabs_copilot/tools/sdk_tools.py` | Modify | Add complexity scoring, caching, enhanced extraction (~80 lines) |
| `src/dabs_copilot/prompts.py` | Modify | Update DAB_ANALYST_PROMPT with hybrid instructions (~30 lines) |
| `tests/test_enhanced_analysis.py` | Create | Test complexity, caching, output schema (~150 lines) |
| `.gitignore` | Modify | Add `.cache/` directory |

---

## Analysis Mode Decision Tree

```
                    analyze_notebook(mode=?)
                              │
              ┌───────────────┼───────────────┐
              │               │               │
         mode="fast"     mode="auto"     mode="full"
              │               │               │
              ▼               ▼               ▼
      Deterministic      Calculate       Deterministic
          Only          Complexity            +
              │               │           Semantic
              │      ┌────────┴────────┐      │
              │      │                 │      │
              │  score < 0.5      score >= 0.5│
              │      │                 │      │
              │      ▼                 ▼      │
              │  Deterministic    Deterministic
              │     Only              +       │
              │                   Semantic    │
              │                       │       │
              └───────────┬───────────┴───────┘
                          │
                          ▼
                    Return Result
```

---

## Example Output (Hybrid Mode)

```json
{
  "file_info": {
    "path": "/Workspace/Users/user/etl_pipeline.py",
    "type": "python_notebook",
    "size_bytes": 4523
  },
  "dependencies": {
    "databricks": ["pyspark", "delta", "mlflow"],
    "third_party": ["pandas", "numpy"],
    "standard_library": ["logging", "datetime"]
  },
  "data_sources": {
    "input_tables": ["main.bronze.sales", "main.bronze.customers"],
    "output_tables": ["main.silver.daily_summary"]
  },
  "databricks_features": {
    "widgets": [
      {"name": "date", "type": "text", "default": "2024-01-01"}
    ],
    "calls_other_notebooks": true,
    "uses_mlflow": true
  },
  "workflow_type": "ETL",
  "architecture_pattern": "medallion",
  "components": [
    {"name": "data_ingestion", "lines": "1-45", "purpose": "Load raw sales data"},
    {"name": "transformation", "lines": "47-120", "purpose": "Join and aggregate"},
    {"name": "output", "lines": "122-150", "purpose": "Write to silver layer"}
  ],
  "data_flow": "bronze.sales + bronze.customers → join on customer_id → aggregate daily → silver.daily_summary",
  "recommendations": {
    "job_type": "scheduled_batch",
    "cluster_config": {
      "spark_version": "14.3.x-scala2.12",
      "node_type_id": "i3.xlarge",
      "num_workers": 2
    },
    "schedule": "0 2 * * *",
    "parameters": ["date"]
  },
  "quality_concerns": [
    "Consider adding data quality checks before write",
    "Hardcoded path in line 67 should be parameterized"
  ],
  "analysis_mode": "hybrid",
  "complexity_score": 0.65
}
```

---

## Benefits of Hybrid Approach

| Aspect | Deterministic Only | LLM Only | Hybrid |
|--------|-------------------|----------|--------|
| Speed | Fast (< 1s) | Slow (3-10s) | Adaptive |
| Accuracy (extraction) | High | Variable | High |
| Semantic understanding | Low | High | High |
| Cost | Free | API costs | Optimized |
| Complex workflows | Poor | Good | Excellent |
| Simple tasks | Excellent | Overkill | Excellent |

---

## Summary: Why This Approach

1. **Minimal changes**: Enhances existing tools rather than creating new services
2. **Leverages architecture**: Uses existing subagent system for semantic analysis
3. **No new dependencies**: No Claude API calls in tools - subagent uses inherited model
4. **Cache is transparent**: Agent doesn't manage cache, just gets fast results
5. **Backwards compatible**: Same tool interface, richer output
