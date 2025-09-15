#!/usr/bin/env python3
"""Check if all integration files can be imported correctly."""

import sys
import os
import traceback

# Add the custom_components path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components'))

def check_file_imports():
    """Check if all integration files can be imported."""
    print("🔍 Checking EasyIQ Integration File Imports")
    print("=" * 50)
    
    files_to_check = [
        'custom_components.easyiq.const',
        'custom_components.easyiq.client', 
        'custom_components.easyiq.sensor',
        'custom_components.easyiq.binary_sensor',
        'custom_components.easyiq.calendar',
        'custom_components.easyiq.config_flow',
    ]
    
    all_good = True
    
    for module_name in files_to_check:
        try:
            __import__(module_name)
            print(f"✅ {module_name}")
        except Exception as e:
            print(f"❌ {module_name}: {e}")
            traceback.print_exc()
            all_good = False
    
    if all_good:
        print("\n🎉 All files import successfully!")
    else:
        print("\n❌ Some files have import errors - fix these first!")
    
    return all_good

if __name__ == "__main__":
    check_file_imports()