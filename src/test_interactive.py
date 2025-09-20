#!/usr/bin/env python3
"""Interactive testing script for IDE"""
import asyncio
from agents.orchestrator import OrchestratorAgent
from config.settings import get_settings

async def test_configuration():
    """Test configuration loading"""
    print("🔧 Testing Configuration")
    print("=" * 40)
    
    try:
        settings = get_settings()
        print(f"✅ Settings loaded successfully")
        print(f"✅ Claude API key: {'Set' if settings.claude_api_key else 'Not set'}")
        print(f"✅ MCP mode: {settings.mcp_mode}")
        print(f"✅ MCP remote URL: {settings.mcp_remote_url}")
        return True
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

async def test_agent_creation():
    """Test agent initialization"""
    print("\n🤖 Testing Agent Creation")
    print("=" * 40)
    
    try:
        agent = OrchestratorAgent()
        print(f"✅ Agent created: {agent.name}")
        print(f"✅ MCP client initialized: {agent.mcp_client is not None}")
        print(f"✅ Settings loaded: {agent.settings is not None}")
        return agent
    except Exception as e:
        print(f"❌ Agent creation error: {e}")
        return None

async def test_agent_commands(agent):
    """Test agent command handling"""
    print("\n📝 Testing Agent Commands")
    print("=" * 40)
    
    test_commands = [
        "help",
        "list jobs",
        "get job 188317192422679", 
        # "generate bundle from job 456",
    ]
    
    results = []
    for cmd in test_commands:
        try:
            print(f"\n🔹 Command: '{cmd}'")
            response = await agent.handle_request(cmd)
            print(f"✅ Response: {response[:100]}{'...' if len(response) > 100 else ''}")
            results.append((cmd, True, response))
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append((cmd, False, str(e)))
    
    return results

async def test_mcp_bridge():
    """Test MCP bridge functionality"""
    print("\n🌉 Testing MCP Bridge")
    print("=" * 40)
    
    try:
        from tools.mcp_client import DatabricksMCPClient
        
        # Test local mode
        client_local = DatabricksMCPClient(mode="local")
        print(f"✅ Local client created: {client_local.use_stdio}")
        
        # Test remote mode  
        client_remote = DatabricksMCPClient(mode="remote")
        print(f"✅ Remote client created: {not client_remote.use_stdio}")
        print(f"✅ Remote URL: {client_remote.base_url}")
        
        # Test method availability
        print(f"✅ Methods available: {hasattr(client_local, 'list_jobs')}")
        
        return True
    except Exception as e:
        print(f"❌ MCP bridge error: {e}")
        return False

async def run_full_test():
    """Run complete test suite"""
    print("🚀 Starting DAB Agent System Tests")
    print("=" * 50)
    
    # Test configuration
    config_ok = await test_configuration()
    if not config_ok:
        print("\n❌ Configuration tests failed. Check your .env file.")
        return
    
    # Test MCP bridge
    mcp_ok = await test_mcp_bridge()
    if not mcp_ok:
        print("\n❌ MCP bridge tests failed.")
        return
    
    # Test agent creation
    agent = await test_agent_creation()
    if not agent:
        print("\n❌ Agent creation failed.")
        return
    
    # Test agent commands
    results = await test_agent_commands(agent)
    
    # Summary
    print("\n📊 Test Summary")
    print("=" * 40)
    success_count = sum(1 for _, success, _ in results if success)
    total_count = len(results)
    print(f"✅ Commands passed: {success_count}/{total_count}")
    
    if success_count == total_count:
        print("🎉 All tests passed! Agent system is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")

if __name__ == "__main__":
    # Run the test suite
    asyncio.run(run_full_test())