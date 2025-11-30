# DABs Copilot Agent - Skills & Subagents Integration

## Overview

This document describes how skills and subagents are integrated into `agent.py` using the Claude Agent SDK.

---

## SDK Features Used

### Skills

Skills are loaded from `.claude/skills/` and require:
- `setting_sources=["project"]` - Load from project's `.claude/` directory
- `cwd` - Project root path containing `.claude/skills/`
- `"Skill"` in `allowed_tools`

### Subagents

Subagents are defined via `AgentDefinition` with:
- `description` - When to invoke this agent
- `prompt` - System prompt for the agent
- `tools` - Allowed tools (subset of main agent's tools)
- `model` - Model to use (haiku/sonnet/opus)

---

## Architecture

```
agent.py
├── ALLOWED_TOOLS       # MCP tools + Skill + Task + file tools
├── DABS_AGENTS         # 6 specialized subagents
├── get_project_root()  # Find .claude directory
├── DABsAgent           # Interactive multi-turn agent
└── generate_bundle()   # One-shot convenience function
```

### Subagents

| Agent | Model | Purpose |
|-------|-------|---------|
| `dab-orchestrator` | sonnet | Coordinates bundle generation workflow |
| `dab-discovery` | haiku | Discovers jobs, notebooks from workspace |
| `dab-analyzer` | haiku | Analyzes code patterns and dependencies |
| `dab-generator` | sonnet | Generates databricks.yml configuration |
| `dab-validator` | haiku | Validates bundles and suggests fixes |
| `dab-deployer` | haiku | Uploads and deploys bundles |

### Skill

| Skill | Purpose |
|-------|---------|
| `databricks-asset-bundles` | DAB patterns, best practices, YAML templates |

---

## Configuration

### ClaudeAgentOptions

```python
ClaudeAgentOptions(
    allowed_tools=ALLOWED_TOOLS,
    mcp_servers=mcp_config,
    system_prompt={"type": "preset", "preset": "claude_code", "append": DABS_SYSTEM_PROMPT},
    permission_mode="default",
    cwd=get_project_root(),           # For skill loading
    setting_sources=["project"],       # Load .claude/skills/
    agents=DABS_AGENTS,               # Subagent definitions
)
```

---

## Usage

### Interactive Multi-Turn

```python
async with DABsAgent() as agent:
    async for msg in agent.chat("Generate a bundle from job 123"):
        print(msg)
    async for msg in agent.chat("Now deploy it"):
        print(msg)
```

### One-Shot

```python
async for msg in generate_bundle("Generate bundle from job 123"):
    print(msg)
```

---

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `DABS_MCP_SERVER_URL` | MCP server URL (SSE mode) | None (uses subprocess) |
| `DABS_MCP_COMMAND` | MCP subprocess command | `python` |
| `DABS_MCP_ARGS` | MCP subprocess args | `-m,mcp_server` |
