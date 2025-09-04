# Host Custom MCP Servers Using Databricks Apps

> **Note**: This feature is currently in Beta.

## Overview

You can host your own custom or third-party MCP servers as Databricks apps. This is useful if you already have MCP servers you want to deploy and share with others in your organization or if you want to run a third-party MCP server as a source of tools.

An MCP server hosted as a Databricks app must implement an HTTP-compatible transport, such as the streamable HTTP transport.

## Requirements

- MCP server must implement an HTTP-compatible transport (like streamable HTTP transport)
- Databricks workspace with Apps enabled
- OAuth authentication configured

## Setup Instructions

### Step 1: Environment Preparation

Authenticate to your workspace using OAuth:

```bash
databricks auth login --host https://<your-workspace-hostname>
```

### Step 2: Configure Your MCP Server

#### Add Dependencies

Create a `requirements.txt` file in your server's root directory and specify Python dependencies for your server.

**Note**: Python MCP servers often use `uv` for package management. If you use `uv`, add `uv` and it will handle installing additional dependencies.

Example `requirements.txt`:
```txt
uv
# Add other dependencies as needed
```

#### Configure app.yaml

Add an `app.yaml` file specifying the CLI command to run your server.

Example `app.yaml`:
```yaml
command: [
    'uv',
    'run',
    'your-server-name',
    # Optional additional parameters
]
```

**Important**: By default, Databricks apps listen on port 8000. If your server listens on a different port, set it using an environment variable override in the `app.yaml` file.

### Step 3: Deploy as Databricks App

1. Create the Databricks app:
```bash
databricks apps create mcp-my-custom-server
```

2. Upload your source code:
```bash
# Get your Databricks username
DATABRICKS_USERNAME=$(databricks current-user me | jq -r .userName)

# Sync your local code to the workspace
databricks sync . "/Users/$DATABRICKS_USERNAME/mcp-my-custom-server"
```

3. Deploy the app:
```bash
databricks apps deploy mcp-my-custom-server \
    --source-code-path "/Workspace/Users/$DATABRICKS_USERNAME/mcp-my-custom-server"
```

## Connection Methods

Custom MCP servers support multiple connection methods:

1. **Local environment connections** - Connect from your local development environment
2. **Notebook connections via service principal** - Connect from Databricks notebooks using service principal authentication
3. **Agent code connections** - Connect from agent code running on behalf of a user or service principal

## Connection Example

Here's how to connect to and test your custom MCP server:

```python
async def test_connection_to_server():
    async with streamablehttp_client(
        f"{mcp_server_url}", 
        auth=DatabricksOAuthClientProviderfrom(workspace_client)
    ) as (read_stream, write_stream, _), ClientSession(
        read_stream, write_stream
    ) as session:
        # List available tools
        tools = await session.list_tools()
        print(f"Available tools: {[tool.name for tool in tools.tools]}")
```

## Authentication Options

Custom MCP servers support various authentication methods:

- **OAuth** - Recommended for user authentication
- **Service Principal** - For automated workflows and CI/CD
- **Model Serving User Credentials** - For model serving endpoints

## Example Notebooks

Databricks provides example notebooks for implementing MCP tool-calling agents:

- **LangGraph MCP tool-calling agent** - Example using LangGraph framework
- **OpenAI MCP tool-calling agent** - Example using OpenAI's agent framework

## Best Practices

1. **Security**: Always use proper authentication and never hardcode credentials
2. **Port Configuration**: Ensure your server listens on the correct port (default 8000)
3. **Dependencies**: Keep your `requirements.txt` up to date
4. **Testing**: Test your MCP server locally before deploying to Databricks
5. **Monitoring**: Use Databricks app logs to monitor server health and debug issues

## Pricing

Custom MCP servers are subject to Databricks Apps pricing. Check your workspace billing settings for details.

## Additional Resources

- [Custom MCP server repository](https://github.com/databrickslabs/mcp/tree/master/examples/custom-server)
- [Model Context Protocol Specification](https://modelcontextprotocol.io)
- [Databricks Apps Documentation](https://docs.databricks.com/apps/index.html)

## Troubleshooting

### Common Issues

1. **Port conflicts**: If your server isn't accessible, check that it's listening on the correct port
2. **Authentication failures**: Ensure OAuth is properly configured and tokens are valid
3. **Deployment errors**: Check the app logs using `databricks apps logs <app-name>`
4. **Dependencies missing**: Verify all required packages are in `requirements.txt`

### Getting Help

For issues specific to custom MCP servers on Databricks, refer to:
- Databricks Community Forums
- Official Databricks Support (for customers with support plans)
- MCP Protocol Documentation