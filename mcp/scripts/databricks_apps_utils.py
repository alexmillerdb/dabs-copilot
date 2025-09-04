#!/usr/bin/env python3
"""
Databricks Apps utilities for MCP server deployment and testing
"""

import os
import json
import subprocess
import asyncio
import logging
from typing import Optional, Dict, Any
from databricks.sdk import WorkspaceClient
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client

logger = logging.getLogger(__name__)

def find_databricks_cli() -> str:
    """Find the best available Databricks CLI in a portable way"""
    
    # Try different locations in order of preference
    cli_paths = [
        # Check if it's in PATH (most portable)
        "databricks",
        # Common installation locations
        "/usr/local/bin/databricks",
        "/opt/homebrew/bin/databricks",
        "~/.local/bin/databricks",
        # Virtual environment (if we're in one)
        os.path.join(os.path.dirname(os.path.dirname(__file__)), ".venv", "bin", "databricks")
    ]
    
    for cli_path in cli_paths:
        expanded_path = os.path.expanduser(cli_path)
        
        # For 'databricks' (PATH lookup), test if it exists and is v2+
        if cli_path == "databricks":
            try:
                result = subprocess.run([cli_path, "--version"], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0 and "v0." in result.stdout and not "v0.1" in result.stdout:
                    # This is the new CLI (v0.2+)
                    logger.info(f"Found Databricks CLI v2+ in PATH")
                    return cli_path
            except (subprocess.SubprocessError, FileNotFoundError):
                continue
        else:
            # For specific paths, just check if file exists
            if os.path.isfile(expanded_path):
                logger.info(f"Found Databricks CLI at: {expanded_path}")
                return expanded_path
    
    # Fallback: assume 'databricks' is available and hope for the best
    logger.warning("Could not find Databricks CLI v2+, using 'databricks' from PATH")
    return "databricks"

class DatabricksAppsManager:
    """Manage Databricks Apps deployment and testing"""
    
    def __init__(self, app_name: str = "databricks-mcp-server", profile: Optional[str] = None):
        self.app_name = app_name
        self.profile = profile or os.getenv("DATABRICKS_CONFIG_PROFILE", "DEFAULT")
        self.databricks_cmd = find_databricks_cli()
        self.workspace_client = WorkspaceClient(profile=self.profile)
        logger.info(f"Using Databricks CLI: {self.databricks_cmd}")
    
    def get_app_url(self) -> Optional[str]:
        """Dynamically get the Databricks Apps URL"""
        try:
            result = subprocess.run([
                self.databricks_cmd, "apps", "get", self.app_name, 
                "--profile", self.profile, "--output", "json"
            ], capture_output=True, text=True, check=True)
            
            app_info = json.loads(result.stdout)
            url = app_info.get("url")
            
            if url:
                logger.info(f"Found app URL: {url}")
                return url
            else:
                logger.error("No URL found in app info")
                return None
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get app info: {e.stderr}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse app info JSON: {e}")
            return None
    
    def get_mcp_endpoint_url(self) -> Optional[str]:
        """Get the full MCP endpoint URL with /mcp/ path"""
        app_url = self.get_app_url()
        if app_url:
            # Ensure URL ends with /mcp/ for MCP compatibility
            if not app_url.endswith('/'):
                app_url += '/'
            return f"{app_url}mcp/"
        return None
    
    def get_auth_token(self) -> str:
        """Get Databricks authentication token"""
        try:
            result = subprocess.run([
                self.databricks_cmd, "auth", "token", 
                "--profile", self.profile
            ], capture_output=True, text=True, check=True)
            
            return result.stdout.strip()
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get auth token: {e.stderr}")
            raise
    
    async def test_mcp_connection(self) -> Dict[str, Any]:
        """Test MCP server connection using streamable HTTP"""
        mcp_url = self.get_mcp_endpoint_url()
        if not mcp_url:
            return {"success": False, "error": "Could not get MCP endpoint URL"}
        
        try:
            # Use Databricks OAuth provider for authentication
            from databricks_mcp import DatabricksOAuthClientProvider
            auth_provider = DatabricksOAuthClientProvider(self.workspace_client)
            
            logger.info(f"Testing MCP connection to: {mcp_url}")
            
            async with streamablehttp_client(
                mcp_url, 
                auth=auth_provider
            ) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    # Test basic connection
                    tools = await session.list_tools()
                    tool_names = [tool.name for tool in tools.tools]
                    
                    logger.info(f"Successfully connected! Available tools: {tool_names}")
                    
                    return {
                        "success": True,
                        "mcp_url": mcp_url,
                        "tools_count": len(tool_names),
                        "tools": tool_names
                    }
                    
        except Exception as e:
            logger.error(f"MCP connection test failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "mcp_url": mcp_url
            }
    
    async def test_mcp_tool(self, tool_name: str, args: Dict[str, Any] = None) -> Dict[str, Any]:
        """Test a specific MCP tool"""
        mcp_url = self.get_mcp_endpoint_url()
        if not mcp_url:
            return {"success": False, "error": "Could not get MCP endpoint URL"}
        
        try:
            from databricks_mcp import DatabricksOAuthClientProvider
            auth_provider = DatabricksOAuthClientProvider(self.workspace_client)
            
            async with streamablehttp_client(
                mcp_url,
                auth=auth_provider
            ) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    # Call the specific tool
                    result = await session.call_tool(tool_name, args or {})
                    
                    return {
                        "success": True,
                        "tool": tool_name,
                        "result": result.content[0].text if result.content else None
                    }
                    
        except Exception as e:
            logger.error(f"Tool test failed for {tool_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "tool": tool_name
            }
    
    def deploy_app(self) -> bool:
        """Deploy the MCP server to Databricks Apps"""
        try:
            # Get current user for workspace path
            username_result = subprocess.run([
                self.databricks_cmd, "current-user", "me", 
                "--profile", self.profile, "--output", "json"
            ], capture_output=True, text=True, check=True)
            
            user_info = json.loads(username_result.stdout)
            username = user_info.get("userName")
            source_path = f"/Users/{username}/{self.app_name}"
            
            logger.info(f"Deploying {self.app_name} to Databricks Apps...")
            
            # Create app if it doesn't exist
            try:
                subprocess.run([
                    self.databricks_cmd, "apps", "get", self.app_name, "--profile", self.profile
                ], capture_output=True, check=True)
                logger.info(f"App {self.app_name} already exists")
            except subprocess.CalledProcessError:
                logger.info(f"Creating new app: {self.app_name}")
                subprocess.run([
                    self.databricks_cmd, "apps", "create", self.app_name, "--profile", self.profile
                ], check=True)
            
            # Sync code to workspace
            logger.info(f"Syncing code to workspace path: {source_path}")
            subprocess.run([
                self.databricks_cmd, "sync", ".", source_path, "--profile", self.profile
            ], check=True)
            
            # Deploy app
            logger.info("Deploying app...")
            subprocess.run([
                self.databricks_cmd, "apps", "deploy", self.app_name,
                "--source-code-path", f"/Workspace{source_path}",
                "--profile", self.profile
            ], check=True)
            
            # Get and display app URL
            app_url = self.get_app_url()
            mcp_url = self.get_mcp_endpoint_url()
            
            logger.info("✅ Deployment successful!")
            logger.info(f"🌐 App URL: {app_url}")
            logger.info(f"🔗 MCP Endpoint: {mcp_url}")
            
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Deployment failed: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Unexpected deployment error: {e}")
            return False


async def main():
    """CLI interface for Databricks Apps management"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Databricks Apps MCP Server Manager")
    parser.add_argument("command", choices=["deploy", "test", "url", "test-tool"], 
                       help="Command to execute")
    parser.add_argument("--app-name", default="databricks-mcp-server", 
                       help="Databricks app name")
    parser.add_argument("--profile", help="Databricks CLI profile")
    parser.add_argument("--tool", help="Tool name for test-tool command")
    parser.add_argument("--args", help="JSON args for tool test")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(levelname)s - %(message)s')
    
    manager = DatabricksAppsManager(args.app_name, args.profile)
    
    if args.command == "deploy":
        success = manager.deploy_app()
        exit(0 if success else 1)
        
    elif args.command == "url":
        app_url = manager.get_app_url()
        mcp_url = manager.get_mcp_endpoint_url()
        print(f"App URL: {app_url}")
        print(f"MCP Endpoint: {mcp_url}")
        
    elif args.command == "test":
        result = await manager.test_mcp_connection()
        print(json.dumps(result, indent=2))
        exit(0 if result["success"] else 1)
        
    elif args.command == "test-tool":
        if not args.tool:
            print("--tool argument required for test-tool command")
            exit(1)
        
        tool_args = {}
        if args.args:
            try:
                tool_args = json.loads(args.args)
            except json.JSONDecodeError:
                print("Invalid JSON in --args")
                exit(1)
        
        result = await manager.test_mcp_tool(args.tool, tool_args)
        print(json.dumps(result, indent=2))
        exit(0 if result["success"] else 1)


if __name__ == "__main__":
    asyncio.run(main())
