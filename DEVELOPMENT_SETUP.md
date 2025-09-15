# EasyIQ Development Setup Guide

This guide explains how to set up a complete development environment for the EasyIQ Home Assistant integration, including getting the localhost:8123 web interface working.

## Prerequisites

- Python 3.11 or higher
- Git
- Your Aula credentials (username/password)

## Step 1: Install Home Assistant with Docker

The easiest and most reliable way to run Home Assistant for development:

### Prerequisites
- Docker Desktop installed and running
- Git for cloning the repository

### Docker Setup
```bash
# Pull Home Assistant Docker image
docker pull homeassistant/home-assistant:latest

# Create a directory for Home Assistant config
mkdir ha-config

# Run Home Assistant in Docker
docker run -d \
  --name homeassistant \
  --restart=unless-stopped \
  -e TZ=Europe/Copenhagen \
  -v "$(pwd)/ha-config:/config" \
  -p 8123:8123 \
  homeassistant/home-assistant:latest
```

### Windows PowerShell Version
```powershell
# Pull Home Assistant Docker image
docker pull homeassistant/home-assistant:latest

# Create config directory and run Home Assistant
mkdir ha-config
docker run -d --name homeassistant --restart=unless-stopped -e TZ=Europe/Copenhagen -v "${PWD}/ha-config:/config" -p 8123:8123 homeassistant/home-assistant:latest
```

## Step 2: Clone and Setup EasyIQ Integration

```bash
# Clone the repository
git clone https://github.com/your-username/easyiq-ha.git
cd easyiq-ha

# Set up credentials
cp .env.template .env
# Edit .env file with your Aula credentials:
# EASYIQ_USERNAME=your_aula_username
# EASYIQ_PASSWORD=your_aula_password
```

## Step 3: Automated Setup (Recommended)

Use our automated setup script for the easiest installation:

```bash
# Run the automated Docker setup
python scripts/docker_setup.py
```

This script will:
- ✅ Check Docker installation and status
- ✅ Create Home Assistant config directory
- ✅ Copy EasyIQ integration to the right location
- ✅ Pull Home Assistant Docker image
- ✅ Start Home Assistant container
- ✅ Provide next steps and useful commands

## Step 3 Alternative: Manual Setup

If you prefer manual setup or need to customize the installation:

### Copy Integration to Home Assistant Config
```bash
# Create config directory
mkdir ha-config
mkdir ha-config/custom_components

# Copy the EasyIQ integration
# Windows PowerShell:
cp -r custom_components\easyiq ha-config\custom_components\

# Linux/Mac:
cp -r custom_components/easyiq ha-config/custom_components/

# Pull and start Home Assistant
docker pull homeassistant/home-assistant:latest
docker run -d --name homeassistant --restart=unless-stopped -e TZ=Europe/Copenhagen -v "${PWD}/ha-config:/config" -p 8123:8123 homeassistant/home-assistant:latest
```

## Step 4: Access the Web Interface and Add Integration

1. **Open your browser** and go to: `http://localhost:8123`
2. **First-time setup**: Home Assistant will ask you to create an admin user
3. **Complete onboarding**: Follow the setup wizard
4. **Add EasyIQ integration**:
   - Go to Settings → Devices & Services
   - Click "Add Integration"
   - Search for "EasyIQ" (it should now appear!)
   - Enter your Aula credentials

### If Integration Doesn't Appear
If you don't see "EasyIQ" in the integration list:

1. **Check the integration is installed**:
   ```bash
   # Verify files are in the right place
   docker exec homeassistant ls -la /config/custom_components/easyiq/
   ```

2. **Restart Home Assistant**:
   ```bash
   docker restart homeassistant
   ```

3. **Check logs for errors**:
   ```bash
   docker logs homeassistant
   ```

4. **Manual configuration** (if UI doesn't work):
   Add to your `ha-config/configuration.yaml`:
   ```yaml
   easyiq:
     username: your_aula_username
     password: your_aula_password
   ```

## Step 5: Development Workflow

### Testing the Integration
```bash
# Test the client directly
python scripts/test_client.py

# Interactive debugging
python scripts/debug_helper.py

# Validate Home Assistant compatibility
python scripts/validate_ha_integration.py
```

### Making Changes
1. Edit files in `custom_components/easyiq/`
2. Restart Home Assistant (Ctrl+C, then run dev_start script again)
3. Test changes in the web interface at `http://localhost:8123`

### Development Server Features
The development scripts automatically:
- Create a temporary Home Assistant configuration
- Copy the EasyIQ integration to the right location
- Load your credentials from `.env`
- Start Home Assistant on `http://localhost:8123`
- Enable debug logging for the EasyIQ integration

## Troubleshooting

### Docker Issues

#### Container won't start
```bash
# Check if Docker is running
docker --version

# Check container status
docker ps -a

# View container logs
docker logs homeassistant
```

#### Port 8123 already in use
```bash
# Find what's using port 8123
netstat -ano | findstr :8123  # Windows
lsof -i :8123                 # Linux/Mac

# Use a different port
docker run -d --name homeassistant -p 8124:8123 homeassistant/home-assistant:latest
# Then access at http://localhost:8124
```

### Integration Issues

#### Integration not appearing in UI
1. **Verify integration is installed**:
   ```bash
   docker exec homeassistant ls -la /config/custom_components/easyiq/
   ```

2. **Check manifest.json is valid**:
   ```bash
   docker exec homeassistant cat /config/custom_components/easyiq/manifest.json
   ```

3. **Restart Home Assistant**:
   ```bash
   docker restart homeassistant
   ```

4. **Check logs for errors**:
   ```bash
   docker logs homeassistant | grep -i easyiq
   ```

#### Integration fails to load
1. **Check Home Assistant logs**:
   ```bash
   docker logs homeassistant
   ```

2. **Verify file permissions**:
   ```bash
   # Make sure files are readable
   chmod -R 755 custom_components/easyiq/
   ```

3. **Test the client directly**:
   ```bash
   python scripts/test_client.py
   ```

### API Authentication Issues
1. **Verify your credentials** in `.env` file
2. **Test with the client script**:
   ```bash
   python scripts/test_client.py
   ```
3. **Check if your Aula account works** in a browser
4. **Look for authentication errors** in Home Assistant logs:
   ```bash
   docker logs homeassistant | grep -i "auth\|login\|error"
   ```

## Development Tips

### Live Development
- Home Assistant automatically reloads integrations when files change
- Use the debug helper for interactive testing: `python scripts/debug_helper.py`
- Check logs in the Home Assistant web interface: Settings → System → Logs

### Testing Different Scenarios
```bash
# Test specific functionality
python scripts/test_client.py

# Interactive debugging menu
python scripts/debug_helper.py

# Validate integration structure
python scripts/validate_ha_integration.py
```

### Production Testing
Before releasing, test the integration as users would:
1. Copy `custom_components/easyiq/` to a real Home Assistant installation
2. Add the integration through the UI
3. Verify all sensors and calendar entities work correctly

## Next Steps

Once your development environment is working:
1. Make your changes to the integration code
2. Test thoroughly using the development server
3. Run validation scripts to ensure compatibility
4. Create a pull request or release

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review Home Assistant logs at `http://localhost:8123/config/logs`
3. Test the client directly with `python scripts/test_client.py`
4. Use the debug helper for interactive testing