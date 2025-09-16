#!/usr/bin/env python3
"""
Run EasyIQ integration tests with full debug logging
This script shows you exactly how to get detailed debug output
"""

import subprocess
import sys
import os

def run_with_debug():
    """Run tests with debug logging enabled."""
    print("🔍 EasyIQ Integration Debug Test Runner")
    print("=" * 50)
    
    # Available test scripts
    test_scripts = {
        "1": ("test_integration.py", "Complete integration test with message debugging"),
        "2": ("diagnose_integration.py", "Comprehensive diagnostic with child ID analysis"),
        "3": ("debug_child_ids.py", "Specific child ID mapping debug"),
    }
    
    print("\nAvailable debug tests:")
    for key, (script, description) in test_scripts.items():
        print(f"  {key}. {script} - {description}")
    
    choice = input("\nSelect test to run (1-3): ").strip()
    
    if choice not in test_scripts:
        print("❌ Invalid choice")
        return
    
    script_name, description = test_scripts[choice]
    
    print(f"\n🚀 Running {script_name}...")
    print(f"📋 {description}")
    print("🔍 Debug logging is ENABLED - you'll see detailed API calls and responses")
    print("-" * 50)
    
    # Run the selected script
    try:
        result = subprocess.run([sys.executable, script_name], 
                              capture_output=False, 
                              text=True)
        
        if result.returncode == 0:
            print(f"\n✅ {script_name} completed successfully")
        else:
            print(f"\n❌ {script_name} failed with exit code {result.returncode}")
            
    except Exception as e:
        print(f"\n❌ Error running {script_name}: {e}")
    
    print("\n📋 Debug Information Shown:")
    print("  ✅ Authentication process details")
    print("  ✅ API request URLs and parameters")
    print("  ✅ API response status codes and data")
    print("  ✅ Child ID mapping and data separation")
    print("  ✅ Message parsing and content")
    print("  ✅ Presence status calculations")
    print("  ✅ Error details and stack traces")

if __name__ == "__main__":
    run_with_debug()