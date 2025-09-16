#!/usr/bin/env python3
"""
POC: Test direct EasyIQ portal authentication using cookies
Based on Chrome DevTools request analysis
"""

import asyncio
import aiohttp
import logging
from datetime import datetime
import json

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_direct_easyiq_auth():
    """Test direct EasyIQ portal authentication using cookies."""
    print("🔬 Testing Direct EasyIQ Portal Authentication")
    print("=" * 60)
    
    # From Chrome DevTools - the exact headers used
    headers = {
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9,da;q=0.8",
        "cache-control": "no-cache",
        "pragma": "no-cache",
        "priority": "u=1, i",
        "request-context": "appId=cid-v1:b81df3e4-a890-4c8d-ad53-861a10ae47b2",
        "sec-ch-ua": '"Chromium";v="140", "Not=A?Brand";v="24", "Microsoft Edge";v="140"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "x-requested-with": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edge/140.0.0.0"
    }
    
    # Test parameters from Chrome DevTools
    params = {
        "loginId": "xxxxx",  # This would need to be dynamic
        "date": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-3] + "Z",
        "activityFilter": "2091719",  # This might be child/class specific
        "courseFilter": "-1",
        "textFilter": "",
        "ownWeekPlan": "false"
    }
    
    async with aiohttp.ClientSession() as session:
        print("Step 1: Testing direct CalendarGetWeekplanEvents endpoint...")
        
        try:
            # First, we need to authenticate to get cookies
            # Let's try the main portal login page first
            print("Attempting to access main portal...")
            
            login_url = "https://skoleportal.easyiqcloud.dk/"
            async with session.get(login_url, headers=headers) as response:
                print(f"Portal access status: {response.status}")
                
                if response.status == 200:
                    print("✅ Portal accessible")
                    # Check if we get redirected to login
                    final_url = str(response.url)
                    print(f"Final URL: {final_url}")
                    
                    if "login" in final_url.lower():
                        print("🔄 Redirected to login - need authentication")
                        # This is where we'd need to implement the actual login
                        # For now, let's see what the login page looks like
                        content = await response.text()
                        print(f"Login page length: {len(content)} characters")
                        
                        # Look for form elements
                        if "form" in content.lower():
                            print("📝 Login form detected")
                        if "username" in content.lower() or "brugernavn" in content.lower():
                            print("👤 Username field detected")
                        if "password" in content.lower() or "adgangskode" in content.lower():
                            print("🔒 Password field detected")
                    else:
                        print("✅ Already authenticated or no login required")
                        
                        # Try the calendar endpoint
                        calendar_url = "https://skoleportal.easyiqcloud.dk/Calendar/CalendarGetWeekplanEvents"
                        async with session.get(calendar_url, headers=headers, params=params) as cal_response:
                            print(f"Calendar endpoint status: {cal_response.status}")
                            
                            if cal_response.status == 200:
                                data = await cal_response.json()
                                print("✅ Calendar data retrieved!")
                                print(f"Data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                            else:
                                print(f"❌ Calendar endpoint failed: {cal_response.status}")
                                error_text = await cal_response.text()
                                print(f"Error: {error_text[:200]}...")
                else:
                    print(f"❌ Portal not accessible: {response.status}")
                    error_text = await response.text()
                    print(f"Error: {error_text[:200]}...")
                    
        except Exception as e:
            print(f"❌ Error: {e}")
            logger.exception("Full error details:")

    print("\n📋 Analysis:")
    print("- The direct EasyIQ portal approach requires cookie-based authentication")
    print("- We need to first authenticate to get session cookies")
    print("- Then we can use those cookies with the CalendarGetWeekplanEvents endpoint")
    print("- This is much simpler than the complex Aula flow currently being used")

if __name__ == "__main__":
    asyncio.run(test_direct_easyiq_auth())