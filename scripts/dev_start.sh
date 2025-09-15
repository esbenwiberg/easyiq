#!/bin/bash
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

# Create temporary development configuration directory
export HASS_CONFIG_DIR="$(pwd)/temp_dev_config"

# Create dev config directory if it doesn't exist
if [ ! -d "$HASS_CONFIG_DIR" ]; then
    mkdir -p "$HASS_CONFIG_DIR"
    echo "Created temporary development config directory"
fi

# Create basic configuration.yaml for development
if [ ! -f "$HASS_CONFIG_DIR/configuration.yaml" ]; then
    echo "Creating basic development configuration..."
    cat > "$HASS_CONFIG_DIR/configuration.yaml" << 'EOF'
# Home Assistant Development Configuration for EasyIQ Testing

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
EOF
fi

# Create empty automation, script, and scene files
[ ! -f "$HASS_CONFIG_DIR/automations.yaml" ] && echo "[]" > "$HASS_CONFIG_DIR/automations.yaml"
[ ! -f "$HASS_CONFIG_DIR/scripts.yaml" ] && echo "[]" > "$HASS_CONFIG_DIR/scripts.yaml"
[ ! -f "$HASS_CONFIG_DIR/scenes.yaml" ] && echo "[]" > "$HASS_CONFIG_DIR/scenes.yaml"

# Create custom_components symlink if it doesn't exist
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
