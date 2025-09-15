#!/usr/bin/env python3
"""
Development setup script for EasyIQ Home Assistant integration.
This script helps set up a local development environment with environment variables.
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def create_env_file():
    """Create a .env file template for development."""
    env_content = """# EasyIQ Development Environment Variables
# Copy this file to .env and fill in your actual credentials

# Unilogin credentials for testing
EASYIQ_USERNAME=your_unilogin_username
EASYIQ_PASSWORD=your_unilogin_password

# Home Assistant development settings
HASS_DEV_PORT=8123
HASS_DEV_HOST=localhost

# Optional: Set to true to enable additional debug logging
EASYIQ_DEBUG=true

# Optional: Mock mode for testing without real API calls
EASYIQ_MOCK_MODE=false
"""
    
    env_file = Path(".env.template")
    with open(env_file, "w") as f:
        f.write(env_content)
    
    print(f"Created {env_file}")
    print("Copy this to .env and fill in your credentials")

def create_dev_script():
    """Create a development startup script."""
    script_content = """#!/bin/bash
# EasyIQ Development Startup Script

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check if credentials are set
if [ -z "$EASYIQ_USERNAME" ] || [ -z "$EASYIQ_PASSWORD" ]; then
    echo "Error: EASYIQ_USERNAME and EASYIQ_PASSWORD must be set in .env file"
    echo "Copy .env.template to .env and fill in your credentials"
    exit 1
fi

# Set Home Assistant configuration directory
export HASS_CONFIG_DIR="$(pwd)/dev_config"

# Create custom_components symlink in dev_config if it doesn't exist
if [ ! -L "$HASS_CONFIG_DIR/custom_components" ]; then
    ln -s "$(pwd)/custom_components" "$HASS_CONFIG_DIR/custom_components"
    echo "Created symlink to custom_components"
fi

# Start Home Assistant in development mode
echo "Starting Home Assistant with EasyIQ integration..."
echo "Config directory: $HASS_CONFIG_DIR"
echo "Web interface will be available at: http://$HASS_DEV_HOST:$HASS_DEV_PORT"

# Run Home Assistant
python -m homeassistant --config "$HASS_CONFIG_DIR" --debug
"""
    
    script_file = Path("scripts/dev_start.sh")
    with open(script_file, "w") as f:
        f.write(script_content)
    
    # Make script executable on Unix systems
    if os.name != 'nt':
        os.chmod(script_file, 0o755)
    
    print(f"Created {script_file}")

def create_test_script():
    """Create a test script for the EasyIQ client."""
    test_content = """#!/usr/bin/env python3
\"\"\"
Test script for EasyIQ client functionality.
This script can be used to test the EasyIQ API client independently.
\"\"\"

import os
import sys
import asyncio
from pathlib import Path

# Add the custom_components directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "custom_components"))

from easyiq.client import EasyIQClient

async def test_easyiq_client():
    \"\"\"Test the EasyIQ client with environment variables.\"\"\"
    
    # Load credentials from environment
    username = os.getenv("EASYIQ_USERNAME")
    password = os.getenv("EASYIQ_PASSWORD")
    
    if not username or not password:
        print("Error: EASYIQ_USERNAME and EASYIQ_PASSWORD must be set")
        print("Set them as environment variables or in a .env file")
        return False
    
    print(f"Testing EasyIQ client with username: {username}")
    
    # Create client
    client = EasyIQClient(username, password)
    
    try:
        # Test authentication
        print("Testing authentication...")
        auth_result = await client.authenticate()
        print(f"Authentication result: {auth_result}")
        
        if auth_result:
            # Test getting children
            print("Getting children...")
            children = await client.get_children()
            print(f"Found {len(children)} children: {children}")
            
            # Test getting messages
            print("Getting messages...")
            await client.get_messages()
            print(f"Unread messages: {client.unread_messages}")
            
            # Test ugeplan for each child
            for child in children:
                child_id = child.get("id")
                child_name = child.get("name", "Unknown")
                print(f"Getting ugeplan for {child_name} (ID: {child_id})...")
                ugeplan = await client.get_ugeplan(child_id)
                print(f"Ugeplan data: {ugeplan}")
        
        return auth_result
        
    except Exception as e:
        print(f"Error testing client: {e}")
        return False
    
    finally:
        await client.close()

def load_env_file():
    \"\"\"Load environment variables from .env file.\"\"\"
    env_file = Path(".env")
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    os.environ[key] = value

if __name__ == "__main__":
    # Load .env file if it exists
    load_env_file()
    
    # Run the test
    result = asyncio.run(test_easyiq_client())
    sys.exit(0 if result else 1)
"""
    
    script_file = Path("scripts/test_client.py")
    with open(script_file, "w") as f:
        f.write(test_content)
    
    # Make script executable on Unix systems
    if os.name != 'nt':
        os.chmod(script_file, 0o755)
    
    print(f"Created {script_file}")

def create_requirements():
    """Create requirements file for development."""
    requirements_content = """# EasyIQ Development Requirements

# Home Assistant
homeassistant>=2023.1.0

# Required for EasyIQ integration
requests>=2.28.0
aiohttp>=3.8.0
beautifulsoup4>=4.11.0
lxml>=4.9.0

# Development tools
pytest>=7.0.0
pytest-asyncio>=0.20.0
pytest-homeassistant-custom-component>=0.13.0

# Code quality
black>=22.0.0
isort>=5.10.0
flake8>=5.0.0
mypy>=0.991
"""
    
    req_file = Path("requirements-dev.txt")
    with open(req_file, "w") as f:
        f.write(requirements_content)
    
    print(f"Created {req_file}")

def main():
    """Main setup function."""
    print("Setting up EasyIQ development environment...")
    
    # Create directories
    Path("scripts").mkdir(exist_ok=True)
    Path("dev_config").mkdir(exist_ok=True)
    
    # Create files
    create_env_file()
    create_dev_script()
    create_test_script()
    create_requirements()
    
    print("\nDevelopment setup complete!")
    print("\nNext steps:")
    print("1. Copy .env.template to .env and fill in your credentials")
    print("2. Install requirements: pip install -r requirements-dev.txt")
    print("3. Run development server: ./scripts/dev_start.sh")
    print("4. Test client independently: python scripts/test_client.py")

if __name__ == "__main__":
    main()