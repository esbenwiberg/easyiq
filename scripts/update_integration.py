#!/usr/bin/env python3
"""
Update EasyIQ integration in Docker Home Assistant
This script copies the updated integration files and restarts HA
"""

import subprocess
import sys
from pathlib import Path

def run_command(cmd):
    """Run a command and return success status."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr

def main():
    """Update the integration in Docker."""
    print("🔄 Updating EasyIQ Integration in Docker")
    print("=" * 50)
    
    # Check if Docker container is running
    success, output = run_command("docker ps --filter name=homeassistant")
    if "homeassistant" not in output:
        print("❌ Home Assistant container is not running")
        print("🚀 Starting container...")
        success, _ = run_command("docker start homeassistant")
        if not success:
            print("❌ Failed to start container")
            sys.exit(1)
        print("✅ Container started")
    
    # Copy updated integration files
    print("📋 Copying updated integration files...")
    
    files_to_copy = [
        "custom_components/easyiq/__init__.py",
        "custom_components/easyiq/sensor.py",
        "custom_components/easyiq/client.py",
        "custom_components/easyiq/calendar.py",
        "custom_components/easyiq/manifest.json",
        "custom_components/easyiq/config_flow.py",
        "custom_components/easyiq/const.py",
        "custom_components/easyiq/strings.json",
        "custom_components/easyiq/translations/en.json"
    ]
    
    for file_path in files_to_copy:
        if Path(file_path).exists():
            success, output = run_command(f"docker cp {file_path} homeassistant:/config/{file_path}")
            if success:
                print(f"✅ Copied {file_path}")
            else:
                print(f"❌ Failed to copy {file_path}: {output}")
        else:
            print(f"⚠️  File not found: {file_path}")
    
    # Restart Home Assistant
    print("\n🔄 Restarting Home Assistant...")
    success, output = run_command("docker restart homeassistant")
    if success:
        print("✅ Home Assistant restarted successfully")
        print("⏳ Wait 30-60 seconds for it to fully start up")
        print("🌐 Then check: http://localhost:8123")
    else:
        print("❌ Failed to restart Home Assistant")
        print(output)
    
    print("\n📋 Next Steps:")
    print("1. Wait for Home Assistant to start (30-60 seconds)")
    print("2. Go to http://localhost:8123")
    print("3. Check Settings → Devices & Services → EasyIQ")
    print("4. Look for more entities and better status")
    print("5. Check logs: docker logs homeassistant | grep -i easyiq")

if __name__ == "__main__":
    main()