#!/usr/bin/env python3
"""
Integration test for MCP server with all tools
Tests that both tools.py and tools_dab.py are properly integrated
"""

import sys
import os

# Change to server directory for proper imports
original_dir = os.getcwd()
server_dir = os.path.join(os.path.dirname(__file__), 'server')
os.chdir(server_dir)
sys.path.insert(0, '.')

def test_tool_registration():
    """Test that all tools are properly registered"""
    print("=" * 60)
    print("Testing MCP Server Tool Registration")
    print("=" * 60)
    
    # Import the main module which should load all tools
    from tools import mcp
    
    # This should trigger the import of DAB tools
    import tools_dab
    
    # Get all registered tools
    tools = list(mcp._tool_manager._tools.keys())
    
    print(f"\n✅ Total tools registered: {len(tools)}")
    
    # Expected tools from tools.py
    core_tools = [
        'health',
        'list_jobs', 
        'get_job',
        'run_job',
        'list_notebooks',
        'export_notebook',
        'execute_dbsql',
        'list_warehouses',
        'list_dbfs_files',
        'generate_bundle_from_job'
    ]
    
    # Expected tools from tools_dab.py
    dab_tools = [
        'analyze_notebook',
        'generate_bundle',
        'validate_bundle', 
        'create_tests'
    ]
    
    print("\n📦 Core Tools (tools.py):")
    for tool in core_tools:
        if tool in tools:
            print(f"  ✅ {tool}")
        else:
            print(f"  ❌ {tool} - MISSING!")
    
    print("\n🔧 DAB Generation Tools (tools_dab.py):")
    for tool in dab_tools:
        if tool in tools:
            print(f"  ✅ {tool}")
        else:
            print(f"  ❌ {tool} - MISSING!")
    
    # Check for unexpected tools
    expected_tools = set(core_tools + dab_tools)
    actual_tools = set(tools)
    unexpected = actual_tools - expected_tools
    
    if unexpected:
        print(f"\n⚠️  Unexpected tools found: {unexpected}")
    
    return len(tools) == 14

def test_workspace_client_sharing():
    """Test that workspace client is properly shared between modules"""
    print("\n" + "=" * 60)
    print("Testing Workspace Client Sharing")
    print("=" * 60)
    
    from tools import workspace_client as tools_client
    from tools_dab import workspace_client as dab_client
    
    print(f"\n✅ Tools workspace client initialized: {tools_client is not None}")
    print(f"✅ DAB workspace client initialized: {dab_client is not None}")
    print(f"✅ Clients are the same instance: {tools_client is dab_client}")
    
    if tools_client:
        try:
            # Try to get the workspace URL
            url = tools_client.config.host
            print(f"✅ Connected to workspace: {url}")
        except:
            print("⚠️  Could not retrieve workspace URL")
    
    return tools_client is not None and tools_client is dab_client

def test_mcp_instance_sharing():
    """Test that MCP instance is properly shared"""
    print("\n" + "=" * 60)
    print("Testing MCP Instance Sharing")
    print("=" * 60)
    
    from tools import mcp as tools_mcp
    from tools_dab import mcp as dab_mcp
    
    print(f"\n✅ MCP instances are the same: {tools_mcp is dab_mcp}")
    
    return tools_mcp is dab_mcp

def test_response_helpers():
    """Test that response helper functions work"""
    print("\n" + "=" * 60)
    print("Testing Response Helper Functions")
    print("=" * 60)
    
    from tools import create_success_response, create_error_response
    
    # Test success response
    success = create_success_response({"test": "data"})
    print(f"\n✅ Success response created: {len(success)} chars")
    
    # Test error response
    error = create_error_response("Test error")
    print(f"✅ Error response created: {len(error)} chars")
    
    import json
    success_data = json.loads(success)
    error_data = json.loads(error)
    
    print(f"✅ Success response valid JSON: {success_data['success'] == True}")
    print(f"✅ Error response valid JSON: {error_data['success'] == False}")
    
    return True

def main():
    """Run all integration tests"""
    print("\n🚀 Running MCP Server Integration Tests\n")
    
    results = []
    
    # Run tests
    results.append(("Tool Registration", test_tool_registration()))
    results.append(("Workspace Client Sharing", test_workspace_client_sharing()))
    results.append(("MCP Instance Sharing", test_mcp_instance_sharing()))
    results.append(("Response Helpers", test_response_helpers()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All integration tests passed!")
    else:
        print("\n❌ Some tests failed. Please review the output above.")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    exit(main())