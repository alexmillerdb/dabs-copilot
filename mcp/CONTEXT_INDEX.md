# MCP Context Index - Quick Reference

## 🚀 Current State
- **15 operational tools** deployed to Databricks Apps
- **URL**: https://databricks-mcp-server-1444828305810485.aws.databricksapps.com
- **Phase 2**: 90% complete (4/5 DAB tools working)

## 📁 Context Files for DAB Generation

| File | Purpose | When to Use |
|------|---------|------------|
| `context/DAB_PATTERNS.md` | 5 bundle patterns with examples | Pattern selection for `generate_bundle` |
| `context/CLUSTER_CONFIGS.md` | Cluster sizing guidelines | Resource optimization |
| `context/BEST_PRACTICES.md` | Security, naming, performance | Bundle validation |
| `context/WORKFLOWS.md` | Common workflow implementations | Complex pipelines |

## 🛠️ Tool Context Requirements

### `analyze_notebook`
- **Input**: Notebook path
- **Context Needed**: None (self-contained)
- **Output**: Dependencies, patterns, data sources

### `generate_bundle` 
- **Input**: Analysis results + bundle name
- **Context Loaded**: All 3 context files (35K chars)
- **Output**: Generation context for Claude

### `validate_bundle`
- **Input**: Bundle path/YAML
- **Context Used**: BEST_PRACTICES.md for scoring
- **Output**: Validation results with recommendations

## 🎯 Quick Patterns

### Pattern Selection Logic
```python
if "mlflow" in dependencies:
    → ML Pipeline Pattern
elif multiple_notebooks:
    → Multi-Stage ETL Pattern  
elif "autoloader" or "streaming" in code:
    → Streaming Job Pattern
else:
    → Simple ETL Pattern
```

## 📝 Adding New Features

### 1. New Tool Checklist
- [ ] Add tool to `tools_dab.py` with `@mcp.tool()` decorator
- [ ] Create service in `services/` if complex logic
- [ ] Use standardized response format
- [ ] Test with Claude Code CLI

### 2. Context Extension
- Add patterns to `DAB_PATTERNS.md` (keep under 15KB)
- Update `CLUSTER_CONFIGS.md` for new workload types
- Add validation rules to `BEST_PRACTICES.md`

### 3. Response Format
```python
return create_success_response({
    "data": result,
    "context": {...},  # If Claude needs additional context
    "instructions": "..."  # Clear directives for Claude
})
```

## 🔄 Development Workflow

1. **Local Testing**
   ```bash
   cd mcp/server && python main.py  # Claude Code CLI
   cd mcp/server && python app.py   # FastAPI local
   ```

2. **Deploy to Databricks Apps**
   ```bash
   cd mcp && ./scripts/deploy.sh
   ```

3. **Test Deployment**
   ```bash
   TOKEN=$(databricks auth token --profile aws-apps | jq -r .access_token)
   curl -H "Authorization: Bearer $TOKEN" https://databricks-mcp-server-1444828305810485.aws.databricksapps.com/health
   ```

## 🏃 Next Features to Ship

### Priority 1: Complete Phase 2
- [ ] `create_tests` tool - Generate pytest scaffolds

### Priority 2: Enhanced Intelligence
- [ ] Pattern auto-selection based on analysis
- [ ] Context routing (load only relevant patterns)
- [ ] Bundle optimization suggestions

### Priority 3: Production Features
- [ ] Bundle deployment tool
- [ ] Migration tool (existing jobs → bundles)
- [ ] Bundle diff/comparison tool

## 💡 Quick Tips

### For Faster Iteration
1. **Test locally first** - Use `python main.py` for Claude Code CLI
2. **Skip create_tests** - Focus on core DAB generation first
3. **Use existing patterns** - 5 patterns cover 90% of use cases
4. **Leverage Claude** - Let Claude handle YAML generation complexity

### Common Issues & Fixes
| Issue | Fix |
|-------|-----|
| FastMCP import error | Use miniconda Python: `/Users/alex.miller/miniconda3/bin/python` |
| OAuth redirect | All Databricks Apps endpoints need Bearer token |
| Context too large | Progressive loading - only load relevant patterns |

## 📊 Success Metrics
- **Response time**: < 3 seconds for analysis
- **Bundle generation**: < 10 seconds with context
- **Validation score**: Target 80+ for production bundles
- **Tool count**: 15 operational (14 if skipping create_tests)

## 🔗 Key Files
- **Entry points**: `server/main.py` (CLI), `server/app.py` (HTTP)
- **Tools**: `server/tools.py` (Phase 1), `server/tools_dab.py` (Phase 2)
- **Services**: `services/analysis_service.py`, `services/validation_service.py`
- **Tests**: `tests/test_*.py` (if you need them)

---
*Keep shipping. Context is embedded. Claude handles complexity. Focus on user value.*