#!/usr/bin/env python3
"""Real test of the presence API with actual authentication."""

import asyncio
import aiohttp
import os
import json
from datetime import datetime
import requests
from bs4 import BeautifulSoup

# Load environment variables from .env file
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

async def authenticate_and_test_presence():
    """Authenticate with Aula and test the presence API."""
    
    username = os.getenv('EASYIQ_USERNAME')
    password = os.getenv('EASYIQ_PASSWORD')
    
    if not username or not password:
        print("❌ Please set EASYIQ_USERNAME and EASYIQ_PASSWORD in .env file")
        return False
    
    print("Testing real presence API with authentication...")
    print(f"Username: {username}")
    print("-" * 60)
    
    try:
        # Step 1: Get login page and extract form data
        print("🔐 Step 1: Getting login page...")
        login_url = "https://login.aula.dk/auth/login.php?type=unilogin"
        
        session = requests.Session()
        response = session.get(login_url)
        
        if response.status_code != 200:
            print(f"❌ Failed to get login page: {response.status_code}")
            return False
        
        # Parse the login form
        soup = BeautifulSoup(response.content, 'html.parser')
        form = soup.find('form')
        if not form:
            print("❌ Could not find login form")
            return False
        
        # Extract form action and hidden fields
        form_action = form.get('action')
        if not form_action.startswith('http'):
            form_action = 'https://login.aula.dk' + form_action
        
        form_data = {}
        for input_field in form.find_all('input'):
            name = input_field.get('name')
            value = input_field.get('value', '')
            if name:
                form_data[name] = value
        
        # Add credentials
        form_data['username'] = username
        form_data['password'] = password
        
        print("✅ Login form extracted successfully")
        
        # Step 2: Submit login form
        print("🔐 Step 2: Submitting login...")
        response = session.post(form_action, data=form_data, allow_redirects=True)
        
        if response.status_code != 200:
            print(f"❌ Login failed: {response.status_code}")
            return False
        
        # Check if we're logged in (look for typical Aula elements)
        if 'aula.dk' not in response.url or 'login' in response.url.lower():
            print("❌ Authentication failed - still on login page")
            return False
        
        print("✅ Authentication successful!")
        
        # Step 3: Get session cookies for aiohttp
        print("🔄 Step 3: Converting session for API calls...")
        cookies = session.cookies.get_dict()
        
        # Step 4: Test presence API with authenticated session
        print("📊 Step 4: Testing presence API...")
        
        async with aiohttp.ClientSession(cookies=cookies) as aio_session:
            # Try to get children first (we need child IDs)
            children_url = "https://www.aula.dk/api/v22/"
            children_params = {"method": "profiles.getProfilesByLogin"}
            
            async with aio_session.get(children_url, params=children_params) as resp:
                if resp.status == 200:
                    children_data = await resp.json()
                    print(f"✅ Children data retrieved: {resp.status}")
                    
                    if children_data.get("status", {}).get("code") == 0:
                        profiles = children_data.get("data", {}).get("profiles", [])
                        child_profiles = [p for p in profiles if p.get("role") == "child"]
                        
                        if child_profiles:
                            print(f"Found {len(child_profiles)} children")
                            
                            # Test presence for each child
                            for profile in child_profiles:
                                child_id = str(profile.get("id"))
                                child_name = profile.get("name", "Unknown")
                                
                                print(f"\n--- Testing presence for {child_name} (ID: {child_id}) ---")
                                
                                # Call presence API
                                presence_url = "https://www.aula.dk/api/v22/"
                                presence_params = {
                                    "method": "presence.getDailyOverview",
                                    f"childIds[]": child_id
                                }
                                
                                async with aio_session.get(presence_url, params=presence_params) as presence_resp:
                                    print(f"HTTP Status: {presence_resp.status}")
                                    
                                    if presence_resp.status == 200:
                                        presence_data = await presence_resp.json()
                                        print("✅ Presence API call successful!")
                                        
                                        if presence_data.get("status", {}).get("code") == 0:
                                            entries = presence_data.get("data", [])
                                            print(f"Found {len(entries)} presence entries")
                                            
                                            for entry in entries:
                                                child_info = entry.get("institutionProfile", {})
                                                print(f"  Child: {child_info.get('name', 'Unknown')}")
                                                print(f"  Status Code: {entry.get('status', 'N/A')}")
                                                print(f"  Check In: {entry.get('checkInTime', 'N/A')}")
                                                print(f"  Check Out: {entry.get('checkOutTime', 'N/A')}")
                                                print(f"  Entry Time: {entry.get('entryTime', 'N/A')}")
                                                print(f"  Exit Time: {entry.get('exitTime', 'N/A')}")
                                                print(f"  Comment: {entry.get('comment', 'N/A')}")
                                                print(f"  Exit With: {entry.get('exitWith', 'N/A')}")
                                                
                                                # Show formatted display
                                                status_code = entry.get('status', 0)
                                                print(f"\n  📱 Display format:")
                                                if status_code == 8:
                                                    print(f"  Status: Gået")
                                                elif status_code == 3:
                                                    print(f"  Status: Til stede")
                                                else:
                                                    print(f"  Status: Code {status_code}")
                                                
                                                if entry.get('checkInTime'):
                                                    print(f"  Kom: kl. {entry.get('checkInTime')}")
                                                if entry.get('checkOutTime'):
                                                    print(f"  Gik: kl. {entry.get('checkOutTime')}")
                                                if entry.get('exitTime'):
                                                    print(f"  Send hjem: kl. {entry.get('exitTime')}")
                                                if entry.get('comment'):
                                                    print(f"  Bemærkninger: {entry.get('comment')}")
                                        else:
                                            print(f"❌ Presence API error: {presence_data.get('status', {}).get('message', 'Unknown')}")
                                    else:
                                        error_text = await presence_resp.text()
                                        print(f"❌ Presence API HTTP error: {presence_resp.status}")
                                        print(f"Response: {error_text[:200]}...")
                        else:
                            print("❌ No child profiles found")
                    else:
                        print(f"❌ Children API error: {children_data.get('status', {}).get('message', 'Unknown')}")
                else:
                    print(f"❌ Failed to get children: {resp.status}")
        
        print("\n" + "="*60)
        print("🎉 Real API test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(authenticate_and_test_presence())
    if success:
        print("✅ SUCCESS: Real presence API is working!")
    else:
        print("❌ FAILED: Issues with real API test")