#!/usr/bin/env python3
"""Script to help restart the EasyIQ integration in Home Assistant."""

import requests
import json
import sys

def restart_integration():
    """Restart the EasyIQ integration."""
    # You'll need to configure these for your Home Assistant instance
    ha_url = "http://localhost:8123"  # Change to your HA URL
    token = input("Enter your Home Assistant Long-Lived Access Token: ")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        # Get all config entries
        response = requests.get(f"{ha_url}/api/config/config_entries", headers=headers)
        if response.status_code != 200:
            print(f"Failed to get config entries: {response.status_code}")
            return
        
        config_entries = response.json()
        
        # Find EasyIQ entries
        aula-easyiq_entries = [entry for entry in config_entries if entry.get("domain") == "aula-easyiq"]
        
        if not aula-easyiq_entries:
            print("No EasyIQ integration entries found")
            return
        
        print(f"Found {len(aula-easyiq_entries)} EasyIQ integration(s)")
        
        # Reload each EasyIQ entry
        for entry in aula-easyiq_entries:
            entry_id = entry["entry_id"]
            print(f"Reloading EasyIQ integration: {entry_id}")
            
            reload_response = requests.post(
                f"{ha_url}/api/config/config_entries/{entry_id}/reload",
                headers=headers
            )
            
            if reload_response.status_code == 200:
                print(f"✅ Successfully reloaded integration {entry_id}")
            else:
                print(f"❌ Failed to reload integration {entry_id}: {reload_response.status_code}")
                print(reload_response.text)
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    restart_integration()