#!/usr/bin/env python3
"""
Debug script to check EasyIQ integration status in Docker Home Assistant
"""

import subprocess
import json
import sys

def run_docker_command(cmd):
    """Run a docker command and return the output."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr

def check_integration_files():
    """Check if integration files are properly installed."""
    print("🔍 Checking integration files...")
    
    success, output = run_docker_command("docker exec homeassistant ls -la /config/custom_components/aula-easyiq/")
    if success:
        print("✅ Integration files found:")
        print(output)
    else:
        print("❌ Integration files not found:")
        print(output)
        return False
    
    # Check manifest.json
    success, output = run_docker_command("docker exec homeassistant cat /config/custom_components/aula-easyiq/manifest.json")
    if success:
        try:
            manifest = json.loads(output)
            print(f"✅ Manifest valid - Domain: {manifest.get('domain')}, Version: {manifest.get('version')}")
        except json.JSONDecodeError:
            print("❌ Manifest.json is invalid JSON")
            return False
    else:
        print("❌ Cannot read manifest.json")
        return False
    
    return True

def check_home_assistant_logs():
    """Check Home Assistant logs for EasyIQ related messages."""
    print("\n📋 Checking Home Assistant logs for EasyIQ...")
    
    # Get recent logs
    success, output = run_docker_command("docker logs homeassistant --tail 100")
    if success:
        lines = output.split('\n')
        easyiq_lines = [line for line in lines if 'easyiq' in line.lower()]
        
        if easyiq_lines:
            print("📝 EasyIQ related log entries:")
            for line in easyiq_lines[-10:]:  # Show last 10 entries
                print(f"  {line}")
        else:
            print("⚠️  No EasyIQ related log entries found")
    else:
        print("❌ Cannot read Home Assistant logs")
        print(output)

def check_integration_status():
    """Check if the integration is loaded."""
    print("\n🔧 Checking integration status...")
    
    # Check if integration is in the integrations list
    success, output = run_docker_command("docker exec homeassistant python -c \"import homeassistant.loader; print('easyiq' in homeassistant.loader.INTEGRATIONS)\"")
    if success:
        if "True" in output:
            print("✅ EasyIQ integration is recognized by Home Assistant")
        else:
            print("❌ EasyIQ integration is not recognized by Home Assistant")
    else:
        print("⚠️  Cannot check integration status")

def check_entities():
    """Check if any EasyIQ entities exist."""
    print("\n🏠 Checking for EasyIQ entities...")
    
    # Try to find entity registry
    success, output = run_docker_command("docker exec homeassistant find /config -name '.storage' -type d")
    if success:
        print("✅ Found Home Assistant storage directory")
        
        # Check entity registry
        success, output = run_docker_command("docker exec homeassistant ls -la /config/.storage/")
        if success and "core.entity_registry" in output:
            print("✅ Entity registry exists")
            
            # Look for EasyIQ entities
            success, output = run_docker_command("docker exec homeassistant grep -i easyiq /config/.storage/core.entity_registry 2>/dev/null || echo 'No EasyIQ entities found'")
            if success:
                if "No EasyIQ entities found" in output:
                    print("❌ No EasyIQ entities found in registry")
                else:
                    print("✅ Found EasyIQ entities:")
                    print(output)
        else:
            print("⚠️  Entity registry not found")
    else:
        print("❌ Cannot find storage directory")

def check_config_entries():
    """Check if EasyIQ config entry exists."""
    print("\n⚙️  Checking configuration entries...")
    
    success, output = run_docker_command("docker exec homeassistant grep -i easyiq /config/.storage/core.config_entries 2>/dev/null || echo 'No EasyIQ config entries found'")
    if success:
        if "No EasyIQ config entries found" in output:
            print("❌ No EasyIQ configuration entries found")
            print("💡 This means the integration was never set up through the UI")
        else:
            print("✅ Found EasyIQ configuration entries:")
            print(output)

def restart_home_assistant():
    """Restart Home Assistant container."""
    print("\n🔄 Restarting Home Assistant...")
    success, output = run_docker_command("docker restart homeassistant")
    if success:
        print("✅ Home Assistant restarted successfully")
        print("⏳ Wait 30-60 seconds for it to fully start up")
    else:
        print("❌ Failed to restart Home Assistant")
        print(output)

def main():
    """Main debug function."""
    print("🐛 EasyIQ Integration Debug Tool")
    print("=" * 50)
    
    # Check if Docker is running
    success, _ = run_docker_command("docker ps")
    if not success:
        print("❌ Docker is not running or accessible")
        sys.exit(1)
    
    # Check if Home Assistant container exists
    success, output = run_docker_command("docker ps -a --filter name=homeassistant")
    if "homeassistant" not in output:
        print("❌ Home Assistant container not found")
        print("💡 Run: python scripts/docker_setup.py")
        sys.exit(1)
    
    # Check if container is running
    success, output = run_docker_command("docker ps --filter name=homeassistant")
    if "homeassistant" not in output:
        print("⚠️  Home Assistant container is not running")
        print("🔄 Starting container...")
        run_docker_command("docker start homeassistant")
        print("⏳ Wait 30 seconds for startup...")
        import time
        time.sleep(30)
    
    # Run all checks
    if not check_integration_files():
        print("\n💡 Integration files are missing. Run: python scripts/docker_setup.py")
        return
    
    check_home_assistant_logs()
    check_integration_status()
    check_config_entries()
    check_entities()
    
    print("\n" + "=" * 50)
    print("🎯 Next Steps:")
    print("1. If no config entries found: Set up integration in HA UI")
    print("2. If integration not recognized: Restart HA and check logs")
    print("3. If entities missing: Check integration setup and credentials")
    print("4. Access Home Assistant at: http://localhost:8123")
    
    # Ask if user wants to restart HA
    try:
        restart = input("\n🔄 Restart Home Assistant now? (y/N): ").lower().strip()
        if restart == 'y':
            restart_home_assistant()
    except KeyboardInterrupt:
        print("\n👋 Debug complete!")

if __name__ == "__main__":
    main()