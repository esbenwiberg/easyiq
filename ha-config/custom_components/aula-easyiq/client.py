"""EasyIQ API client with working CalendarGetWeekplanEvents implementation."""
from __future__ import annotations

import asyncio
import logging
from typing import Any
import datetime
import json

try:
    import aiohttp
    from bs4 import BeautifulSoup
    import pytz
except ImportError:
    # For testing without Home Assistant dependencies
    aiohttp = None
    BeautifulSoup = None
    pytz = None

# Also import requests for synchronous authentication (working approach)
try:
    import requests
    from bs4 import BeautifulSoup as BS4
except ImportError:
    requests = None
    BS4 = None

try:
    from .const import (
        API,
        API_VERSION,
        EASYIQ_API,
        EASYIQ_WEEKPLAN_WIDGET_ID,
        EASYIQ_HOMEWORK_WIDGET_ID,
        EASYIQ_WIDGETS,
        PRESENCE_STATUS,
    )
except ImportError:
    # For standalone testing
    API = "https://www.aula.dk/api/v"
    API_VERSION = "22"
    EASYIQ_API = "https://api.easyiqcloud.dk/api/aula"
    EASYIQ_WEEKPLAN_WIDGET_ID = "0128"
    EASYIQ_HOMEWORK_WIDGET_ID = "0142"
    EASYIQ_WIDGETS = {
        "weekplan": "0128",
        "homework": "0142"
    }
    PRESENCE_STATUS = {
        0: "IKKE KOMMET",      # Not arrived
        1: "SYG",              # Sick
        2: "FERIE/FRI",        # Holiday/Free
        3: "KOMMET/TIL STEDE", # Arrived/Present
        4: "PÅ TUR",           # On trip
        5: "SOVER",            # Sleeping
        8: "HENTET/GÅET",      # Picked up/Gone
    }

_LOGGER = logging.getLogger(__name__)


class EasyIQClient:
    """Client for communicating with EasyIQ API using the working CalendarGetWeekplanEvents approach."""

    def __init__(self, username: str, password: str) -> None:
        """Initialize the client."""
        self.username = username
        self.password = password
        self.session: aiohttp.ClientSession | None = None
        self._session: requests.Session | None = None  # Synchronous session for auth
        self._authenticated = False
        
        # Authentication data
        self._profiles = []
        self._profile_context = []
        self._institution_profiles = []
        self._children_data = {}
        self.api_url = ""
        self.apiurl = ""  # For compatibility with Aula client
        self.widgets = {}
        self.tokens = {}
        
        # Data storage
        self.children = []
        self._childuserids = []
        self._childnames = {}
        self._childids = []
        self.unread_messages = 0
        self.message = {}
        self.weekplan_data = {}
        self.homework_data = {}
        self.presence_status = {}  # Stores presence status codes (0-8)
        self.presence_data = {}    # Stores detailed presence information

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure we have an active aiohttp session."""
        if self.session is None or self.session.closed:
            # Create session with cookie jar to maintain authentication
            connector = aiohttp.TCPConnector(ssl=True)
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                cookie_jar=aiohttp.CookieJar()
            )
        return self.session

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()

    def login(self) -> bool:
        """Login using the proven working Aula authentication approach."""
        if requests is None or BS4 is None:
            _LOGGER.error("requests or BeautifulSoup not available - cannot authenticate")
            return False
        
        try:
            _LOGGER.debug("Logging in")
            self._session = requests.Session()
            
            # Step 1: Get initial login page (simplified approach from working Aula client)
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
            response = self._session.get(
                "https://login.aula.dk/auth/login.php",
                params=params,
                headers=headers,
                verify=True,
            )

            _html = BS4(response.text, "lxml")
            _url = _html.form["action"]
            
            # Step 2: Submit IdP selection (simplified)
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
            response = self._session.post(_url, headers=headers, data=data, verify=True)

            # Step 3: Complete authentication flow (simplified from working Aula client)
            user_data = {
                "username": self.username,
                "password": self.password,
                "selected-aktoer": "KONTAKT",
            }
            redirects = 0
            success = False
            url = ""
            while success == False and redirects < 10:
                html = BS4(response.text, "lxml")
                url = html.form["action"]

                post_data = {}
                for input_elem in html.find_all("input"):
                    if input_elem.has_attr("name") and input_elem.has_attr("value"):
                        post_data[input_elem["name"]] = input_elem["value"]
                        for key in user_data:
                            if input_elem.has_attr("name") and input_elem["name"] == key:
                                post_data[key] = user_data[key]

                response = self._session.post(url, data=post_data, verify=True)
                if response.url == "https://www.aula.dk:443/portal/":
                    success = True
                redirects += 1

            if not success:
                _LOGGER.error(f"Authentication failed after {redirects} redirects")
                return False

            # Step 4: Find and validate API version
            self.apiurl = API + API_VERSION
            self.api_url = self.apiurl
            apiver = int(API_VERSION)
            api_success = False
            while api_success == False:
                _LOGGER.debug("Trying API at " + self.apiurl)
                ver = self._session.get(
                    self.apiurl + "?method=profiles.getProfilesByLogin", verify=True
                )
                if ver.status_code == 410:
                    _LOGGER.debug(
                        "API was expected at "
                        + self.apiurl
                        + " but responded with HTTP 410. The integration will automatically try a newer version and everything may work fine."
                    )
                    apiver += 1
                elif ver.status_code == 403:
                    _LOGGER.error("Access denied - check credentials")
                    return False
                elif ver.status_code == 200:
                    ver_json = ver.json()
                    self._profiles = ver_json["data"]["profiles"]
                    api_success = True
                self.apiurl = API + str(apiver)
                self.api_url = self.apiurl
            _LOGGER.debug("Found API on " + self.apiurl)

            # Step 5: Get profile context and children
            profile_response = self._session.get(
                self.apiurl + "?method=profiles.getProfileContext&portalrole=guardian",
                verify=True,
            )
            profile_json = profile_response.json()
            self._profilecontext = profile_json["data"]["institutionProfile"]["relations"]
            
            # Extract children data and institution profiles for compatibility
            self._children_data = {}
            self._childnames = {}
            self._childuserids = []
            self._childids = []
            self.children = []
            
            # Extract institution profiles dynamically from auth response
            for profile in self._profiles:
                # Extract institution codes from institutionProfiles
                for institutioncode in profile["institutionProfiles"]:
                    institution_code = str(institutioncode["institutionCode"])
                    if institution_code not in self._institution_profiles:
                        self._institution_profiles.append(institution_code)
                
                for child in profile["children"]:
                    # Store both userId and id for different API calls
                    user_id = child["userId"]
                    child_id = child["id"]
                    child_name = child["name"]
                    
                    # For get_children() method (uses userId)
                    self._childuserids.append(str(user_id))
                    self._childnames[str(user_id)] = child_name
                    
                    # For calendar API calls (uses id)
                    self._childids.append(str(child_id))
                    
                    # Store complete child data
                    self._children_data[str(user_id)] = {
                        "id": child_id,
                        "userId": user_id,
                        "name": child_name
                    }
                    
                    self.children.append({
                        "id": str(user_id),  # Use userId as primary ID
                        "name": child_name
                    })

            _LOGGER.info(f"Found {len(self.children)} children: {[c['name'] for c in self.children]}")
            _LOGGER.debug(f"Institution codes: {self._institution_profiles}")
            
            self._authenticated = True
            return True
            
        except Exception as e:
            _LOGGER.error(f"Authentication failed: {e}")
            return False

    def get_widgets(self) -> dict[str, str]:
        """Get available widgets."""
        if not self._authenticated:
            _LOGGER.warning("Not authenticated - cannot fetch widgets")
            return {}
        
        try:
            response = self._session.get(
                self.apiurl + "?method=aulaToken.getWidgets", verify=True
            )
            if response.status_code == 200:
                widgets_json = response.json()
                widgets_data = widgets_json.get("data", {})
                
                # Store widgets
                self.widgets = {}
                for widget in widgets_data:
                    widget_id = widget.get("widgetId", "")
                    widget_name = widget.get("widgetName", "")
                    if widget_id and widget_name:
                        self.widgets[widget_id] = widget_name
                
                _LOGGER.debug(f"Found {len(self.widgets)} widgets: {self.widgets}")
                return self.widgets
            else:
                _LOGGER.error(f"Failed to get widgets: {response.status_code}")
                return {}
                
        except Exception as err:
            _LOGGER.error(f"Failed to get widgets: {err}")
            return {}

    def get_token(self, widget_id: str) -> str:
        """Get authentication token for widget."""
        if not self._authenticated:
            _LOGGER.warning("Not authenticated - cannot get token")
            return ""
        
        # Check if we have a cached token
        if widget_id in self.tokens:
            token, timestamp = self.tokens[widget_id]
            current_time = datetime.datetime.now(pytz.utc) if pytz else datetime.datetime.now()
            if (current_time - timestamp).total_seconds() < 60:  # 1 minute cache
                _LOGGER.debug(f"Reusing existing token for widget {widget_id}")
                return token
        
        _LOGGER.debug(f"Requesting new token for widget {widget_id}")
        try:
            response = self._session.get(
                self.apiurl + f"?method=aulaToken.getAulaToken&widgetId={widget_id}",
                verify=True,
            )
            if response.status_code == 200:
                response_json = response.json()
                bearer_token = response_json["data"]
                
                token = "Bearer " + str(bearer_token)
                timestamp = datetime.datetime.now(pytz.utc) if pytz else datetime.datetime.now()
                self.tokens[widget_id] = (token, timestamp)
                return token
            else:
                _LOGGER.error(f"Failed to get token for widget {widget_id}: {response.status_code}")
                return ""
        except Exception as err:
            _LOGGER.error(f"Failed to get token for widget {widget_id}: {err}")
            return ""

    async def _get_calendar_events(self, child_id: str, weeks_ahead: int = 0) -> list[dict[str, Any]]:
        """Get calendar events using the working CalendarGetWeekplanEvents endpoint.
        
        This is the BREAKTHROUGH method that uses the exact Chrome DevTools approach.
        
        Args:
            child_id: The child's user ID
            weeks_ahead: Number of weeks ahead to fetch (0 = current week, 1 = next week, etc.)
        """
        try:
            # Run the synchronous calendar request in an executor to avoid blocking
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._sync_get_calendar_events, child_id, weeks_ahead)
        except Exception as err:
            _LOGGER.error("Failed to get calendar events: %s", err)
            return []

    async def get_calendar_events_for_business_days(self, child_id: str, days: int = 5, weeks_ahead: int = 0) -> list[dict[str, Any]]:
        """Get calendar events for the next N business days (Monday-Friday).
        
        Args:
            child_id: The child's user ID
            days: Number of business days to fetch (default: 5)
            weeks_ahead: Number of weeks ahead to start from (0=current week, 1=next week, etc.)
        """
        try:
            all_events = []
            current_date = datetime.datetime.now()
            
            # Calculate how many weeks we need to fetch to cover the business days
            # Start from the specified weeks_ahead and fetch additional weeks if needed
            for week_offset in range(weeks_ahead, weeks_ahead + 3):  # Fetch 3 weeks starting from weeks_ahead
                events = await self._get_calendar_events(child_id, week_offset)
                all_events.extend(events)
            
            # Filter events to only include the next N business days
            business_day_events = []
            business_days_found = 0
            
            # Start from the beginning of the target week
            if weeks_ahead == 0:
                check_date = current_date.date()
            else:
                # Calculate the start date for the target week
                days_to_add = weeks_ahead * 7
                # Find the Monday of the target week
                target_date = current_date + datetime.timedelta(days=days_to_add)
                # Get to Monday of that week
                days_since_monday = target_date.weekday()
                monday_of_week = target_date - datetime.timedelta(days=days_since_monday)
                check_date = monday_of_week.date()
            
            while business_days_found < days:
                # Skip weekends (Saturday=5, Sunday=6)
                if check_date.weekday() < 5:  # Monday=0 to Friday=4
                    # Find events for this business day
                    date_str = check_date.strftime("%Y/%m/%d")
                    day_events = [
                        event for event in all_events 
                        if event.get("start", "").startswith(date_str)
                    ]
                    business_day_events.extend(day_events)
                    business_days_found += 1
                
                # Move to next day
                check_date += datetime.timedelta(days=1)
            
            week_desc = "current week" if weeks_ahead == 0 else f"{weeks_ahead} week{'s' if weeks_ahead > 1 else ''} ahead"
            _LOGGER.info(f"Found {len(business_day_events)} events for next {days} business days starting from {week_desc}")
            return business_day_events
            
        except Exception as err:
            _LOGGER.error("Failed to get business day events: %s", err)
            return []

    def _sync_get_calendar_events(self, child_id: str, weeks_ahead: int = 0) -> list[dict[str, Any]]:
        """Synchronous version of calendar events retrieval.
        
        Args:
            child_id: The child's user ID
            weeks_ahead: Number of weeks ahead to fetch (0 = current week, 1 = next week, etc.)
        """
        try:
            # Get authentication token for EasyIQ widget
            token = self.get_token(EASYIQ_WEEKPLAN_WIDGET_ID)
            if not token:
                _LOGGER.error("Failed to get token for EasyIQ widget")
                return []
            
            # Prepare the request exactly like Chrome DevTools
            url = "https://skoleportal.easyiqcloud.dk/Calendar/CalendarGetWeekplanEvents"
            
            # Parameters - use actual child data instead of hardcoded values
            # Get the child's actual ID for the loginId parameter
            child_data = self._children_data.get(child_id)
            if not child_data:
                _LOGGER.error(f"Child data not found for ID: {child_id}")
                _LOGGER.debug(f"Available child data keys: {list(self._children_data.keys())}")
                _LOGGER.debug(f"Children data: {self._children_data}")
                return []
            
            # Use the child's actual ID as loginId (this was the bug!)
            actual_child_id = child_data.get("id", child_id)
            _LOGGER.debug(f"Child {child_id} -> using actual_child_id: {actual_child_id} for API call")
            
            # Calculate the target date based on weeks_ahead
            target_date = datetime.datetime.now() + datetime.timedelta(weeks=weeks_ahead)
            
            params = {
                "loginId": str(actual_child_id),  # Use actual child ID
                "date": target_date.isoformat() + "Z",  # Support different weeks
                "activityFilter": "-1",  # Try with no filter first
                "courseFilter": "-1",
                "textFilter": "",
                "ownWeekPlan": "false"
            }
            
            # Headers exactly like Chrome DevTools
            headers = {
                "accept": "*/*",
                "accept-encoding": "gzip, deflate, br, zstd",
                "accept-language": "en-US,en;q=0.9,da;q=0.8",
                "authorization": token,
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
                "x-child": child_id,
                "x-childfilter": child_id,
                "x-institutionfilter": ",".join(self._institution_profiles) if self._institution_profiles else "",  # Dynamic institution filter
                "x-login": self.username,
                "x-userprofile": "guardian",
            }
            
            _LOGGER.debug("Calendar events request - URL: %s", url)
            _LOGGER.debug("Calendar events request - Params: %s", params)
            
            # Make the request using the authenticated session
            response = self._session.get(url, params=params, headers=headers, verify=True)
            
            if response.status_code == 200:
                try:
                    # Debug: Log response info
                    _LOGGER.debug(f"Response status: {response.status_code}")
                    _LOGGER.debug(f"Content encoding: {response.headers.get('content-encoding', 'none')}")
                    _LOGGER.debug(f"Content type: {response.headers.get('content-type', 'none')}")
                    
                    # Let requests handle decompression automatically (including Brotli)
                    # This is more reliable than manual decompression
                    try:
                        events = response.json()
                        _LOGGER.debug(f"Successfully parsed JSON response with {len(events)} events")
                    except Exception as json_error:
                        _LOGGER.error(f"Failed to parse JSON response: {json_error}")
                        # Try manual decompression as last resort
                        content_encoding = response.headers.get('content-encoding', '').lower()
                        if 'br' in content_encoding:
                            _LOGGER.debug("Attempting manual Brotli decompression as fallback")
                            try:
                                import brotli
                                decompressed_content = brotli.decompress(response.content)
                                json_text = decompressed_content.decode('utf-8')
                                import json
                                events = json.loads(json_text)
                                _LOGGER.debug("Manual Brotli decompression successful")
                            except Exception as decomp_error:
                                _LOGGER.debug(f"Manual Brotli decompression also failed: {decomp_error}")
                                events = []
                        else:
                            events = []
                    
                    _LOGGER.info("🎉 Successfully retrieved %d calendar events!", len(events))
                    
                    # Log some sample data for debugging
                    if events and len(events) > 0:
                        sample_event = events[0]
                        _LOGGER.debug(f"Sample event keys: {list(sample_event.keys())}")
                        _LOGGER.debug(f"Sample event: {sample_event}")
                    
                    return events
                except Exception as e:
                    _LOGGER.error("Failed to parse calendar events JSON: %s", e)
                    # Try to get more info about the response
                    try:
                        content_type = response.headers.get('content-type', '')
                        encoding = response.headers.get('content-encoding', '')
                        _LOGGER.debug(f"Content-Type: {content_type}, Encoding: {encoding}")
                        _LOGGER.debug(f"Raw content length: {len(response.content)}")
                        _LOGGER.debug(f"Text length: {len(response.text)}")
                        _LOGGER.debug(f"Response text preview: {repr(response.text[:100])}")
                    except Exception as debug_error:
                        _LOGGER.debug(f"Debug info error: {debug_error}")
                    return []
            else:
                _LOGGER.error("Calendar events API returned status %s", response.status_code)
                _LOGGER.debug(f"Error response: {response.text[:200]}...")
                return []
                
        except Exception as err:
            _LOGGER.error("Failed to get calendar events: %s", err)
            return []

    async def get_children(self) -> list[dict[str, Any]]:
        """Get children data."""
        if not self._authenticated:
            _LOGGER.warning("Not authenticated - cannot fetch children")
            return []
        
        return self.children

    async def get_weekplan(self, child_id: str) -> dict[str, Any]:
        """Get weekplan data using the working CalendarGetWeekplanEvents endpoint."""
        if not self._authenticated:
            _LOGGER.warning("Not authenticated - cannot fetch weekplan")
            return {}
        
        try:
            # Get calendar events (contains both weekplan and homework)
            events = await self._get_calendar_events(child_id)
            if not events:
                return {}
            
            # Filter for weekplan events (itemType 9 = schedule events)
            weekplan_events = [event for event in events if event.get("itemType") == 9]
            
            # Process weekplan events
            current_date = datetime.datetime.now()
            week_num = current_date.isocalendar()[1]
            
            weekplan_html = f"<h2>Week {week_num}</h2>"
            
            for event in weekplan_events:
                try:
                    start_time = event.get("start", "")
                    end_time = event.get("end", "")
                    description = event.get("description", "")
                    courses = event.get("courses", "")
                    activities = event.get("activities", "")
                    
                    weekplan_html += f"<br><b>{start_time} - {end_time}</b><br>"
                    weekplan_html += f"<b>{courses}</b> ({activities})<br>"
                    if description:
                        weekplan_html += f"{description}<br>"
                    weekplan_html += "<br>"
                    
                except Exception as e:
                    _LOGGER.debug("Error processing weekplan event: %s", e)
                    continue
            
            return {
                "week": f"Week {week_num}",
                "html_content": weekplan_html,
                "events": weekplan_events,
                "raw_data": events
            }
            
        except Exception as err:
            _LOGGER.error("Failed to get weekplan for child %s: %s", child_id, err)
            return {}

    async def get_homework(self, child_id: str) -> dict[str, Any]:
        """Get homework data using the working CalendarGetWeekplanEvents endpoint."""
        if not self._authenticated:
            _LOGGER.warning("Not authenticated - cannot fetch homework")
            return {}
        
        try:
            # Get calendar events (contains both weekplan and homework)
            events = await self._get_calendar_events(child_id)
            if not events:
                return {}
            
            # Filter for homework events (itemType 4 = homework/assignments)
            homework_events = [event for event in events if event.get("itemType") == 4]
            
            # Process homework events
            current_date = datetime.datetime.now()
            week_num = current_date.isocalendar()[1]
            
            assignments = []
            homework_html = f"<h2>Week {week_num} - Homework</h2>"
            
            for event in homework_events:
                try:
                    assignment_data = {
                        "title": event.get("courses", ""),
                        "subject": event.get("courses", ""),
                        "description": event.get("description", ""),
                        "start_time": event.get("start", ""),
                        "activities": event.get("activities", ""),
                        "raw_data": event
                    }
                    assignments.append(assignment_data)
                    
                    # Build HTML representation
                    homework_html += f"<h3>{assignment_data['subject']}</h3>"
                    homework_html += f"<p><strong>Activities:</strong> {assignment_data['activities']}</p>"
                    homework_html += f"<p><strong>Time:</strong> {assignment_data['start_time']}</p>"
                    if assignment_data['description']:
                        homework_html += f"<p><strong>Description:</strong> {assignment_data['description']}</p>"
                    homework_html += "<hr>"
                    
                except Exception as e:
                    _LOGGER.debug("Error processing homework event: %s", e)
                    continue
            
            return {
                "week": f"Week {week_num}",
                "html_content": homework_html,
                "assignments": assignments,
                "raw_data": events
            }
            
        except Exception as err:
            _LOGGER.error("Failed to get homework for child %s: %s", child_id, err)
            return {}

    async def get_messages(self) -> dict[str, Any]:
        """Get messages data from Aula API."""
        if not self._authenticated:
            _LOGGER.warning("Not authenticated - cannot fetch messages")
            return {}
        
        try:
            # Run the synchronous message request in an executor to avoid blocking
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._sync_get_messages)
        except Exception as err:
            _LOGGER.error("Failed to get messages: %s", err)
            return {}
    
    def _sync_get_messages(self) -> dict[str, Any]:
        """Synchronous version of messages retrieval."""
        try:
            # Get message threads from Aula API
            _LOGGER.debug("Fetching message threads...")
            mesres = self._session.get(
                self.apiurl + "?method=messaging.getThreads&sortOn=date&orderDirection=desc&page=0",
                verify=True,
            )
            
            if mesres.status_code != 200:
                _LOGGER.error(f"Failed to get message threads: {mesres.status_code}")
                return {}
            
            # Reset message data
            self.unread_messages = 0
            unread = 0
            self.message = {}
            
            # Check for unread messages
            threads_data = mesres.json()
            if "data" not in threads_data or "threads" not in threads_data["data"]:
                _LOGGER.debug("No message threads found")
                return self.message
            
            # Find first unread message
            threadid = None
            for mes in threads_data["data"]["threads"]:
                if not mes.get("read", True):  # Default to read if not specified
                    unread = 1
                    threadid = mes["id"]
                    _LOGGER.debug(f"Found unread message thread: {threadid}")
                    break
            
            # If we have an unread message, get its content
            if unread == 1 and threadid:
                _LOGGER.debug(f"Fetching message content for thread: {threadid}")
                threadres = self._session.get(
                    self.apiurl + f"?method=messaging.getMessagesForThread&threadId={threadid}&page=0",
                    verify=True,
                )
                
                if threadres.status_code == 200:
                    thread_data = threadres.json()
                    
                    # Handle sensitive messages (403 status)
                    if thread_data.get("status", {}).get("code") == 403:
                        self.message = {
                            "text": "Log ind på Aula med MitID for at læse denne besked.",
                            "sender": "Ukendt afsender",
                            "subject": "Følsom besked"
                        }
                        self.unread_messages = 1
                    else:
                        # Parse regular messages
                        if "data" in thread_data and "messages" in thread_data["data"]:
                            for message in thread_data["data"]["messages"]:
                                if message.get("messageType") == "Message":
                                    # Extract message text
                                    try:
                                        if isinstance(message.get("text"), dict):
                                            self.message["text"] = message["text"].get("html", message["text"].get("text", ""))
                                        else:
                                            self.message["text"] = message.get("text", "")
                                    except Exception:
                                        self.message["text"] = "intet indhold..."
                                        _LOGGER.warning("Could not extract message text")
                                    
                                    # Extract sender
                                    try:
                                        sender_info = message.get("sender", {})
                                        self.message["sender"] = sender_info.get("fullName", "Ukendt afsender")
                                    except Exception:
                                        self.message["sender"] = "Ukendt afsender"
                                    
                                    # Extract subject
                                    try:
                                        self.message["subject"] = thread_data["data"].get("subject", "")
                                    except Exception:
                                        self.message["subject"] = ""
                                    
                                    self.unread_messages = 1
                                    _LOGGER.info(f"Found unread message: {self.message.get('subject', 'No subject')}")
                                    break
                else:
                    _LOGGER.error(f"Failed to get message thread content: {threadres.status_code}")
            
            _LOGGER.debug(f"Messages check complete: {self.unread_messages} unread messages")
            return self.message
            
        except Exception as err:
            _LOGGER.error(f"Error getting messages: {err}")
            return {}

    async def get_presence(self, child_id: str) -> dict[str, Any]:
        """Get presence data based on current schedule events."""
        if not self._authenticated:
            _LOGGER.warning("Not authenticated - cannot fetch presence")
            return {}
        
        try:
            # Get calendar events to determine current presence
            events = await self._get_calendar_events(child_id)
            if not events:
                return {
                    "status": "No Schedule Data",
                    "status_code": 0,
                    "last_updated": datetime.datetime.now().isoformat()
                }
            
            # Filter for today's schedule events (itemType 9)
            now = datetime.datetime.now()
            today_str = now.strftime("%Y/%m/%d")
            
            current_events = []
            for event in events:
                if event.get("itemType") == 9:  # Schedule events
                    event_start = event.get("start", "")
                    if event_start.startswith(today_str):
                        # Parse start and end times
                        try:
                            start_time_str = event_start  # Format: "2025/09/15 08:05"
                            end_time_str = event.get("end", "")
                            
                            start_time = datetime.datetime.strptime(start_time_str, "%Y/%m/%d %H:%M")
                            end_time = datetime.datetime.strptime(end_time_str, "%Y/%m/%d %H:%M")
                            
                            # Check if current time is within this event
                            if start_time <= now <= end_time:
                                current_events.append({
                                    "course": event.get("courses", ""),
                                    "activity": event.get("activities", ""),
                                    "start": start_time_str,
                                    "end": end_time_str,
                                    "description": event.get("description", "")
                                })
                        except ValueError:
                            continue
            
            # Determine presence status based on current events
            if current_events:
                # Child is currently in a scheduled class
                current_event = current_events[0]  # Take the first if multiple
                status = f"In Class - {current_event['course']}"
                status_code = 3  # KOMMET/TIL STEDE (Present)
                
                return {
                    "status": status,
                    "status_code": status_code,
                    "current_event": current_event,
                    "last_updated": now.isoformat()
                }
            else:
                # Check if there are any events today to determine if it's a school day
                today_events = [e for e in events if e.get("itemType") == 9 and e.get("start", "").startswith(today_str)]
                
                if today_events:
                    # It's a school day but no current class
                    # Check if school day has started or ended
                    earliest_start = None
                    latest_end = None
                    
                    for event in today_events:
                        try:
                            start_time = datetime.datetime.strptime(event.get("start", ""), "%Y/%m/%d %H:%M")
                            end_time = datetime.datetime.strptime(event.get("end", ""), "%Y/%m/%d %H:%M")
                            
                            if earliest_start is None or start_time < earliest_start:
                                earliest_start = start_time
                            if latest_end is None or end_time > latest_end:
                                latest_end = end_time
                        except ValueError:
                            continue
                    
                    if earliest_start and latest_end:
                        if now < earliest_start:
                            status = "Before School"
                            status_code = 0  # IKKE KOMMET (Not arrived)
                        elif now > latest_end:
                            status = "After School"
                            status_code = 8  # HENTET/GÅET (Picked up/Gone)
                        else:
                            status = "Between Classes"
                            status_code = 3  # KOMMET/TIL STEDE (Present)
                    else:
                        status = "School Day - No Schedule"
                        status_code = 0
                else:
                    # No school today
                    status = "No School Today"
                    status_code = 2  # FERIE/FRI (Holiday/Free)
                
                return {
                    "status": status,
                    "status_code": status_code,
                    "last_updated": now.isoformat()
                }
                
        except Exception as err:
            _LOGGER.error("Failed to get presence for child %s: %s", child_id, err)
            return {
                "status": "Error",
                "status_code": 0,
                "last_updated": datetime.datetime.now().isoformat()
            }

    async def update_data(self) -> None:
        """Update all data from the API using business days approach."""
        try:
            # First authenticate if not already authenticated
            if not await self.authenticate():
                _LOGGER.error("Failed to authenticate - cannot update data")
                return
            
            # Update children data
            self.children = await self.get_children()
            
            # Update weekplan, homework, and presence data for each child using business days approach
            self.weekplan_data = {}
            self.homework_data = {}
            self.presence_data = {}
            
            for child in self.children:
                child_id = child.get("id", "")
                child_name = child.get("name", "Unknown")
                if child_id:
                    _LOGGER.info(f"Updating data for child: {child_name} (ID: {child_id})")
                    
                    # Debug: Show child data mapping
                    child_data = self._children_data.get(child_id)
                    if child_data:
                        actual_id = child_data.get("id")
                        _LOGGER.info(f"  Child {child_name}: userId={child_id} -> actual_id={actual_id}")
                    else:
                        _LOGGER.error(f"  No child data found for {child_name} (ID: {child_id})")
                        _LOGGER.error(f"  Available child data keys: {list(self._children_data.keys())}")
                    
                    # Get events for next 5 business days instead of just current week
                    try:
                        business_day_events = await self.get_calendar_events_for_business_days(child_id, 5)
                        
                        # Separate weekplan and homework events
                        weekplan_events = [event for event in business_day_events if event.get("itemType") == 9]
                        homework_events = [event for event in business_day_events if event.get("itemType") == 4]
                        
                        # Store weekplan data
                        self.weekplan_data[child_id] = {
                            "week": f"Next 5 Business Days",
                            "events": weekplan_events,
                            "html_content": self._build_weekplan_html(weekplan_events),
                            "raw_data": business_day_events
                        }
                        
                        # Store homework data
                        homework_assignments = []
                        for event in homework_events:
                            assignment_data = {
                                "title": event.get("courses", ""),
                                "subject": event.get("courses", ""),
                                "description": event.get("description", ""),
                                "start_time": event.get("start", ""),
                                "activities": event.get("activities", ""),
                                "raw_data": event
                            }
                            homework_assignments.append(assignment_data)
                        
                        self.homework_data[child_id] = {
                            "week": f"Next 5 Business Days",
                            "assignments": homework_assignments,
                            "html_content": self._build_homework_html(homework_assignments),
                            "raw_data": business_day_events
                        }
                        
                        # Get presence data for this child
                        self.presence_data[child_id] = await self.get_presence(child_id)
                        
                        _LOGGER.info(f"Updated data for {child_name}: {len(weekplan_events)} weekplan events, {len(homework_events)} homework events")
                        
                    except Exception as child_err:
                        _LOGGER.error(f"Failed to update data for child {child_name}: {child_err}", exc_info=True)
                        # Set empty data for this child to avoid errors but keep integration running
                        self.weekplan_data[child_id] = {
                            "week": "Error - Check Logs",
                            "events": [],
                            "html_content": f"<p>Error updating data for {child_name}. Check Home Assistant logs.</p>",
                            "raw_data": []
                        }
                        self.homework_data[child_id] = {
                            "week": "Error - Check Logs",
                            "assignments": [],
                            "html_content": f"<p>Error updating homework for {child_name}. Check Home Assistant logs.</p>",
                            "raw_data": []
                        }
                        self.presence_data[child_id] = {
                            "status": "Error - Check Logs",
                            "status_code": 0,
                            "last_updated": datetime.datetime.now().isoformat()
                        }
            
            # Update messages (placeholder)
            self.unread_messages = 0
            self.message = await self.get_messages()
            
            _LOGGER.info("Successfully updated all data")
            _LOGGER.debug(f"Final data summary:")
            _LOGGER.debug(f"  Children: {len(self.children)}")
            _LOGGER.debug(f"  Weekplan data keys: {list(self.weekplan_data.keys())}")
            _LOGGER.debug(f"  Homework data keys: {list(self.homework_data.keys())}")
            _LOGGER.debug(f"  Presence data keys: {list(self.presence_data.keys())}")
            
        except Exception as err:
            _LOGGER.error("Failed to update data: %s", err)
            raise

    def _build_weekplan_html(self, weekplan_events: list[dict[str, Any]]) -> str:
        """Build HTML content for weekplan events."""
        html = "<h2>Next 5 Business Days - Schedule</h2>"
        
        if not weekplan_events:
            html += "<p>No scheduled events found.</p>"
            return html
        
        # Group events by date
        events_by_date = {}
        for event in weekplan_events:
            start_time = event.get("start", "")
            if start_time:
                date_part = start_time.split(" ")[0]  # Get "2025/09/15" part
                if date_part not in events_by_date:
                    events_by_date[date_part] = []
                events_by_date[date_part].append(event)
        
        # Sort dates and build HTML
        for date_str in sorted(events_by_date.keys()):
            try:
                # Convert to readable date format
                date_obj = datetime.datetime.strptime(date_str, "%Y/%m/%d")
                readable_date = date_obj.strftime("%A, %B %d, %Y")
                html += f"<h3>{readable_date}</h3>"
                
                # Sort events by time for this date
                day_events = sorted(events_by_date[date_str], key=lambda x: x.get("start", ""))
                
                for event in day_events:
                    start_time = event.get("start", "")
                    end_time = event.get("end", "")
                    courses = event.get("courses", "")
                    activities = event.get("activities", "")
                    description = event.get("description", "")
                    
                    # Extract time part
                    start_time_part = start_time.split(" ")[1] if " " in start_time else start_time
                    end_time_part = end_time.split(" ")[1] if " " in end_time else end_time
                    
                    html += f"<p><b>{start_time_part} - {end_time_part}</b><br>"
                    html += f"<b>{courses}</b>"
                    if activities:
                        html += f" ({activities})"
                    html += "<br>"
                    if description:
                        html += f"{description}<br>"
                    html += "</p>"
                        
            except ValueError:
                continue
        
        return html
    
    def _build_homework_html(self, homework_assignments: list[dict[str, Any]]) -> str:
        """Build HTML content for homework assignments."""
        html = "<h2>Next 5 Business Days - Homework</h2>"
        
        if not homework_assignments:
            html += "<p>No homework assignments found.</p>"
            return html
        
        for assignment in homework_assignments:
            subject = assignment.get("subject", "Unknown Subject")
            activities = assignment.get("activities", "")
            start_time = assignment.get("start_time", "")
            description = assignment.get("description", "")
            
            html += f"<h3>{subject}</h3>"
            if activities:
                html += f"<p><strong>Activities:</strong> {activities}</p>"
            if start_time:
                html += f"<p><strong>Time:</strong> {start_time}</p>"
            if description:
                html += f"<p><strong>Description:</strong> {description}</p>"
            html += "<hr>"
        
        return html

    async def authenticate(self) -> bool:
        """Authenticate with the EasyIQ API using async approach."""
        try:
            # Run the synchronous login in an executor to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self.login)
            return result
        except Exception as err:
            _LOGGER.error("Unexpected error during authentication: %s", err)
            return False