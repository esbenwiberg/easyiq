# EasyIQ Development Startup Script for PowerShell

Write-Host "EasyIQ Development Server" -ForegroundColor Green
Write-Host "=========================" -ForegroundColor Green

# Check if .env file exists
if (Test-Path ".env") {
    Write-Host "Loading environment variables from .env..." -ForegroundColor Yellow
    
    # Read .env file and set environment variables
    Get-Content ".env" | ForEach-Object {
        if ($_ -match "^\s*([^#][^=]*)\s*=\s*(.*)\s*$") {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
            Write-Host "  Set $name" -ForegroundColor Gray
        }
    }
} else {
    Write-Host "Error: .env file not found!" -ForegroundColor Red
    Write-Host "Copy .env.template to .env and fill in your credentials" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if credentials are set
$username = [Environment]::GetEnvironmentVariable("EASYIQ_USERNAME", "Process")
$password = [Environment]::GetEnvironmentVariable("EASYIQ_PASSWORD", "Process")

if (-not $username -or -not $password) {
    Write-Host "Error: EASYIQ_USERNAME and EASYIQ_PASSWORD must be set in .env file" -ForegroundColor Red
    Write-Host "Copy .env.template to .env and fill in your credentials" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Set default values if not set
if (-not [Environment]::GetEnvironmentVariable("HASS_DEV_HOST", "Process")) {
    [Environment]::SetEnvironmentVariable("HASS_DEV_HOST", "localhost", "Process")
}
if (-not [Environment]::GetEnvironmentVariable("HASS_DEV_PORT", "Process")) {
    [Environment]::SetEnvironmentVariable("HASS_DEV_PORT", "8123", "Process")
}

# Create temporary development configuration directory
$hassConfigDir = Join-Path $PWD "temp_dev_config"
[Environment]::SetEnvironmentVariable("HASS_CONFIG_DIR", $hassConfigDir, "Process")

# Create dev config directory if it doesn't exist
if (-not (Test-Path $hassConfigDir)) {
    New-Item -ItemType Directory -Path $hassConfigDir | Out-Null
    Write-Host "Created temporary development config directory" -ForegroundColor Green
}

# Create basic configuration.yaml for development
$configFile = Join-Path $hassConfigDir "configuration.yaml"
if (-not (Test-Path $configFile)) {
    Write-Host "Creating basic development configuration..." -ForegroundColor Yellow
    @"
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
"@ | Out-File -FilePath $configFile -Encoding UTF8
}

# Create empty automation, script, and scene files
$automationsFile = Join-Path $hassConfigDir "automations.yaml"
$scriptsFile = Join-Path $hassConfigDir "scripts.yaml"
$scenesFile = Join-Path $hassConfigDir "scenes.yaml"

if (-not (Test-Path $automationsFile)) { "[]" | Out-File -FilePath $automationsFile -Encoding UTF8 }
if (-not (Test-Path $scriptsFile)) { "[]" | Out-File -FilePath $scriptsFile -Encoding UTF8 }
if (-not (Test-Path $scenesFile)) { "[]" | Out-File -FilePath $scenesFile -Encoding UTF8 }

# Create custom_components junction if it doesn't exist
$customComponentsLink = Join-Path $hassConfigDir "custom_components"
$customComponentsSource = Join-Path $PWD "custom_components"

if (-not (Test-Path $customComponentsLink)) {
    try {
        New-Item -ItemType Junction -Path $customComponentsLink -Target $customComponentsSource | Out-Null
        Write-Host "Created junction to custom_components" -ForegroundColor Green
    } catch {
        Write-Host "Warning: Could not create junction. Trying symbolic link..." -ForegroundColor Yellow
        try {
            New-Item -ItemType SymbolicLink -Path $customComponentsLink -Target $customComponentsSource | Out-Null
            Write-Host "Created symbolic link to custom_components" -ForegroundColor Green
        } catch {
            Write-Host "Error: Could not create link to custom_components" -ForegroundColor Red
            Write-Host "You may need to run PowerShell as Administrator" -ForegroundColor Yellow
        }
    }
}

# Display startup information
Write-Host ""
Write-Host "Starting Home Assistant with EasyIQ integration..." -ForegroundColor Green
Write-Host "Config directory: $hassConfigDir" -ForegroundColor Gray
Write-Host "Web interface will be available at: http://$([Environment]::GetEnvironmentVariable('HASS_DEV_HOST', 'Process')):$([Environment]::GetEnvironmentVariable('HASS_DEV_PORT', 'Process'))" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

# Run Home Assistant
try {
    python -m homeassistant --config $hassConfigDir --debug
} catch {
    Write-Host "Error starting Home Assistant: $_" -ForegroundColor Red
    Write-Host "Make sure Home Assistant is installed: pip install homeassistant" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Server stopped." -ForegroundColor Yellow
Read-Host "Press Enter to exit"