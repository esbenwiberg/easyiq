#!/usr/bin/env python3
"""
Final test replicating the EXACT Chrome DevTools request that returns JSON.
Key insight: The request is made FROM the UgeplanWidget page with bearer token + custom headers.
"""

import requests
import os
import sys
import json
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_credentials():
    """Load credentials from .env file."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value.strip('"\'')
    
    username = os.getenv('EASYIQ_USERNAME')
    password = os.getenv('EASYIQ_PASSWORD')
    
    if not password:
        print("❌ EASYIQ_PASSWORD not found in environment")
        sys.exit(1)
    
    return username, password

def main():
    """Test the CalendarGetWeekplanEvents with EXACT Chrome DevTools approach."""
    print("🔬 Final Test: Exact Chrome DevTools Replication")
    print("=" * 70)
    
    # Use the working Aula client for authentication
    sys.path.append('aula/custom_components/aula')
    from client import Client
    
    username, password = load_credentials()
    
    # Use the working Aula client to get authenticated session
    print(f"Testing with username: {username}")
    client = Client(username, password, True, True, True)
    
    if not client.login():
        print("❌ Authentication failed")
        return
    
    print("✅ Authentication successful!")
    print(f"API URL: {client.apiurl}")
    print(f"Profiles: {len(client._profiles)}")
    
    # Get EasyIQ token using the working Aula client
    EASYIQ_UGEPLAN_WIDGET_ID = "0128"
    
    try:
        # Use the Aula client's method to get EasyIQ token
        token = client.get_easyiq_token(EASYIQ_UGEPLAN_WIDGET_ID)
        if not token:
            print("❌ Failed to get EasyIQ token")
            return
        
        print(f"✅ Got EasyIQ token: {token[:30]}...")
        
        # Ensure token has Bearer prefix
        if not token.startswith("Bearer "):
            token = f"Bearer {token}"
            
    except Exception as e:
        print(f"❌ Error getting EasyIQ token: {e}")
        return
    
    # Now replicate the EXACT Chrome DevTools request
    url = "https://skoleportal.easyiqcloud.dk/Calendar/CalendarGetWeekplanEvents"
    
    # Parameters from Chrome DevTools
    params = {
        "loginId": "xxxxx",  # From Chrome DevTools
        "date": "2025-09-15T00:00:00.000Z",  # Simplified date
        "activityFilter": "2091719",
        "courseFilter": "-1",
        "textFilter": "",
        "ownWeekPlan": "false"
    }
    
    # Headers EXACTLY like Chrome DevTools
    headers = {
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "en-US,en;q=0.9,da;q=0.8",
        "authorization": token,  # Bearer token
        "cache-control": "no-cache",
        "pragma": "no-cache",
        "priority": "u=1, i",
        "referer": "https://skoleportal.easyiqcloud.dk/UgeplanWidget",  # KEY: Called FROM widget
        "sec-ch-ua": '"Chromium";v="140", "Not=A?Brand";v="24", "Microsoft Edge";v="140"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edge/140.0.0.0",
        "x-requested-with": "XMLHttpRequest",
        # Custom headers from Chrome DevTools
        "x-userprofile": "guardian",
        "x-widgetinstanceid": "168810a-dafa-40a6-9a12-18cd4654939e"  # From Chrome DevTools
    }
    
    print(f"\nTesting: {url}")
    print(f"Key insight: Using bearer token + custom headers + referer from UgeplanWidget")
    
    try:
        # Use the authenticated session from Aula client
        response = client._session.get(url, params=params, headers=headers, verify=True)
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type', 'unknown')}")
        print(f"Content-Length: {len(response.text)} characters")
        
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')
            
            if 'json' in content_type.lower():
                print("\n" + "="*70)
                print("🎉 BREAKTHROUGH! Got JSON response!")
                print("="*70)
                
                try:
                    data = response.json()
                    print(json.dumps(data, indent=2, ensure_ascii=False))
                    print("="*70)
                    
                    print(f"\n📋 SUCCESS! The complete solution:")
                    print(f"- Authentication: Aula session + Bearer token")
                    print(f"- Custom headers: X-Child, X-Childfilter, X-Institutionfilter, etc.")
                    print(f"- Referer: Must be called FROM UgeplanWidget page")
                    print(f"- Response: JSON with schedule data")
                    print(f"- Data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                    
                    return True
                    
                except json.JSONDecodeError as e:
                    print(f"❌ JSON decode error: {e}")
                    print(f"Raw response: {response.text[:500]}...")
            else:
                print(f"❌ Still not JSON. Content-Type: {content_type}")
                print(f"Response preview: {response.text[:500]}...")
        else:
            print(f"❌ Failed with status {response.status_code}")
            print(f"Response: {response.text[:500]}...")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
    
    return False

if __name__ == "__main__":
    success = main()
    if success:
        print(f"\n🎉 COMPLETE SUCCESS! We've cracked the EasyIQ API!")
        print("The solution requires: Bearer token + Custom headers + Correct referer")
    else:
        print(f"\n❌ Still working on the complete solution...")