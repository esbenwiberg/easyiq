@echo off
REM EasyIQ Development Startup Script for Windows

REM Check if .env file exists and load variables
if exist .env (
    echo Loading environment variables from .env...
    for /f "usebackq tokens=1,2 delims==" %%a in (.env) do (
        if not "%%a"=="" if not "%%a:~0,1%"=="#" (
            set "%%a=%%b"
        )
    )
) else (
    echo .env file not found. Copy .env.template to .env and fill in your credentials.
    pause
    exit /b 1
)

REM Check if credentials are set
if "%EASYIQ_USERNAME%"=="" (
    echo Error: EASYIQ_USERNAME must be set in .env file
    pause
    exit /b 1
)

if "%EASYIQ_PASSWORD%"=="" (
    echo Error: EASYIQ_PASSWORD must be set in .env file
    pause
    exit /b 1
)

REM Set default values if not set
if "%HASS_DEV_HOST%"=="" set HASS_DEV_HOST=localhost
if "%HASS_DEV_PORT%"=="" set HASS_DEV_PORT=8123

REM Create temporary development configuration directory
set HASS_CONFIG_DIR=%CD%\temp_dev_config

REM Create dev config directory if it doesn't exist
if not exist "%HASS_CONFIG_DIR%" (
    mkdir "%HASS_CONFIG_DIR%"
    echo Created temporary development config directory
)

REM Create basic configuration.yaml for development
if not exist "%HASS_CONFIG_DIR%\configuration.yaml" (
    echo Creating basic development configuration...
    (
        echo # Home Assistant Development Configuration for EasyIQ Testing
        echo.
        echo homeassistant:
        echo   name: EasyIQ Dev
        echo   latitude: 55.6761
        echo   longitude: 12.5683
        echo   elevation: 0
        echo   unit_system: metric
        echo   time_zone: Europe/Copenhagen
        echo   country: DK
        echo.
        echo frontend:
        echo config:
        echo system_health:
        echo mobile_app:
        echo person:
        echo zone:
        echo.
        echo # Enable debug logging for EasyIQ
        echo logger:
        echo   default: info
        echo   logs:
        echo     custom_components.easyiq: debug
        echo.
        echo # Development tools
        echo developer_tools:
    ) > "%HASS_CONFIG_DIR%\configuration.yaml"
)

REM Create empty automation, script, and scene files
if not exist "%HASS_CONFIG_DIR%\automations.yaml" echo [] > "%HASS_CONFIG_DIR%\automations.yaml"
if not exist "%HASS_CONFIG_DIR%\scripts.yaml" echo [] > "%HASS_CONFIG_DIR%\scripts.yaml"
if not exist "%HASS_CONFIG_DIR%\scenes.yaml" echo [] > "%HASS_CONFIG_DIR%\scenes.yaml"

REM Create custom_components junction if it doesn't exist
if not exist "%HASS_CONFIG_DIR%\custom_components" (
    mklink /J "%HASS_CONFIG_DIR%\custom_components" "%CD%\custom_components"
    echo Created junction to custom_components
)

REM Start Home Assistant in development mode
echo Starting Home Assistant with EasyIQ integration...
echo Config directory: %HASS_CONFIG_DIR%
echo Web interface will be available at: http://%HASS_DEV_HOST%:%HASS_DEV_PORT%
echo.
echo Press Ctrl+C to stop the server
echo.

REM Run Home Assistant
python -m homeassistant --config "%HASS_CONFIG_DIR%" --debug

pause