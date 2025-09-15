# 🔧 Debugging the Async HTTP Conversion

This document explains how to debug and test the EasyIQ Home Assistant integration during development, specifically focusing on the async HTTP conversion process.

## 🚀 Quick Debug Workflow

### 1. Update Integration in Docker
```bash
python scripts/update_integration.py
```

This script:
- Copies all integration files to the Docker container
- Restarts Home Assistant automatically
- Shows status and next steps

### 2. Wait for Home Assistant to Start
```bash
# Wait 30-60 seconds for full startup
timeout 15
```

### 3. Check Integration Logs
```powershell
# Get the latest 15 EasyIQ-related log entries
docker logs homeassistant | Select-String -Pattern "easyiq" | Select-Object -Last 15
```
