#!/usr/bin/env python3
"""
Simple POC to test the exact Chrome DevTools request you captured.
This uses our working authentication and then tests the specific endpoint.
"""

import sys
import os
import requests
import json
from datetime import datetime

# Add the custom_components directory to the path
sys.path.append('custom_components/easyiq')

from client import EasyIQClient

def test_chrome_devtools_request():
    """Test the exact Chrome DevTools request with our working authentication."""
    print("🔬 Testing Chrome DevTools Request POC")
    print("=" * 60)
    
    # Load credentials
    username = os.getenv('EASYIQ_USERNAME', 'test_user')
    password = os.getenv('EASYIQ_PASSWORD', 'test_password')
    
    print(f"Testing with username: {username}")
    
    try:
        # Use our working authentication approach
        client = EasyIQClient(username, password)
        client.login()
        print("✅ Authentication successful!")
        
        # Test the exact endpoint from Chrome DevTools
        url = "https://skoleportal.easyiqcloud.dk/Calendar/CalendarGetWeekplanEvents"
        
        # Parameters from your Chrome DevTools capture
        params = {
            'loginId': 'xxxxx',  # From your DevTools capture
            'date': '2025-09-15T06:54:24.612Z',  # From your DevTools capture
            'activityFilter': '2091719',  # From your DevTools capture
            'courseFilter': '-1',
            'textFilter': '',
            'ownWeekPlan': 'false'
        }
        
        # Headers from your Chrome DevTools capture
        headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9,da;q=0.8',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'x-requested-with': 'XMLHttpRequest',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edge/140.0.0.0'
        }
        
        print("\n🌐 Testing Chrome DevTools endpoint...")
        print(f"URL: {url}")
        print(f"Params: {params}")
        
        # Create a session with cookies from our authenticated client
        session = requests.Session()
        if hasattr(client, '_session') and client._session:
            session.cookies.update(client._session.cookies)
            print("✅ Using authenticated session cookies")
        else:
            print("⚠️ No authenticated session found")
        
        # Make the request
        print("\n📡 Making request...")
        response = session.get(url, params=params, headers=headers)
        
        print(f"Response status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type', 'N/A')}")
        print(f"Content-Length: {response.headers.get('content-length', 'N/A')}")
        
        if response.status_code == 200:
            try:
                # Try to parse JSON
                data = response.json()
                print(f"✅ Successfully got JSON response with {len(data)} items")
                
                if data:
                    print("\n📋 Sample events:")
                    for i, event in enumerate(data[:3]):
                        print(f"  Event {i+1}:")
                        print(f"    Title: {event.get('title', 'N/A')}")
                        print(f"    Course: {event.get('courses', 'N/A')}")
                        print(f"    Start: {event.get('start', 'N/A')}")
                        print(f"    End: {event.get('end', 'N/A')}")
                        print(f"    Type: {event.get('itemType', 'N/A')}")
                        print()
                else:
                    print("📋 No events returned")
                        
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse JSON: {e}")
                print(f"Response content (first 500 chars): {response.text[:500]}...")
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print(f"Response headers: {dict(response.headers)}")
            print(f"Response content (first 500 chars): {response.text[:500]}...")
            
        # Now test with different loginId values to see if that's the issue
        print("\n🔄 Testing with different loginId values...")
        
        # Try with our current user's ID if we can find it
        if hasattr(client, '_children_data') and client._children_data:
            for child_id, child_data in client._children_data.items():
                print(f"\n🧪 Testing with loginId: {child_data.get('id', child_id)}")
                test_params = params.copy()
                test_params['loginId'] = str(child_data.get('id', child_id))
                
                test_response = session.get(url, params=test_params, headers=headers)
                print(f"  Status: {test_response.status_code}")
                
                if test_response.status_code == 200:
                    try:
                        test_data = test_response.json()
                        print(f"  ✅ Got {len(test_data)} events")
                        break
                    except:
                        print(f"  ❌ Failed to parse JSON")
                else:
                    print(f"  ❌ Failed with status {test_response.status_code}")
        else:
            print("  No child data available for testing different loginId values")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_chrome_devtools_request()