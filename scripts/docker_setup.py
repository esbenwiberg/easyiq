#!/usr/bin/env python3
"""
Docker Setup Script for EasyIQ Home Assistant Integration
Simplifies the Docker setup process for development.
"""

import os
import subprocess
import sys
from pathlib import Path

def run_command(cmd, shell=True):
    """Run a command and return success status."""
    try:
        result = subprocess.run(cmd, shell=shell, check=True, capture_output=True, text=True)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr

def check_docker():
    """Check if Docker is installed and running."""
    print("🐳 Checking Docker...")
    success, output = run_command("docker --version")
    if not success:
        print("❌ Docker is not installed or not in PATH")
        print("Please install Docker Desktop from: https://www.docker.com/products/docker-desktop")
        return False
    
    print(f"✅ Docker found: {output.strip()}")
    
    # Check if Docker daemon is running
    success, _ = run_command("docker ps")
    if not success:
        print("❌ Docker daemon is not running")
        print("Please start Docker Desktop")
        return False
    
    print("✅ Docker daemon is running")
    return True

def setup_config_directory():
    """Create Home Assistant config directory."""
    config_dir = Path("ha-config")
    custom_components_dir = config_dir / "custom_components"
    
    print(f"📁 Creating config directory: {config_dir}")
    config_dir.mkdir(exist_ok=True)
    custom_components_dir.mkdir(exist_ok=True)
    
    # Copy configuration template if configuration.yaml doesn't exist
    config_file = config_dir / "configuration.yaml"
    if not config_file.exists():
        print("📝 Creating Home Assistant configuration...")
        template_file = Path("scripts/ha_config_template.yaml")
        if template_file.exists():
            import shutil
            shutil.copy(template_file, config_file)
            print("✅ Configuration file created")
        else:
            # Create minimal config if template doesn't exist
            config_file.write_text("""# Basic Home Assistant Configuration
homeassistant:
  name: EasyIQ Development
  latitude: 55.6761
  longitude: 12.5683
  elevation: 0
  unit_system: metric
  time_zone: Europe/Copenhagen
  country: DK

frontend:
config:
automation: !include automations.yaml
scene: !include scenes.yaml
script: !include scripts.yaml

logger:
  default: info
  logs:
    custom_components.easyiq: debug
""")
            print("✅ Basic configuration file created")
    
    # Create empty automation, scene, and script files
    for filename in ["automations.yaml", "scenes.yaml", "scripts.yaml"]:
        file_path = config_dir / filename
        if not file_path.exists():
            file_path.write_text("[]")
    
    return config_dir

def copy_integration(config_dir):
    """Copy EasyIQ integration to Home Assistant config."""
    source_dir = Path("custom_components/easyiq")
    target_dir = config_dir / "custom_components/easyiq"
    
    if not source_dir.exists():
        print(f"❌ Source integration not found: {source_dir}")
        return False
    
    print(f"📋 Copying integration from {source_dir} to {target_dir}")
    
    # Remove existing target if it exists
    if target_dir.exists():
        import shutil
        shutil.rmtree(target_dir)
    
    # Copy the integration
    import shutil
    shutil.copytree(source_dir, target_dir)
    
    print("✅ Integration copied successfully")
    return True

def stop_existing_container():
    """Stop and remove existing Home Assistant container."""
    print("🛑 Stopping existing Home Assistant container...")
    
    # Stop container
    success, _ = run_command("docker stop homeassistant")
    if success:
        print("✅ Stopped existing container")
    
    # Remove container
    success, _ = run_command("docker rm homeassistant")
    if success:
        print("✅ Removed existing container")

def pull_home_assistant():
    """Pull the latest Home Assistant Docker image."""
    print("📥 Pulling Home Assistant Docker image...")
    success, output = run_command("docker pull homeassistant/home-assistant:latest")
    if not success:
        print(f"❌ Failed to pull Home Assistant image: {output}")
        return False
    
    print("✅ Home Assistant image pulled successfully")
    return True

def start_home_assistant(config_dir):
    """Start Home Assistant container."""
    print("🚀 Starting Home Assistant container...")
    
    # Get absolute path for volume mounting
    config_path = config_dir.resolve()
    
    cmd = [
        "docker", "run", "-d",
        "--name", "homeassistant",
        "--restart", "unless-stopped",
        "-e", "TZ=Europe/Copenhagen",
        "-v", f"{config_path}:/config",
        "-p", "8123:8123",
        "homeassistant/home-assistant:latest"
    ]
    
    success, output = run_command(cmd, shell=False)
    if not success:
        print(f"❌ Failed to start Home Assistant: {output}")
        return False
    
    print("✅ Home Assistant container started successfully")
    print("🌐 Web interface will be available at: http://localhost:8123")
    return True

def check_credentials():
    """Check if credentials are set up."""
    env_file = Path(".env")
    if not env_file.exists():
        print("⚠️  No .env file found")
        print("📝 Please create .env file with your Aula credentials:")
        print("   cp .env.template .env")
        print("   # Edit .env with your username and password")
        return False
    
    print("✅ .env file found")
    return True

def main():
    """Main setup function."""
    print("🏗️  EasyIQ Home Assistant Docker Setup")
    print("=" * 50)
    
    # Check Docker
    if not check_docker():
        sys.exit(1)
    
    # Check credentials
    check_credentials()
    
    # Setup config directory
    config_dir = setup_config_directory()
    
    # Copy integration
    if not copy_integration(config_dir):
        sys.exit(1)
    
    # Stop existing container
    stop_existing_container()
    
    # Pull Home Assistant image
    if not pull_home_assistant():
        sys.exit(1)
    
    # Start Home Assistant
    if not start_home_assistant(config_dir):
        sys.exit(1)
    
    print("\n🎉 Setup Complete!")
    print("=" * 50)
    print("📋 Next Steps:")
    print("1. Wait 30-60 seconds for Home Assistant to start")
    print("2. Open http://localhost:8123 in your browser")
    print("3. Complete the initial setup wizard")
    print("4. Go to Settings → Devices & Services")
    print("5. Click 'Add Integration' and search for 'EasyIQ'")
    print("6. Enter your Aula credentials")
    print("\n🔧 Useful Commands:")
    print("   docker logs homeassistant     # View logs")
    print("   docker restart homeassistant  # Restart container")
    print("   docker stop homeassistant     # Stop container")

if __name__ == "__main__":
    main()