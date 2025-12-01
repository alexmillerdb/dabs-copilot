# DABs Copilot

AI-powered CLI for generating, validating, and deploying Databricks Asset Bundles.

## Installation

```bash
pip install -e .
```

Requires:
- Python 3.10+
- [Databricks CLI](https://docs.databricks.com/dev-tools/cli/index.html) (`databricks auth login`)
- `ANTHROPIC_API_KEY` environment variable (or LiteLLM proxy)

## Quick Start

```bash
# Check authentication
dabs-copilot --check-auth

# Generate bundle from a job
dabs-copilot generate 12345 --name my-etl

# Generate from workspace notebooks
dabs-copilot generate "/Workspace/Users/me/notebooks" -n my-pipeline

# Validate bundle
dabs-copilot validate ./my-etl/

# Deploy to dev
dabs-copilot deploy ./my-etl/ -t dev

# Interactive chat mode
dabs-copilot chat
```

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      dabs-copilot CLI                        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐      │
│  │  generate   │    │  validate   │    │   deploy    │      │
│  │  (one-shot) │    │  (bundle)   │    │  (bundle)   │      │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘      │
│         │                  │                  │              │
│         └────────┬─────────┴─────────┬────────┘              │
│                  ▼                   ▼                       │
│         ┌─────────────────┐  ┌─────────────────┐            │
│         │   DABsAgent     │  │  Databricks CLI │            │
│         │  (Claude SDK)   │  │                 │            │
│         └────────┬────────┘  └─────────────────┘            │
│                  │                                           │
│    ┌─────────────┼─────────────┐                            │
│    ▼             ▼             ▼                            │
│ ┌──────┐   ┌──────────┐   ┌──────────┐                      │
│ │Disco-│   │ Analyzer │   │Generator │  ... 6 subagents    │
│ │ very │   │          │   │          │                      │
│ └──────┘   └──────────┘   └──────────┘                      │
│                  │                                           │
│                  ▼                                           │
│         ┌─────────────────┐                                 │
│         │  17 Databricks  │                                 │
│         │     Tools       │                                 │
│         │  (SDK + MCP)    │                                 │
│         └─────────────────┘                                 │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Components

- **CLI** (`dabs-copilot`): Typer-based commands for generate, validate, deploy, chat
- **DABsAgent**: Claude Agent SDK orchestrator with 6 specialized subagents
- **Tools**: 17 Databricks operations (jobs, notebooks, clusters, bundles)
- **Subagents**: Discovery → Analysis → Generation → Validation → Deployment

## Commands

### `dabs-copilot generate SOURCE`

Generate a bundle from a job ID or workspace path.

```bash
dabs-copilot generate 12345 --name my-bundle --output ./bundles/
dabs-copilot generate "/Workspace/Users/me/etl" -n data-pipeline -t dev
```

| Option | Description |
|--------|-------------|
| `-o, --output` | Output directory (default: current) |
| `-n, --name` | Bundle name (auto-generated if omitted) |
| `-t, --target` | Target environment (default: dev) |
| `-y, --yes` | Skip confirmation prompts |

### `dabs-copilot validate [BUNDLE_PATH]`

Validate bundle configuration using Databricks CLI.

```bash
dabs-copilot validate ./my-bundle/
dabs-copilot validate -t prod --json
```

### `dabs-copilot deploy [BUNDLE_PATH]`

Deploy bundle to Databricks workspace.

```bash
dabs-copilot deploy ./my-bundle/ -t dev
dabs-copilot deploy -t prod --run  # Deploy and run job
```

### `dabs-copilot chat`

Interactive REPL for conversational bundle generation.

```bash
dabs-copilot chat
dabs-copilot chat "Help me create a bundle for job 12345"
```

**Chat commands:**
- `/quit` - Exit session
- `/reset` - Start new conversation
- `/tools` - List available tools
- `/save PATH` - Save generated YAML

## Authentication

### Databricks

Configure via any of:
```bash
# CLI profile (recommended)
export DATABRICKS_CONFIG_PROFILE=my-profile

# Direct credentials
export DATABRICKS_HOST=https://my-workspace.cloud.databricks.com
export DATABRICKS_TOKEN=dapi...

# Or use: databricks auth login
```

### LLM Backend

```bash
# Option 1: Anthropic direct
export ANTHROPIC_API_KEY=sk-ant-...

# Option 2: LiteLLM proxy (for Databricks FMAPI)
export LITELLM_API_BASE=http://localhost:4000
```

#### Using Databricks Foundation Model API via LiteLLM

To use Claude models hosted on Databricks instead of Anthropic directly:

1. Configure environment variables in `.env`:
```bash
DATABRICKS_API_BASE=https://your-workspace.cloud.databricks.com/serving-endpoints
DATABRICKS_API_KEY=dapi...
LITELLM_API_BASE=http://localhost:4000
```

2. Configure `litellm_config.yaml` to route model requests to Databricks:
```yaml
model_list:
  - model_name: claude-sonnet-4-20250514
    litellm_params:
      model: databricks/databricks-claude-sonnet-4-5
      api_key: os.environ/DATABRICKS_API_KEY
      api_base: os.environ/DATABRICKS_API_BASE
```

3. Start the LiteLLM proxy:
```bash
litellm --config litellm_config.yaml
```

4. Run dabs-copilot commands as usual - requests route through LiteLLM to Databricks.

## Project Structure

```
src/dabs_copilot/
├── cli/                    # CLI module
│   ├── main.py             # Entry point
│   ├── auth.py             # Authentication
│   ├── output.py           # Rich console output
│   └── commands/           # generate, validate, deploy, chat
├── agent.py                # DABsAgent (Claude SDK)
└── tools/sdk_tools.py      # 17 Databricks tools
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/ && ruff check src/ --fix
```

## Examples

### Generate from Job

```bash
$ dabs-copilot generate 662067900958232 --name sales-etl

Source type: job
Bundle name: sales-etl
Output: ./sales-etl

Generating bundle...

✓ Written: ./sales-etl/databricks.yml

Bundle generated successfully!

Next steps:
  1. Review: ./sales-etl/databricks.yml
  2. Validate: dabs-copilot validate ./sales-etl
  3. Deploy: dabs-copilot deploy ./sales-etl -t dev
```

### Interactive Chat

```bash
$ dabs-copilot chat

╭─ Welcome ─────────────────────────────────────────────╮
│ DABs Copilot - Conversational AI for DABs             │
│                                                       │
│ Commands:                                             │
│   /quit, /exit  - Exit the session                    │
│   /reset        - Start new conversation              │
│   /tools        - List available tools                │
│   /save PATH    - Save last generated YAML            │
╰───────────────────────────────────────────────────────╯

You: Generate a bundle for my ML training job 12345

Agent: I'll analyze job 12345 and generate a bundle...
  → get_job
  → analyze_notebook
  → generate_bundle

Here's your bundle configuration:
...
```

## License

Apache-2.0
