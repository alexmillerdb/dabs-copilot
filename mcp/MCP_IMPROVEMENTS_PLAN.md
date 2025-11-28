# MCP Codebase Improvements Plan

Based on analysis against **Anthropic MCP Builder best practices**.

---

## Official MCP Builder Standards

### Server Naming Convention
- **Required**: `{service}_mcp` (lowercase, underscores)
- **Current**: `databricks-mcp` (uses hyphens)

### Tool Naming Convention
- **Required**: `{service}_{action}_{resource}` (snake_case with service prefix)
- **Current**: `health`, `list_jobs`, `get_job` (missing service prefix)

### Tool Annotations (Required)
```python
@mcp.tool(annotations={
    "readOnlyHint": True,      # Doesn't modify state
    "destructiveHint": False,  # Non-destructive
    "idempotentHint": True,    # Safe to retry
    "openWorldHint": True      # Interacts with external service
})
```

### Pydantic v2 Patterns
- Use `model_config = ConfigDict(...)` not nested `Config` class
- Use `field_validator` with `@classmethod` decorator
- Use `model_dump()` not `dict()`

---

## Implementation Phases

### Phase 1: Bug Fixes (Critical)
1. Remove `create_tests` tool from `tools_dab.py`
2. Fix hardcoded `profile="aws-apps"` with env var
3. Standardize `databricks.yml` naming

### Phase 2: Main.py Cleanup (High)
4. Refactor main.py per MCP Builder standards
5. Configure stderr logging (not stdout)
6. Remove print statements and internal API access

### Phase 3: MCP Compliance (High)
7. Add tool annotations to all 17 tools
8. Add comprehensive docstrings with schema docs
9. Implement centralized error handling

### Phase 4: Code Quality (Medium)
10. Add Pydantic v2 input validation
11. Clean up unused code files
12. Verify stderr logging throughout

### Phase 5: Evaluations (Medium)
13. Create evaluation XML file with 10 questions
14. Create evaluation runner script
15. Validate evaluations against live workspace

---

## Tool Annotations Reference

| Tool | readOnlyHint | destructiveHint | idempotentHint | openWorldHint |
|------|--------------|-----------------|----------------|---------------|
| health | True | False | True | True |
| list_jobs | True | False | True | True |
| get_job | True | False | True | True |
| run_job | False | True | False | True |
| list_notebooks | True | False | True | True |
| export_notebook | True | False | True | True |
| execute_dbsql | False | Depends | False | True |
| list_warehouses | True | False | True | True |
| list_dbfs_files | True | False | True | True |
| analyze_notebook | True | False | True | True |
| generate_bundle | True | False | True | False |
| validate_bundle | True | False | True | True |
| generate_bundle_from_job | True | False | True | True |
| get_cluster | True | False | True | True |
| upload_bundle | False | False | True | True |
| run_bundle_command | False | True | False | True |
| sync_workspace_to_local | False | False | True | True |

---

## Critical Files

| File | Priority | Changes |
|------|----------|---------|
| `server/main.py` | High | Complete refactor for MCP compliance |
| `server/tools_dab.py` | High | Remove create_tests, fix profile, add annotations |
| `server/tools.py` | High | Add annotations, docstrings, error handling |
| `server/tools_workspace.py` | High | Add annotations, docstrings |
| `evaluations/databricks_mcp_eval.xml` | Medium | New file - 10 evaluation questions |
| `scripts/run_evaluation.py` | Medium | New file - evaluation runner |

---

## Verification Steps

1. Run MCP server and verify tool list (17 tools, no `create_tests`)
2. Test `health` tool works without hardcoded profile
3. Verify tool annotations appear in MCP tool metadata
4. Run existing tests to ensure no regressions
5. Verify main.py outputs nothing to stdout
6. Run evaluations and verify accuracy > 80%
