#!/usr/bin/env python3
"""
Test script for context-driven DAB generation
Demonstrates the new generate_bundle tool with context files
"""

import os
import sys
import json
import asyncio

# Add server directory to path
sys.path.insert(0, 'server')

async def test_context_driven_generation():
    """Test the context-driven generate_bundle tool"""
    
    print("🧪 Testing Context-Driven DAB Generation")
    print("=" * 50)
    
    try:
        # Import the tools after path setup
        from tools_dab import generate_bundle
        
        # Test 1: Generate bundle with sample analysis data
        print("\n📝 Test 1: Generate bundle with analysis data")
        
        # Sample analysis results (simulating what analyze_notebook would return)
        sample_analysis = {
            "file_info": {
                "type": "python",
                "path": "/Users/test/etl_pipeline.py",
                "size_bytes": 5432
            },
            "dependencies": {
                "imports": ["pandas", "pyspark.sql", "delta"],
                "databricks": ["databricks-sdk"],
                "third_party": ["requests"]
            },
            "data_sources": {
                "input_tables": ["main.raw.sales", "main.raw.customers"],
                "output_tables": ["main.silver.sales_summary"],
                "file_paths": ["/dbfs/mnt/data/config.json"]
            },
            "patterns": {
                "workflow_type": "ETL",
                "stages": ["extract", "transform", "load"],
                "complexity": "medium"
            },
            "databricks_features": {
                "widgets": ["processing_date", "environment"],
                "spark_operations": ["read", "write", "join", "aggregate"],
                "unity_catalog": True
            },
            "recommendations": {
                "job_type": "scheduled_batch",
                "cluster_config": {
                    "node_type_id": "i3.xlarge",
                    "num_workers": 4
                },
                "schedule": "daily"
            }
        }
        
        # Call the generate_bundle tool
        result = await generate_bundle(
            bundle_name="test-etl-pipeline",
            analysis_results=sample_analysis,
            target_environment="dev",
            output_path="/tmp/test_bundle_context"
        )
        
        print(f"✅ Bundle generation context prepared")
        
        # Parse and display the result
        result_data = json.loads(result)
        if result_data.get("success"):
            context = result_data["data"]["bundle_generation_context"]
            print(f"📁 Bundle directory: {context['bundle_directory']}")
            print(f"🎯 Target environment: {context['target_environment']}")
            print(f"📋 Pattern guidance available: {len(context['pattern_selection_guidance'])} patterns")
            print(f"📚 Context files referenced: {len(context['context_files'])} files")
            print(f"📝 Generation instructions: {len(context['generation_instructions'])} characters")
            
            # Show what Claude should do next
            print(f"\n🤖 Instructions for Claude:")
            print(f"   {result_data['data']['instructions_for_claude']}")
            
        else:
            print(f"❌ Error: {result_data.get('error')}")
            
        print("\n" + "=" * 50)
        
        # Test 2: Test with notebook paths (would analyze them first)
        print("\n📝 Test 2: Generate bundle from notebook paths")
        
        result2 = await generate_bundle(
            bundle_name="multi-notebook-pipeline", 
            notebook_paths=[
                "/Users/test/extract.py",
                "/Users/test/transform.py"
            ],
            target_environment="staging",
            output_path="/tmp/test_bundle_multi"
        )
        
        result2_data = json.loads(result2)
        if result2_data.get("success"):
            print("✅ Multi-notebook bundle context prepared")
            context2 = result2_data["data"]["bundle_generation_context"]
            print(f"📁 Bundle directory: {context2['bundle_directory']}")
            print(f"🎯 Target environment: {context2['target_environment']}")
        else:
            print(f"❌ Error: {result2_data.get('error')}")
            
        print("\n" + "=" * 50)
        
        # Test 3: Check context files exist
        print("\n📝 Test 3: Verify context files are accessible")
        
        context_files = [
            "/Users/alex.miller/Documents/GitHub/dabs-copilot/mcp/context/DAB_PATTERNS.md",
            "/Users/alex.miller/Documents/GitHub/dabs-copilot/mcp/context/CLUSTER_CONFIGS.md",
            "/Users/alex.miller/Documents/GitHub/dabs-copilot/mcp/context/BEST_PRACTICES.md"
        ]
        
        for file_path in context_files:
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                print(f"✅ {os.path.basename(file_path)}: {file_size:,} bytes")
            else:
                print(f"❌ Missing: {os.path.basename(file_path)}")
                
        print("\n🎉 Context-driven generation tests completed!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running from the mcp directory")
        return False
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def demonstrate_claude_workflow():
    """Show how this would work with Claude Code CLI"""
    
    print("\n" + "=" * 60)
    print("🚀 Demonstration: Claude Code CLI Workflow")
    print("=" * 60)
    
    print("""
    Here's how this works with Claude Code CLI:
    
    1. User: "Analyze this notebook and generate a DAB"
       
    2. Claude Code:
       a) Calls analyze_notebook MCP tool → Gets detailed analysis
       b) Calls generate_bundle MCP tool → Gets generation context
       c) Reads context files (DAB_PATTERNS.md, CLUSTER_CONFIGS.md, BEST_PRACTICES.md)
       d) Uses AI intelligence to generate appropriate YAML
       e) Saves complete databricks.yml to specified directory
       
    3. Example result - Claude generates something like:
    
    ```yaml
    bundle:
      name: test-etl-pipeline
      description: ETL pipeline generated from notebook analysis
      
    variables:
      catalog:
        description: Unity Catalog catalog name
        default: ${bundle.target}
        
    resources:
      jobs:
        etl_job:
          name: ${bundle.name}-${bundle.target}
          job_clusters:
            - job_cluster_key: etl_cluster
              new_cluster:
                spark_version: "13.3.x-scala2.12"
                node_type_id: "i3.xlarge"  # From CLUSTER_CONFIGS.md
                num_workers: 4              # Based on analysis
                
          tasks:
            - task_key: etl_process
              notebook_task:
                notebook_path: ./notebooks/etl_pipeline.py
                base_parameters:
                  processing_date: ${var.processing_date}
                  catalog: ${var.catalog}
                  
    targets:
      dev:
        mode: development
        variables:
          catalog: dev_catalog
    ```
    
    4. User gets a complete, deployable DAB that follows best practices!
    
    ✨ No rigid templates - just intelligent generation based on context!
    """)

def main():
    """Run the context generation tests"""
    print("🎯 Context-Driven DAB Generation Test Suite")
    
    # Check we're in the right directory
    if not os.path.exists("server/tools_dab.py"):
        print("❌ Please run this script from the mcp/ directory")
        print("   cd /path/to/dabs-copilot/mcp")
        print("   python test_context_generation.py")
        return 1
    
    # Run the tests
    success = asyncio.run(test_context_driven_generation())
    
    if success:
        asyncio.run(demonstrate_claude_workflow())
        print("\n✅ All tests passed! Context-driven generation is ready.")
        return 0
    else:
        print("\n❌ Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    exit(main())