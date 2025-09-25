## Sprint Planning — Databricks Apps + Claude Code SDK + Remote MCP

### Goal

- Keep Claude Code SDK for agent orchestration while migrating the MCP server to a remote (Databricks Apps) deployment and running the Streamlit app in Databricks Apps.

### Architecture

- Current (Local):
  - Streamlit App → Claude Code SDK → Local MCP Server → Databricks API

- Target (Databricks Apps):
  - Streamlit App (Databricks Apps) → Claude Code SDK → Remote MCP Server (Databricks Apps) → Databricks API

---

### Revised Migration Strategy

#### Phase 1: MCP Server Connection Update

- Configure Claude Code SDK to use deployed MCP server instead of local
  1) Update `src/api/claude_client.py` to point to remote MCP server URL
  2) Configure authentication (OAuth tokens) for MCP server access
  3) Test connectivity Claude Code SDK → Remote MCP server

Files to modify:
- `src/api/claude_client.py` — update MCP server configuration
- `.env` — add MCP server URL and auth settings

#### Phase 2: Databricks Apps Deployment

- Deploy Streamlit app to Databricks Apps while keeping Claude Code SDK
  1) Create `app.yaml` for Streamlit + Claude Code SDK
  2) Update `requirements.txt` (ensure claude-code-sdk, streamlit, databricks-sdk)
  3) Configure environment: MCP server URL, OAuth tokens
  4) Provide deployment script

New files:
- `src/api/app.yaml` — Databricks Apps configuration
- `src/api/deploy_dab_generator.sh` — Deployment script

#### Phase 3: Integration & Testing

- Validate end-to-end with Claude Code SDK + remote MCP server (in Apps)

---

### Technical Implementation Details

#### Claude client update (key change)

```python
# src/api/claude_client.py — Update MCP server configuration
from pathlib import Path
import os
from claude_code_sdk import ClaudeCodeOptions

def get_databricks_token():
    """Get OAuth token for MCP server authentication"""
    from databricks.sdk import WorkspaceClient
    workspace_client = WorkspaceClient()
    return workspace_client.config.token

def build_chat_options() -> ClaudeCodeOptions:
    project_root = Path(__file__).parent.parent.parent

    # Use deployed MCP server instead of local
    mcp_server_url = os.getenv(
        "DATABRICKS_MCP_SERVER_URL",
        "https://databricks-mcp-server-1444828305810485.aws.databricksapps.com",
    )

    return ClaudeCodeOptions(
        model="claude-sonnet-4-20250514",
        cwd=str(project_root),
        mcp_servers={
            "databricks-mcp": {
                "command": "http_client",  # HTTP instead of subprocess/stdio
                "url": f"{mcp_server_url}/mcp-server/mcp",
                "auth": {
                    "type": "bearer",
                    "token": get_databricks_token(),
                },
            }
        },
        allowed_tools=allowed_tools,  # existing list of MCP tools
        max_turns=10,
        system_prompt=system_prompt,
    )
```

#### Databricks Apps configuration for Streamlit

```yaml
# src/api/app.yaml
command: [
  "streamlit", "run", "streamlit_app_enhanced.py",
  "--server.port", "8000", "--server.address", "0.0.0.0"
]
```

#### Environment configuration

```env
# .env additions
DATABRICKS_MCP_SERVER_URL=https://databricks-mcp-server-1444828305810485.aws.databricksapps.com
DATABRICKS_WORKSPACE_URL=https://your-workspace.cloud.databricks.com
```

---

### Architecture Benefits (Corrected)

Why keep Claude Code SDK:
1) Agent intelligence: natural language + tool orchestration
2) Conversation management: streaming, turn control, loop prevention
3) Tool selection: chooses appropriate MCP tools from intent
4) Error handling: retries and recovery patterns
5) State management: conversation context and memory

What changes:
1) MCP server location → remote HTTP endpoint
2) Authentication → OAuth tokens instead of local profiles
3) Deployment → Streamlit app runs in Databricks Apps
4) Network → HTTP calls to MCP server vs stdio

---

### Implementation Priority (Revised)

High priority:
1) Update Claude Code SDK configuration to remote MCP server
2) Test remote MCP connectivity
3) Deploy Streamlit app to Databricks Apps
4) Configure OAuth token flow for MCP

Medium priority:
1) Enhanced state management in Apps environment
2) Error handling for network/auth issues
3) File generation/handling for bundles in Apps

Low priority:
1) Performance optimization (HTTP connection pooling)
2) Monitoring (logging/metrics)
3) UI enhancements (Apps-specific styling)

---

### Key Advantage

- Keep the intelligence in Claude Code SDK; just point it to the remote MCP server, supply proper authentication, and host the Streamlit app in Databricks Apps for a fully managed, scalable deployment.


