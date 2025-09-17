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
    
    # Check if Docker is available
    success, output = run_command("docker --version")
    if not success:
        print("❌ Docker is not available or not running")
        print("💡 Please ensure Docker Desktop is running and try again")
        print("🔧 Alternative: Run 'python scripts/manual_update_integration.py'")
        sys.exit(1)
    
    # Check if Docker container is running
    success, output = run_command("docker ps --filter name=homeassistant")
    if not success:
        print("❌ Cannot connect to Docker daemon")
        print("💡 Please start Docker Desktop and try again")
        print("🔧 Alternative: Run 'python scripts/manual_update_integration.py'")
        sys.exit(1)
        
    if "homeassistant" not in output:
        print("❌ Home Assistant container is not running")
        print("🚀 Starting container...")
        success, _ = run_command("docker start homeassistant")
        if not success:
            print("❌ Failed to start container")
            print("🔧 Alternative: Run 'python scripts/manual_update_integration.py'")
            sys.exit(1)
        print("✅ Container started")
    
    # Create directory structure in container first
    print("📁 Creating directory structure in container...")
    success, output = run_command("docker exec homeassistant mkdir -p /config/custom_components/aula_easyiq/translations")
    if not success:
        print("❌ Failed to create directory structure in container")
        print("🔧 Alternative: Run 'python scripts/manual_update_integration.py'")
        sys.exit(1)
    
    # Copy updated integration files
    print("📋 Copying updated integration files...")
    
    files_to_copy = [
        "custom_components/aula_easyiq/__init__.py",
        "custom_components/aula_easyiq/sensor.py",
        "custom_components/aula_easyiq/client.py",
        "custom_components/aula_easyiq/calendar.py",
        "custom_components/aula_easyiq/binary_sensor.py",  # Added missing binary_sensor.py!
        "custom_components/aula_easyiq/manifest.json",
        "custom_components/aula_easyiq/config_flow.py",
        "custom_components/aula_easyiq/const.py",
        "custom_components/aula_easyiq/strings.json",
        "custom_components/aula_easyiq/translations/en.json"
    ]
    
    copy_failed = False
    for file_path in files_to_copy:
        if Path(file_path).exists():
            success, output = run_command(f"docker cp {file_path} homeassistant:/config/{file_path}")
            if success:
                print(f"✅ Copied {file_path}")
            else:
                print(f"❌ Failed to copy {file_path}: {output}")
                copy_failed = True
        else:
            print(f"⚠️  File not found: {file_path}")
    
    if copy_failed:
        print("\n❌ Some files failed to copy due to Docker connectivity issues")
        print("🔧 Alternative solution: Run 'python scripts/manual_update_integration.py'")
        print("   Then restart Home Assistant container manually: docker restart homeassistant")
        return
    
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
    print("4. Look for NEW separate calendars:")
    print("   - EasyIQ [Child Name] Weekplan (school schedule)")
    print("   - EasyIQ [Child Name] Homework (assignments)")
    print("5. Check for presence sensors: EasyIQ [Child Name] Present")
    print("6. Check messages sensor: EasyIQ Messages")
    print("7. Check logs: docker logs homeassistant | grep -i easyiq")

if __name__ == "__main__":
    main()