#!/usr/bin/env python3
"""Create local development helper files for the EasyIQ integration."""
from __future__ import annotations

import os
from pathlib import Path


def write_text_if_missing(path: Path, content: str, executable: bool = False) -> None:
    """Write generated setup files without overwriting committed scripts."""
    if path.exists():
        print(f"{path} already exists; leaving it unchanged")
        return

    path.write_text(content)
    if executable and os.name != "nt":
        os.chmod(path, 0o755)
    print(f"Created {path}")


def create_env_file() -> None:
    """Create a .env file template for development."""
    env_content = """# EasyIQ Development Environment Variables
# Copy this file to .env when running an opt-in live MitID smoke test

# Guardian MitID/Aula token state for live smoke testing
EASYIQ_MITID_USERNAME=your_mitid_username
EASYIQ_ACCESS_TOKEN=your_aula_access_token
EASYIQ_REFRESH_TOKEN=your_aula_refresh_token
EASYIQ_TOKEN_EXPIRES_AT=1893456000

# Home Assistant development settings
HASS_DEV_PORT=8123
HASS_DEV_HOST=localhost

# Optional: Set to true to enable additional debug logging
EASYIQ_DEBUG=true

# Optional: Mock mode for testing without real API calls
EASYIQ_MOCK_MODE=false
"""
    write_text_if_missing(Path(".env.template"), env_content)


def create_dev_script() -> None:
    """Create a development startup script."""
    script_content = """#!/bin/bash
# EasyIQ Development Startup Script

if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

export HASS_CONFIG_DIR="$(pwd)/dev_config"
mkdir -p "$HASS_CONFIG_DIR"

if [ ! -L "$HASS_CONFIG_DIR/custom_components" ]; then
    ln -s "$(pwd)/custom_components" "$HASS_CONFIG_DIR/custom_components"
    echo "Created symlink to custom_components"
fi

echo "Starting Home Assistant with EasyIQ integration..."
echo "Config directory: $HASS_CONFIG_DIR"
echo "Web interface will be available at: http://${HASS_DEV_HOST:-localhost}:${HASS_DEV_PORT:-8123}"

python -m homeassistant --config "$HASS_CONFIG_DIR" --debug
"""
    write_text_if_missing(Path("scripts/dev_start.sh"), script_content, executable=True)


def create_requirements() -> None:
    """Create requirements file for development."""
    requirements_content = """# EasyIQ Development Requirements

# Home Assistant
homeassistant>=2024.1.0

# Required for EasyIQ integration
requests>=2.28.0
aiohttp>=3.8.0
beautifulsoup4>=4.11.0
lxml>=4.9.0
pytz>=2023.3

# Development tools
pytest>=7.0.0
pytest-asyncio>=0.20.0
pytest-homeassistant-custom-component>=0.13.0

# Code quality
ruff>=0.8.0
mypy>=1.13.0
"""
    write_text_if_missing(Path("requirements-dev.txt"), requirements_content)


def main() -> None:
    """Create local development helper files."""
    print("Setting up EasyIQ development environment...")

    Path("scripts").mkdir(exist_ok=True)
    Path("dev_config").mkdir(exist_ok=True)

    create_env_file()
    create_dev_script()
    create_requirements()

    print("\nDevelopment setup complete!")
    print("\nNext steps:")
    print("1. Install requirements: ./scripts/bootstrap-dev.sh")
    print("2. Run development server: ./scripts/dev_start.sh")
    print("3. Validate the repo: ./scripts/validate.sh")
    print("4. Optional live smoke: fill MitID token fields in .env and run python scripts/test_client.py")


if __name__ == "__main__":
    main()
