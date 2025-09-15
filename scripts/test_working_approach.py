#!/usr/bin/env python3
"""
POC: Test the working CalendarGetWeekplanEvents approach
Based on the working implementation from ha-config
"""

import asyncio
import aiohttp
import logging
from datetime import datetime
import json
import os
from bs4 import BeautifulSoup

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Constants from working implementation
API = "https://www.aula.dk/api/v"
API_VERSION = "22"
EASYIQ_WEEKPLAN_WIDGET_ID = "0128"

class WorkingEasyIQClient:
    """Test client using the working CalendarGetWeekplanEvents approach."""
    
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.session = None
        self._authenticated = False
        self.apiurl = ""
        self._profiles = []
        self._childuserids = []
        self.widgets = {}
        self.tokens = {}
        
    async def _ensure_session(self):
        """Ensure we have an active session."""
        if self.session is None or self.session.closed:
            connector = aiohttp.TCPConnector(ssl=True)
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                cookie_jar=aiohttp.CookieJar()
            )
        return self.session
    
    async def close(self):
        """Close the session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def login(self) -> bool:
        """Login using the working authentication flow."""
        try:
            logger.info("Starting authentication...")
            session = await self._ensure_session()
            
            # Step 1: Get initial login page
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/112.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "da,en-US;q=0.7,en;q=0.3",
                "DNT": "1",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
            }
            params = {"type": "unilogin"}
            
            async with session.get(
                "https://login.aula.dk/auth/login.php",
                params=params,
                headers=headers,
                ssl=True,
            ) as response:
                logger.debug(f"Login page status: {response.status}")
                if response.status != 200:
                    logger.error(f"Login page returned status {response.status}")
                    return False
                response_text = await response.text()

            _html = BeautifulSoup(response_text, "html.parser")
            if not _html.form:
                logger.error("No form found in login page response")
                return False
            _url = _html.form["action"]
            
            # Step 2: Submit IdP selection
            headers = {
                "Host": "broker.unilogin.dk",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/112.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "da,en-US;q=0.7,en;q=0.3",
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "null",
                "DNT": "1",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-User": "?1",
            }
            data = {"selectedIdp": "uni_idp"}
            
            async with session.post(_url, headers=headers, data=data, ssl=True) as response:
                response_text = await response.text()

            # Step 3: Complete authentication flow
            user_data = {
                "username": self.username,
                "password": self.password,
                "selected-aktoer": "KONTAKT",
            }
            
            redirects = 0
            success = False
            
            while not success and redirects < 10:
                html = BeautifulSoup(response_text, "html.parser")
                if not html.form:
                    logger.error(f"No form found in authentication step {redirects}")
                    break
                url = html.form["action"]

                post_data = {}
                for input_elem in html.find_all("input"):
                    if input_elem.has_attr("name") and input_elem.has_attr("value"):
                        post_data[input_elem["name"]] = input_elem["value"]
                        for key in user_data:
                            if input_elem.has_attr("name") and input_elem["name"] == key:
                                post_data[key] = user_data[key]

                async with session.post(url, data=post_data, ssl=True) as response:
                    response_text = await response.text()
                    if str(response.url) == "https://www.aula.dk:443/portal/":
                        success = True
                redirects += 1

            if not success:
                logger.error(f"Authentication failed after {redirects} redirects")
                return False

            # Step 4: Find API version
            self.apiurl = API + API_VERSION
            apiver = int(API_VERSION)
            api_success = False
            
            while not api_success:
                logger.debug(f"Trying API at {self.apiurl}")
                async with session.get(
                    self.apiurl + "?method=profiles.getProfilesByLogin", ssl=True
                ) as ver:
                    if ver.status == 410:
                        logger.debug(f"API version {apiver} returned 410, trying newer version")
                        apiver += 1
                    elif ver.status == 403:
                        logger.error("Access denied - check credentials")
                        return False
                    elif ver.status == 200:
                        ver_json = await ver.json()
                        self._profiles = ver_json["data"]["profiles"]
                        api_success = True
                    self.apiurl = API + str(apiver)

            logger.info(f"Found API on {self.apiurl}")

            # Step 5: Get profile context
            async with session.get(
                self.apiurl + "?method=profiles.getProfileContext&portalrole=guardian",
                ssl=True,
            ) as profile_response:
                profile_json = await profile_response.json()
                self._profilecontext = profile_json["data"]["institutionProfile"]["relations"]
            
            # Extract children data
            self._childuserids = []
            for profile in self._profiles:
                for child in profile["children"]:
                    self._childuserids.append(str(child["userId"]))
            
            logger.info(f"Found {len(self._childuserids)} children: {self._childuserids}")
            
            self._authenticated = True
            return True
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False
    
    async def get_token(self, widget_id: str) -> str:
        """Get authentication token for widget."""
        if widget_id in self.tokens:
            token, timestamp = self.tokens[widget_id]
            # Check if token is still valid (1 minute cache)
            current_time = datetime.now()
            if (current_time - timestamp).total_seconds() < 60:
                logger.debug(f"Reusing existing token for widget {widget_id}")
                return token
        
        logger.debug(f"Requesting new token for widget {widget_id}")
        try:
            session = await self._ensure_session()
            async with session.get(
                self.apiurl + f"?method=aulaToken.getAulaToken&widgetId={widget_id}",
                ssl=True,
            ) as response:
                response_json = await response.json()
                bearer_token = response_json["data"]

            token = "Bearer " + str(bearer_token)
            self.tokens[widget_id] = (token, datetime.now())
            return token
        except Exception as err:
            logger.error(f"Failed to get token for widget {widget_id}: {err}")
            return ""
    
    async def test_calendar_events(self, child_id: str):
        """Test the CalendarGetWeekplanEvents endpoint."""
        try:
            # Get authentication token
            token = await self.get_token(EASYIQ_WEEKPLAN_WIDGET_ID)
            if not token:
                logger.error("Failed to get token for EasyIQ widget")
                return None
            
            # Prepare the request exactly like working implementation
            url = "https://skoleportal.easyiqcloud.dk/Calendar/CalendarGetWeekplanEvents"
            
            params = {
                "loginId": "xxxxx",  # From working implementation
                "date": datetime.now().isoformat() + "Z",
                "activityFilter": "2091719",  # From working implementation
                "courseFilter": "-1",
                "textFilter": "",
                "ownWeekPlan": "false"
            }
            
            headers = {
                "accept": "*/*",
                "accept-language": "en-US,en;q=0.9,da;q=0.8",
                "authorization": token,
                "cache-control": "no-cache",
                "pragma": "no-cache",
                "priority": "u=1, i",
                "referer": "https://skoleportal.easyiqcloud.dk/UgeplanWidget",
                "sec-ch-ua": '"Chromium";v="140", "Not=A?Brand";v="24", "Microsoft Edge";v="140"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edge/140.0.0.0",
                "x-requested-with": "XMLHttpRequest",
                "x-child": child_id,
                "x-childfilter": ",".join(self._childuserids),
                "x-institutionfilter": "731003,G20313",  # From working implementation
                "x-login": self.username,
                "x-userprofile": "guardian",
                "x-widgetinstanceid": "168810a-dafa-40a6-9a12-18cd4654939e"
            }
            
            logger.info(f"Testing CalendarGetWeekplanEvents endpoint...")
            logger.debug(f"URL: {url}")
            logger.debug(f"Params: {params}")
            
            session = await self._ensure_session()
            async with session.get(url, params=params, headers=headers, ssl=True) as response:
                logger.info(f"Response status: {response.status}")
                
                if response.status == 200:
                    try:
                        events = await response.json()
                        logger.info(f"✅ Successfully retrieved {len(events)} calendar events")
                        
                        # Analyze event types
                        event_types = {}
                        for event in events:
                            item_type = event.get("itemType", "unknown")
                            event_types[item_type] = event_types.get(item_type, 0) + 1
                        
                        logger.info(f"Event types found: {event_types}")
                        
                        # Show sample events
                        for i, event in enumerate(events[:3]):
                            logger.info(f"Sample event {i+1}: {json.dumps(event, indent=2)}")
                        
                        return events
                    except Exception as e:
                        logger.error(f"Failed to parse JSON response: {e}")
                        response_text = await response.text()
                        logger.debug(f"Response text: {response_text[:500]}...")
                        return None
                else:
                    logger.error(f"❌ Calendar events API returned status {response.status}")
                    response_text = await response.text()
                    logger.debug(f"Error response: {response_text[:500]}...")
                    return None
                    
        except Exception as err:
            logger.error(f"Failed to get calendar events: {err}")
            return None

async def main():
    """Test the working CalendarGetWeekplanEvents approach."""
    print("🔬 Testing Working CalendarGetWeekplanEvents Approach")
    print("=" * 60)
    
    # Load credentials
    username = os.getenv('EASYIQ_USERNAME')
    password = os.getenv('EASYIQ_PASSWORD', 'test_password')
    
    print(f"Testing with username: {username}")
    
    client = WorkingEasyIQClient(username, password)
    
    try:
        # Test authentication
        print("\n📝 Step 1: Testing authentication...")
        if not await client.login():
            print("❌ Authentication failed")
            return
        
        print("✅ Authentication successful!")
        print(f"Found {len(client._childuserids)} children: {client._childuserids}")
        
        # Test calendar events for first child
        if client._childuserids:
            child_id = client._childuserids[0]
            print(f"\n📅 Step 2: Testing CalendarGetWeekplanEvents for child {child_id}...")
            
            events = await client.test_calendar_events(child_id)
            
            if events:
                print("✅ CalendarGetWeekplanEvents working!")
                
                # Filter and analyze weekplan vs homework
                weekplan_events = [e for e in events if e.get("itemType") == 9]
                homework_events = [e for e in events if e.get("itemType") == 4]
                
                print(f"📚 Weekplan events (itemType 9): {len(weekplan_events)}")
                print(f"📝 Homework events (itemType 4): {len(homework_events)}")
                
                print("\n🎉 SUCCESS: The working approach is confirmed!")
                print("This approach can replace the failing authentication in the current client.")
            else:
                print("❌ CalendarGetWeekplanEvents failed")
        else:
            print("❌ No children found")
            
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())