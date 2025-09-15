#!/usr/bin/env python3
"""
Manual installation script for EasyIQ integration
Use this if Docker installation fails
"""

import subprocess
import sys
import shutil
from pathlib import Path

def run_command(cmd):
    """Run a command and return success status."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr

def main():
    """Manual installation of the integration."""
    print("🔧 Manual EasyIQ Integration Installation")
    print("=" * 50)
    
    # Ask for Home Assistant config directory
    ha_config = input("Enter your Home Assistant config directory path (e.g., /config or C:\\Users\\YourName\\.homeassistant): ")
    ha_config_path = Path(ha_config)
    
    if not ha_config_path.exists():
        print(f"❌ Directory {ha_config} does not exist")
        sys.exit(1)
    
    # Create custom_components directory if it doesn't exist
    custom_components_dir = ha_config_path / "custom_components" / "easyiq"
    custom_components_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 Created directory: {custom_components_dir}")
    
    # Create translations directory
    translations_dir = custom_components_dir / "translations"
    translations_dir.mkdir(exist_ok=True)
    
    # Copy files
    files_to_copy = [
        ("custom_components/easyiq/__init__.py", "__init__.py"),
        ("custom_components/easyiq/sensor.py", "sensor.py"),
        ("custom_components/easyiq/client.py", "client.py"),
        ("custom_components/easyiq/calendar.py", "calendar.py"),
        ("custom_components/easyiq/binary_sensor.py", "binary_sensor.py"),
        ("custom_components/easyiq/manifest.json", "manifest.json"),
        ("custom_components/easyiq/config_flow.py", "config_flow.py"),
        ("custom_components/easyiq/const.py", "const.py"),
        ("custom_components/easyiq/strings.json", "strings.json"),
        ("custom_components/easyiq/services.yaml", "services.yaml"),
        ("custom_components/easyiq/translations/en.json", "translations/en.json"),
    ]
    
    print("📋 Copying integration files...")
    for source_path, dest_name in files_to_copy:
        source = Path(source_path)
        if source.exists():
            if "/" in dest_name:
                dest = custom_components_dir / dest_name
            else:
                dest = custom_components_dir / dest_name
            
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
            print(f"✅ Copied {source_path} -> {dest}")
        else:
            print(f"⚠️  File not found: {source_path}")
    
    print("\n🎉 Installation complete!")
    print("\n📋 Next Steps:")
    print("1. Restart Home Assistant")
    print("2. Go to Settings → Devices & Services")
    print("3. Add EasyIQ integration")
    print("4. Check for new sensors and entities")
    
    print("\n🔍 If you have issues:")
    print("1. Check Home Assistant logs")
    print("2. Run: python diagnose_integration.py")
    print("3. Verify all files were copied correctly")

if __name__ == "__main__":
    main()