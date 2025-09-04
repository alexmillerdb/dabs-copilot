#!/usr/bin/env python3
"""
Databricks Connect smoke test script
Tests OAuth authentication and serverless compute connectivity
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from databricks.connect import DatabricksSession
from databricks.sdk import WorkspaceClient

# Load environment variables
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

def test_databricks_connect():
    """Test Databricks Connect with serverless compute using OAuth profile"""
    
    print("=" * 60)
    print("Databricks Connect Configuration Test")
    print("=" * 60)
    
    # Get configuration from environment
    profile = os.getenv("DATABRICKS_CONFIG_PROFILE", "aws-apps")
    host = os.getenv("DATABRICKS_HOST")
    serverless_compute = os.getenv("DATABRICKS_SERVERLESS_COMPUTE_ID", "auto")
    
    print(f"Profile: {profile}")
    print(f"Host: {host}")
    print(f"Serverless Compute: {serverless_compute}")
    print("-" * 60)
    
    try:
        # Test 1: Create Databricks Session with profile-based auth
        print("\n1. Creating DatabricksSession with OAuth profile...")
        
        if serverless_compute == "auto":
            # Use serverless compute
            spark = DatabricksSession.builder \
                .profile(profile) \
                .serverless(True) \
                .getOrCreate()
        else:
            # Use specific cluster
            cluster_id = os.getenv("DATABRICKS_CLUSTER_ID")
            if not cluster_id:
                print("ERROR: DATABRICKS_CLUSTER_ID not set and serverless not enabled")
                return False
            
            spark = DatabricksSession.builder \
                .profile(profile) \
                .clusterId(cluster_id) \
                .getOrCreate()
        
        print("✓ DatabricksSession created successfully")
        
        # Test 2: Run a simple Spark query
        print("\n2. Testing Spark connectivity...")
        df = spark.range(10)
        count = df.count()
        print(f"✓ Spark query executed. Row count: {count}")
        
        # Test 3: Show Spark version
        print("\n3. Spark environment info:")
        print(f"   Spark version: {spark.version}")
        
        # Test 4: Create a simple DataFrame
        print("\n4. Creating and displaying test DataFrame...")
        test_data = spark.createDataFrame(
            [(1, "Alice", 25), (2, "Bob", 30), (3, "Charlie", 35)],
            ["id", "name", "age"]
        )
        test_data.show(5)
        print("✓ DataFrame operations successful")
        
        # Test 5: Test SDK Client
        print("\n5. Testing Databricks SDK client...")
        client = WorkspaceClient(profile=profile)
        current_user = client.current_user.me()
        print(f"✓ SDK authenticated as: {current_user.user_name}")
        
        # Clean up
        spark.stop()
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print("\nTroubleshooting steps:")
        print("1. Ensure you're authenticated: databricks auth login --profile aws-apps")
        print("2. Check your .env file has correct DATABRICKS_HOST")
        print("3. Verify serverless compute is enabled in your workspace")
        print("4. If using a cluster, set DATABRICKS_CLUSTER_ID in .env")
        return False

if __name__ == "__main__":
    print("\n🚀 Starting Databricks Connect setup verification...\n")
    
    # Check if virtual environment is activated
    if not sys.prefix.endswith(".venv"):
        print("⚠️  WARNING: Virtual environment not activated!")
        print("   Run: source .venv/bin/activate")
        print("")
    
    # Run main test
    connect_success = test_databricks_connect()
    
    print("\n📝 Next steps:")
    print("1. Start building your MCP server in backend/mcp_server/")
    print("2. Implement Claude agent in backend/claude_agent/")
    print("3. Create FastAPI backend in backend/api/")
    print("4. Build React UI in frontend/")
    print("\nRefer to /docs for detailed implementation guidance.")
    
    sys.exit(0 if connect_success else 1)