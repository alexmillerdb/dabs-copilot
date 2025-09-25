#!/usr/bin/env python3
"""
Setup script for DAB Generator environment configuration
"""

import os
import sys
from pathlib import Path

def check_environment():
    """Check current environment configuration"""
    print("🔍 Checking Current Environment Configuration")
    print("=" * 50)
    
    # Check Claude API Key
    claude_key = os.getenv("CLAUDE_API_KEY")
    if claude_key:
        print(f"✅ CLAUDE_API_KEY: Set (ending in ...{claude_key[-8:]})")
    else:
        print("❌ CLAUDE_API_KEY: Not set")
    
    # Check Databricks Configuration
    db_profile = os.getenv("DATABRICKS_CONFIG_PROFILE")
    db_host = os.getenv("DATABRICKS_HOST")
    db_token = os.getenv("DATABRICKS_TOKEN")
    
    print(f"📊 DATABRICKS_CONFIG_PROFILE: {db_profile or 'Not set (will use DEFAULT)'}")
    print(f"🌐 DATABRICKS_HOST: {db_host or 'Not set'}")
    print(f"🔑 DATABRICKS_TOKEN: {'Set' if db_token else 'Not set'}")
    
    # Check Databricks CLI
    try:
        import subprocess
        result = subprocess.run(['databricks', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Databricks CLI: {result.stdout.strip()}")
        else:
            print("❌ Databricks CLI: Not found or not working")
    except FileNotFoundError:
        print("❌ Databricks CLI: Not installed")
    
    return bool(claude_key), bool(db_profile or db_host)

def create_env_file():
    """Create a sample .env file"""
    env_path = Path(".env")
    
    if env_path.exists():
        print(f"⚠️  .env file already exists at {env_path.absolute()}")
        response = input("Do you want to overwrite it? (y/N): ").lower()
        if response != 'y':
            return False
    
    env_content = """# DAB Generator Environment Configuration

# Required: Claude API Key
# Get your API key from: https://console.anthropic.com/
CLAUDE_API_KEY=sk-ant-api03-your-key-here

# Required: Databricks Configuration
# Option 1: Use a specific profile (recommended)
DATABRICKS_CONFIG_PROFILE=your-profile-name

# Option 2: Direct configuration
# DATABRICKS_HOST=https://your-workspace.databricks.com
# DATABRICKS_TOKEN=your-databricks-token

# Optional: Additional configuration
# LOG_LEVEL=INFO
"""
    
    with open(env_path, 'w') as f:
        f.write(env_content)
    
    print(f"✅ Created sample .env file at {env_path.absolute()}")
    print("📝 Please edit this file and add your actual API keys and configuration.")
    return True

def setup_databricks_cli():
    """Provide instructions for Databricks CLI setup"""
    print("\n🔧 Databricks CLI Setup Instructions")
    print("=" * 40)
    
    print("1. Install Databricks CLI:")
    print("   pip install databricks-cli")
    print()
    print("2. Configure authentication:")
    print("   databricks configure --token")
    print("   - Enter your workspace URL (e.g., https://your-workspace.databricks.com)")
    print("   - Enter your personal access token")
    print()
    print("3. Or use a profile:")
    print("   databricks configure --token --profile your-profile-name")
    print("   export DATABRICKS_CONFIG_PROFILE=your-profile-name")
    print()
    print("4. Test the configuration:")
    print("   databricks workspace list")

def main():
    print("🚀 DAB Generator Environment Setup")
    print("=" * 50)
    
    # Check current environment
    claude_ok, databricks_ok = check_environment()
    
    if claude_ok and databricks_ok:
        print("\n🎉 Environment looks good! You should be ready to use the full DAB Generator.")
        print("   Test it at: http://localhost:8000")
        return
    
    print("\n⚠️  Environment setup needed:")
    
    if not claude_ok:
        print("   - Claude API key is required for AI functionality")
    
    if not databricks_ok:
        print("   - Databricks configuration is needed for DAB generation")
    
    print("\n🛠️  Setup Options:")
    print("1. Create a .env file template")
    print("2. Show Databricks CLI setup instructions")
    print("3. Exit")
    
    while True:
        choice = input("\nSelect an option (1-3): ").strip()
        
        if choice == '1':
            create_env_file()
            break
        elif choice == '2':
            setup_databricks_cli()
            break
        elif choice == '3':
            print("👋 Goodbye! Run this script again after setting up your environment.")
            break
        else:
            print("❌ Invalid choice. Please enter 1, 2, or 3.")
    
    print("\n📚 Next Steps:")
    print("1. Set up your environment variables (CLAUDE_API_KEY, etc.)")
    print("2. Install and configure Databricks CLI")
    print("3. Start the server: python -m uvicorn main:app --reload")
    print("4. Test at: http://localhost:8000/test")
    print("5. Once working, use the full UI at: http://localhost:8000")

if __name__ == "__main__":
    main()