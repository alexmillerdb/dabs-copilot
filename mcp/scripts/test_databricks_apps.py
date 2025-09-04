#!/usr/bin/env python3
"""
Comprehensive testing for Databricks Apps MCP Server deployment
"""

import asyncio
import json
import logging
from typing import Dict, List, Any
from databricks_apps_utils import DatabricksAppsManager

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MCPServerTester:
    """Comprehensive MCP server testing for Databricks Apps"""
    
    def __init__(self, app_name: str = "databricks-mcp-server", profile: str = None):
        self.manager = DatabricksAppsManager(app_name, profile)
        self.test_results = []
    
    async def test_basic_connection(self) -> Dict[str, Any]:
        """Test basic MCP connection"""
        logger.info("🔌 Testing basic MCP connection...")
        result = await self.manager.test_mcp_connection()
        self.test_results.append({"test": "basic_connection", "result": result})
        return result
    
    async def test_health_tool(self) -> Dict[str, Any]:
        """Test the health tool"""
        logger.info("💓 Testing health tool...")
        result = await self.manager.test_mcp_tool("health")
        self.test_results.append({"test": "health_tool", "result": result})
        return result
    
    async def test_list_jobs_tool(self) -> Dict[str, Any]:
        """Test the list_jobs tool"""
        logger.info("📋 Testing list_jobs tool...")
        result = await self.manager.test_mcp_tool("list_jobs", {"limit": 3})
        self.test_results.append({"test": "list_jobs_tool", "result": result})
        return result
    
    async def test_list_notebooks_tool(self) -> Dict[str, Any]:
        """Test the list_notebooks tool"""
        logger.info("📓 Testing list_notebooks tool...")
        result = await self.manager.test_mcp_tool("list_notebooks", {"path": "/Users", "limit": 5})
        self.test_results.append({"test": "list_notebooks_tool", "result": result})
        return result
    
    async def test_list_warehouses_tool(self) -> Dict[str, Any]:
        """Test the list_warehouses tool"""
        logger.info("🏭 Testing list_warehouses tool...")
        result = await self.manager.test_mcp_tool("list_warehouses")
        self.test_results.append({"test": "list_warehouses_tool", "result": result})
        return result
    
    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run all tests and return comprehensive results"""
        logger.info("🚀 Starting comprehensive MCP server testing...")
        
        # Get app URLs first
        app_url = self.manager.get_app_url()
        mcp_url = self.manager.get_mcp_endpoint_url()
        
        if not mcp_url:
            return {
                "success": False,
                "error": "Could not get MCP endpoint URL",
                "app_url": app_url
            }
        
        logger.info(f"🌐 App URL: {app_url}")
        logger.info(f"🔗 MCP Endpoint: {mcp_url}")
        
        # Run all tests
        tests = [
            self.test_basic_connection(),
            self.test_health_tool(),
            self.test_list_jobs_tool(),
            self.test_list_notebooks_tool(),
            self.test_list_warehouses_tool(),
        ]
        
        # Execute tests
        results = await asyncio.gather(*tests, return_exceptions=True)
        
        # Process results
        passed = 0
        failed = 0
        errors = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed += 1
                errors.append(f"Test {i} failed with exception: {str(result)}")
            elif result.get("success"):
                passed += 1
            else:
                failed += 1
                errors.append(f"Test {i} failed: {result.get('error', 'Unknown error')}")
        
        # Summary
        summary = {
            "success": failed == 0,
            "app_url": app_url,
            "mcp_endpoint": mcp_url,
            "tests_passed": passed,
            "tests_failed": failed,
            "total_tests": len(tests),
            "errors": errors,
            "detailed_results": self.test_results
        }
        
        # Log summary
        if summary["success"]:
            logger.info(f"✅ All tests passed! ({passed}/{len(tests)})")
        else:
            logger.error(f"❌ Some tests failed. Passed: {passed}, Failed: {failed}")
            for error in errors:
                logger.error(f"  - {error}")
        
        return summary


async def test_specific_tool_scenarios():
    """Test specific tool scenarios that are important for Databricks Apps"""
    logger.info("🎯 Testing specific tool scenarios...")
    
    manager = DatabricksAppsManager()
    
    # Test scenarios
    scenarios = [
        {
            "name": "Health check with connection info",
            "tool": "health",
            "args": {}
        },
        {
            "name": "List recent jobs",
            "tool": "list_jobs", 
            "args": {"limit": 5}
        },
        {
            "name": "Browse user notebooks",
            "tool": "list_notebooks",
            "args": {"path": "/Users", "recursive": False, "limit": 10}
        },
        {
            "name": "Check available warehouses",
            "tool": "list_warehouses",
            "args": {}
        },
        {
            "name": "Browse DBFS root",
            "tool": "list_dbfs_files",
            "args": {"path": "/", "limit": 10}
        }
    ]
    
    results = []
    for scenario in scenarios:
        logger.info(f"🧪 Testing: {scenario['name']}")
        result = await manager.test_mcp_tool(scenario["tool"], scenario["args"])
        results.append({
            "scenario": scenario["name"],
            "tool": scenario["tool"],
            "success": result.get("success", False),
            "error": result.get("error") if not result.get("success") else None
        })
    
    return results


async def main():
    """Main testing function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Databricks Apps MCP Server")
    parser.add_argument("--app-name", default="databricks-mcp-server", help="App name")
    parser.add_argument("--profile", help="Databricks CLI profile")
    parser.add_argument("--test-type", choices=["comprehensive", "scenarios", "both"], 
                       default="both", help="Type of test to run")
    parser.add_argument("--output", help="Output file for results (JSON)")
    
    args = parser.parse_args()
    
    all_results = {}
    
    if args.test_type in ["comprehensive", "both"]:
        logger.info("=" * 60)
        logger.info("COMPREHENSIVE MCP SERVER TESTING")
        logger.info("=" * 60)
        
        tester = MCPServerTester(args.app_name, args.profile)
        comprehensive_results = await tester.run_comprehensive_test()
        all_results["comprehensive"] = comprehensive_results
    
    if args.test_type in ["scenarios", "both"]:
        logger.info("=" * 60)
        logger.info("SPECIFIC SCENARIO TESTING")
        logger.info("=" * 60)
        
        scenario_results = await test_specific_tool_scenarios()
        all_results["scenarios"] = scenario_results
        
        # Log scenario results
        passed_scenarios = sum(1 for r in scenario_results if r["success"])
        total_scenarios = len(scenario_results)
        
        logger.info(f"📊 Scenario Results: {passed_scenarios}/{total_scenarios} passed")
        for result in scenario_results:
            status = "✅" if result["success"] else "❌"
            logger.info(f"  {status} {result['scenario']}")
            if result["error"]:
                logger.error(f"      Error: {result['error']}")
    
    # Output results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(all_results, f, indent=2)
        logger.info(f"📄 Results saved to: {args.output}")
    else:
        print("\n" + "=" * 60)
        print("FINAL RESULTS")
        print("=" * 60)
        print(json.dumps(all_results, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
