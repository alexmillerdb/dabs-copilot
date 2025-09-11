# Creating a Custom MCP Server on Databricks Apps

This comprehensive guide provides step-by-step instructions for creating, configuring, and deploying a custom MCP (Model Control Plane) server using Databricks Apps. It includes sample code, configuration files, best practices, deployment steps, local development tips, and troubleshooting resources.

---

## 1\. Prerequisites

- Databricks CLI installed and configured (workspace authentication set up)  
- Python (supported version) installed locally  
- **Optional**: [uv](https://github.com/astral-sh/uv) (modern Python package manager) for dependency management

---

## 2\. Initialize Your Project

Create a new directory and set up a Python virtual environment:

```shell
mkdir my-mcp-server
cd my-mcp-server
python -m venv .venv
source .venv/bin/activate
```

---

## 3\. Add Dependencies

List required dependencies in `requirements.txt` (e.g., FastAPI, Uvicorn):

```
# requirements.txt
fastapi
uvicorn
# Add any additional MCP dependencies here
```

If you use `uv`, add it and install all packages:

```shell
uv pip install -r requirements.txt
```

---

## 4\. Create Your MCP Server

Example server using FastAPI:

```py
# custom_server/app.py
from fastapi import FastAPI

app = FastAPI()

@app.get("/mcp/")
async def root():
return {"message": "MCP server is running!"}
```

Modify the `/mcp/` route and logic to implement your server functionality as needed.

---

## 5\. Define App Entry Point

Create an `app.yaml` file specifying your app's start command:

```
# app.yaml
command: ["uvicorn", "custom_server.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

*Note: Default port for Databricks Apps is 8000\. Override as needed using `app.yaml` or environment variables.*

---

## 6\. Local Development and Hot Reload

Run your server locally for development:

```shell
uvicorn custom_server.app:app --reload
```

If using `uv`, sync environments as needed:

```shell
uv sync
```

---

## 7\. Authenticate to Databricks

Log in for workspace authentication:

```shell
databricks auth login --host https://<your-workspace-hostname>
# Optionally specify a profile with -p <profile-name>
```

---

## 8\. Create Your Databricks App

Create an app in your Databricks workspace:

```shell
databricks apps create mcp-my-custom-server
```

(Record or remember your app name.)

---

## 9\. Upload Your Code to the Databricks Workspace

Sync your project directory to your user workspace directory:

```shell
DATABRICKS_USERNAME=$(databricks current-user me | jq -r .userName)
databricks sync . "/Users/$DATABRICKS_USERNAME/mcp-my-custom-server"
```

---

## 10\. Deploy MCP Server with Databricks Apps

Deploy the app with the uploaded source code:

```shell
databricks apps deploy mcp-my-custom-server --source-code-path "/Workspace/Users/$DATABRICKS_USERNAME/mcp-my-custom-server"
```

---

## 11\. Alternative: Deploy Using Bundles

If using [Databricks Bundles](https://docs.databricks.com/en/dev-tools/bundles/index.html) and `uv`:

```
# app.yaml
command: ["uvicorn", "custom_server.app:app"]
```

Then:

```shell
uv build --wheel
databricks bundle deploy
databricks bundle run mcp-my-custom-server
```

---

## 12\. Connect to Your Custom MCP Server

The API endpoint format:

```
https://your-app-url.databricksapps.com/mcp-server/mcp
```

*The MCP server is mounted at `/mcp-server` and serves the MCP protocol at the `/mcp` subpath using streamable HTTP transport for Databricks Apps compatibility.*

**Authentication:** Use the Bearer token from your Databricks profile.

```shell
databricks auth token -p <your-profile>
```

**Python Example (list server tools):**

```py
from databricks_mcp import DatabricksOAuthClientProvider
from databricks.sdk import WorkspaceClient
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client

databricks_cli_profile = "DEFAULT"
workspace_client = WorkspaceClient(profile=databricks_cli_profile)
mcp_server_url = "https://your-app-url.databricksapps.com/mcp-server/mcp"

async def test_connection_to_server():
async with streamablehttp_client(
mcp_server_url,
auth=DatabricksOAuthClientProvider(workspace_client)
) as (read_stream, write_stream, _), ClientSession(read_stream, write_stream) as session:
tools = await session.list_tools()
print(f"Available tools: {[tool.name for tool in tools.tools]}")
```

---

## 13\. Local Development Cycle

- Use VS Code or your favorite IDE for edit/reload cycles.  
- To retrieve the latest workspace code locally:

```shell
databricks workspace export-dir /Workspace/Users/<your-username>/mcp-my-custom-server ./local-folder
```

---

## Appendix: Troubleshooting and Tips

- View standard output/error logs via the Logs tab in the app details UI or at `<appurl>/logz`.  
- If the app fails, check logs, verify it works locally, and redeploy.  
- Only Python servers are currently supported (Node.js/server-side JS not supported).  
- Ensure workspace networking is open if your app accesses external services (use Secret Manager for credentials).
