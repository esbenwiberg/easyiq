#!/usr/bin/env python3
"""
Cross-platform development server startup script for EasyIQ integration.
This Python script handles environment variables reliably on all platforms.
"""

import os
import sys
import subprocess
from pathlib import Path

def load_env_file():
    """Load environment variables from .env file."""
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ Error: .env file not found!")
        print("📝 Copy .env.template to .env and fill in your credentials")
        return False
    
    print("📂 Loading environment variables from .env...")
    
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                if "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()
                    print(f"   ✅ Set {key.strip()}")
    
    return True

def check_credentials():
    """Check if required credentials are set."""
    username = os.getenv("EASYIQ_USERNAME")
    password = os.getenv("EASYIQ_PASSWORD")
    
    if not username or not password:
        print("❌ Error: EASYIQ_USERNAME and EASYIQ_PASSWORD must be set in .env file")
        print("📝 Copy .env.template to .env and fill in your credentials")
        return False
    
    print(f"🔐 Username: {username}")
    print(f"🔐 Password: {'*' * len(password)}")
    return True

def setup_environment():
    """Set up the development environment."""
    # Set default values
    if not os.getenv("HASS_DEV_HOST"):
        os.environ["HASS_DEV_HOST"] = "localhost"
    
    if not os.getenv("HASS_DEV_PORT"):
        os.environ["HASS_DEV_PORT"] = "8123"
    
    # Create temporary development configuration directory
    config_dir = Path.cwd() / "temp_dev_config"
    os.environ["HASS_CONFIG_DIR"] = str(config_dir)
    
    # Create dev config directory if it doesn't exist
    config_dir.mkdir(exist_ok=True)
    
    # Create basic configuration.yaml for development
    config_file = config_dir / "configuration.yaml"
    if not config_file.exists():
        print("📝 Creating basic development configuration...")
        config_content = """# Home Assistant Development Configuration for EasyIQ Testing

homeassistant:
  name: EasyIQ Dev
  latitude: 55.6761
  longitude: 12.5683
  elevation: 0
  unit_system: metric
  time_zone: Europe/Copenhagen
  country: DK

frontend:
config:
system_health:
mobile_app:
person:
zone:

# Enable debug logging for EasyIQ
logger:
  default: info
  logs:
    custom_components.easyiq: debug

# Development tools
developer_tools:
"""
        config_file.write_text(config_content)
    
    # Create empty automation, script, and scene files
    for filename in ["automations.yaml", "scripts.yaml", "scenes.yaml"]:
        file_path = config_dir / filename
        if not file_path.exists():
            file_path.write_text("[]")
    
    return config_dir

def create_custom_components_link(config_dir):
    """Create a link to custom_components in the dev_config directory."""
    custom_components_link = config_dir / "custom_components"
    custom_components_source = Path.cwd() / "custom_components"
    
    if custom_components_link.exists():
        return True
    
    try:
        if os.name == 'nt':  # Windows
            # Try junction first, then symbolic link
            try:
                subprocess.run([
                    "mklink", "/J", 
                    str(custom_components_link), 
                    str(custom_components_source)
                ], shell=True, check=True, capture_output=True)
                print("🔗 Created junction to custom_components")
            except subprocess.CalledProcessError:
                # Fallback to symbolic link
                custom_components_link.symlink_to(custom_components_source, target_is_directory=True)
                print("🔗 Created symbolic link to custom_components")
        else:  # Linux/Mac
            custom_components_link.symlink_to(custom_components_source, target_is_directory=True)
            print("🔗 Created symbolic link to custom_components")
        
        return True
    except Exception as e:
        print(f"⚠️  Warning: Could not create link to custom_components: {e}")
        print("   You may need to run as administrator or manually copy the directory")
        return False

def start_home_assistant(config_dir):
    """Start Home Assistant with the development configuration."""
    host = os.getenv("HASS_DEV_HOST", "localhost")
    port = os.getenv("HASS_DEV_PORT", "8123")
    
    print("\n" + "="*60)
    print("🚀 Starting Home Assistant with EasyIQ integration...")
    print("="*60)
    print(f"📁 Config directory: {config_dir}")
    print(f"🌐 Web interface: http://{host}:{port}")
    print("🛑 Press Ctrl+C to stop the server")
    print("="*60)
    print()
    
    try:
        # Start Home Assistant
        subprocess.run([
            sys.executable, "-m", "homeassistant",
            "--config", str(config_dir),
            "--debug"
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error starting Home Assistant: {e}")
        print("💡 Make sure Home Assistant is installed: pip install homeassistant")
        return False
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
        return True
    
    return True

def main():
    """Main startup function."""
    print("🔧 EasyIQ Development Server")
    print("="*30)
    
    # Load environment variables
    if not load_env_file():
        input("Press Enter to exit...")
        return 1
    
    # Check credentials
    if not check_credentials():
        input("Press Enter to exit...")
        return 1
    
    # Setup environment
    config_dir = setup_environment()
    
    # Create custom_components link
    create_custom_components_link(config_dir)
    
    # Start Home Assistant
    success = start_home_assistant(config_dir)
    
    if not success:
        input("Press Enter to exit...")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())