# DABs Copilot CLI Implementation Plan

## Overview

Transform the existing `DABsAgent` into a pip-installable CLI tool (`dabs-copilot`) with both one-shot commands and interactive REPL mode.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Subagent Usage | Full orchestration | Keep 6 subagents for thorough DAB generation |
| Progress Display | `--verbose` flag | Clean by default, detailed when needed |
| Project Config | Full pyproject.toml | Modern standard, proper packaging |
| Missing API Key | Error immediately | Clear failure, no interactive prompts |
| LLM Backend | LiteLLM proxy support | Enable Databricks Foundation Model APIs |

## Directory Structure

```
src/dabs_copilot/
├── __init__.py              # Update exports
├── agent.py                 # Existing DABsAgent (unchanged)
├── tools/
│   └── sdk_tools.py         # Existing 17 custom tools
└── cli/                     # NEW - CLI module
    ├── __init__.py          # Version and exports
    ├── main.py              # Typer app entry point
    ├── commands/
    │   ├── __init__.py
    │   ├── generate.py      # dabs-copilot generate
    │   ├── validate.py      # dabs-copilot validate
    │   ├── deploy.py        # dabs-copilot deploy
    │   └── chat.py          # dabs-copilot chat (REPL)
    ├── auth.py              # Authentication resolution
    ├── output.py            # Rich console streaming/display
    └── utils.py             # File ops, prompts, helpers
```

## Commands

### `dabs-copilot generate SOURCE`
One-shot bundle generation from job ID or workspace path.

```
Arguments:
  SOURCE              Job ID (e.g., "12345") or workspace path

Options:
  -o, --output PATH   Output directory [default: ./]
  -n, --name TEXT     Bundle name (auto-generated if not provided)
  -t, --target TEXT   Target environment [default: dev]
  -y, --yes           Skip confirmation prompts
  -p, --profile TEXT  Databricks CLI profile
  --host TEXT         Databricks workspace URL
  -v, --verbose       Enable verbose output
```

### `dabs-copilot validate [BUNDLE_PATH]`
Validate existing bundle configuration.

```
Arguments:
  BUNDLE_PATH         Path to bundle directory [default: ./]

Options:
  -t, --target TEXT   Target environment [default: dev]
  --json              Output as JSON
```

### `dabs-copilot deploy [BUNDLE_PATH]`
Deploy bundle to target environment.

```
Arguments:
  BUNDLE_PATH         Path to bundle directory [default: ./]

Options:
  -t, --target TEXT   Target environment [default: dev]
  --run               Run job after successful deploy
  -y, --yes           Skip confirmation
```

### `dabs-copilot chat [INITIAL_MESSAGE]`
Interactive REPL for conversational bundle generation.

```
Arguments:
  INITIAL_MESSAGE     Optional message to start conversation

Built-in commands:
  /quit, /exit        Exit the session
  /reset              Start new conversation
  /tools              List available tools
  /help               Show help
  /save PATH          Save last generated YAML
```

## Authentication Flow

Priority order (first match wins):
1. CLI flags (`--profile`, `--host`)
2. Environment variables (`DATABRICKS_HOST`, `DATABRICKS_TOKEN`, `DATABRICKS_CONFIG_PROFILE`)
3. Auto-detect in Databricks workspace runtime
4. Default profile in `~/.databrickscfg`

**LLM Backend** (choose one):
- Anthropic direct: `ANTHROPIC_API_KEY` environment variable
- LiteLLM proxy: `LITELLM_API_BASE` + `LITELLM_API_KEY` (for Databricks FMAPI)

The CLI will auto-detect which backend to use based on environment variables.

## Usage Examples

```bash
# Install
pip install -e .

# Check installation
dabs-copilot --help

# Generate from job
dabs-copilot generate 12345 --name my-etl --output ./bundles/

# Generate from workspace path
dabs-copilot generate "/Workspace/Users/alex/notebooks" -n data-pipeline

# Validate
dabs-copilot validate ./bundles/my-etl/

# Deploy
dabs-copilot deploy ./bundles/my-etl/ -t dev

# Interactive chat
dabs-copilot chat
dabs-copilot chat "Help me create a bundle for job 12345"
```
