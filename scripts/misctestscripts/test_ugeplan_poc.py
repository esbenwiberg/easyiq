#!/usr/bin/env python3
"""
POC script to test the ugeplan (weekplan) API endpoint from Chrome DevTools.
This tests the specific CalendarGetWeekplanEvents endpoint you captured.
"""

import sys
import os
import requests
import json
from datetime import datetime

# Add the custom_components directory to the path
sys.path.append('custom_components/aula_easyiq')

from client import EasyIQClient

def test_ugeplan_api():
    """Test the ugeplan API endpoint with authentication."""
    print("🔬 Testing Ugeplan API POC")
    print("=" * 60)
    
    # Load credentials
    username = os.getenv('EASYIQ_USERNAME')
    password = os.getenv('EASYIQ_PASSWORD', 'test_password')
    
    print(f"Testing with username: {username}")
    
    try:
        # Initialize and authenticate client
        client = EasyIQClient(username, password)
        client.login()
        print("✅ Authentication successful!")
        print(f"Profiles found: {len(client._profiles)}")
        print(f"Children found: {len(client.children)}")
        
        if not client.children:
            print("❌ No children found")
            print("Debug info:")
            print(f"  - Profiles: {client._profiles}")
            print(f"  - Children data: {client._children_data}")
            return
            
        child = client.children[0]
        child_id = child['id']
        print(f"Testing with child: {child['name']} (ID: {child_id})")
        
        # Get the EasyIQ token for widget 0128 (calendar widget)
        if '0128' not in client._widget_tokens:
            print("🔑 Requesting new token for widget 0128...")
            client._get_widget_token('0128')
        
        token = client._widget_tokens.get('0128')
        if not token:
            print("❌ Failed to get widget token")
            return
            
        print(f"✅ Got widget token: {token[:20]}...")
        
        # Test the exact endpoint from Chrome DevTools
        url = "https://skoleportal.easyiqcloud.dk/Calendar/CalendarGetWeekplanEvents"
        
        # Parameters from your Chrome DevTools capture
        params = {
            'loginId': 'xxxxxx',  # From your DevTools capture
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
            'request-context': 'appId=cid-v1:b81df3e4-a890-4c8d-ad53-861a10ae47b2',
            'request-id': '|pRlmn.ZPWZW',
            'sec-ch-ua': '"Chromium";v="140", "Not=A?Brand";v="24", "Microsoft Edge";v="140"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
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
        session.cookies.update(client._session.cookies)
        
        # Make the request
        response = session.get(url, params=params, headers=headers)
        
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
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
                        
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse JSON: {e}")
                print(f"Response content: {response.text[:500]}...")
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print(f"Response: {response.text[:500]}...")
            
        # Now test with our current working approach for comparison
        print("\n🔄 Testing our current working approach...")
        try:
            import asyncio
            weekplan_data = asyncio.run(client.get_weekplan(child_id))
            print(f"✅ Our approach got {len(weekplan_data.get('raw_data', []))} events")
            
            # Compare the approaches
            print("\n📊 Comparison:")
            print(f"Chrome DevTools approach: {response.status_code} status")
            print(f"Our current approach: {len(weekplan_data.get('raw_data', []))} events")
            
        except Exception as e:
            print(f"❌ Our approach failed: {e}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    
    # Run the sync parts
    test_ugeplan_api()