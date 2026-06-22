"""EasyIQ API client with working CalendarGetWeekplanEvents implementation."""
from __future__ import annotations

import asyncio
import html as html_lib
import logging
from typing import Any, Callable
from urllib.parse import urljoin
import datetime
import json
import re

# Import dependencies with better error handling
aiohttp = None
pytz = None
requests = None

# Try to import each dependency individually
try:
    import aiohttp
except ImportError:
    aiohttp = None

try:
    import pytz
except ImportError:
    pytz = None

# For requests, try different approaches
try:
    import requests
except ImportError:
    try:
        # Try importing without any potential conflicts
        import sys
        import importlib
        requests = importlib.import_module('requests')
    except ImportError:
        requests = None

try:
    from .mitid_auth import (
        AulaTokenRefresher,
        AulaTokenState,
        MitIDAuthError,
        MitIDAuthRejected,
        TokenRefresher,
    )
except ImportError:
    # For standalone script execution from custom_components/aula_easyiq.
    from mitid_auth import (  # type: ignore[no-redef]
        AulaTokenRefresher,
        AulaTokenState,
        MitIDAuthError,
        MitIDAuthRejected,
        TokenRefresher,
    )

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


_START_DATETIME_KEYS = (
    "start",
    "startDateTime",
    "startDatetime",
    "start_time",
    "startTime",
    "startTimeUtc",
    "from",
    "fromDateTime",
    "fromDatetime",
    "begin",
    "beginDateTime",
    "beginDatetime",
    "dateStart",
)
_START_DATE_KEYS = (
    "startDate",
    "start_date",
    "date",
    "eventDate",
    "day",
    "dato",
)
_START_TIME_KEYS = (
    "startTime",
    "start_time",
    "fromTime",
    "beginTime",
    "time",
    "tid",
)
_END_DATETIME_KEYS = (
    "end",
    "endDateTime",
    "endDatetime",
    "end_time",
    "endTime",
    "endTimeUtc",
    "to",
    "toDateTime",
    "toDatetime",
    "finish",
    "finishDateTime",
    "dateEnd",
)
_END_DATE_KEYS = (
    "endDate",
    "end_date",
    "date",
    "eventDate",
    "day",
    "dato",
)
_END_TIME_KEYS = (
    "endTime",
    "end_time",
    "toTime",
    "finishTime",
    "slutTid",
)
_COURSE_KEYS = (
    "coursesDisplay",
    "courseDisplay",
    "subjectsDisplay",
    "subjectDisplay",
    "courses",
    "course",
    "courseName",
    "courseTitle",
    "courseText",
    "subject",
    "subjectName",
    "subjectTitle",
    "subjectText",
    "schoolSubject",
    "schoolSubjectName",
    "title",
    "eventTitle",
    "calendarTitle",
    "calendarText",
    "chapterTitle",
    "icon",
    "iconTitle",
    "iconName",
    "entryTitle",
    "displayName",
    "heading",
    "headline",
    "name",
    "text",
    "fag",
    "fagNavn",
    "titel",
    "tekst",
)
_ACTIVITY_KEYS = (
    "activitiesDisplay",
    "activityDisplay",
    "activities",
    "activity",
    "activityName",
    "activityTitle",
    "activityText",
    "lesson",
    "lessonName",
    "lessonTitle",
    "class",
    "className",
    "team",
    "teamName",
    "hold",
    "holdNavn",
    "activityNames",
    "activityTitles",
)
_DESCRIPTION_KEYS = (
    "description",
    "details",
    "note",
    "notes",
    "content",
    "body",
    "comment",
)
_WEEKPLAN_EVENT_TYPES = (8, 9)
_HOMEWORK_EVENT_TYPES = (4,)


def _clean_text(value: Any) -> str:
    """Strip HTML and placeholder values from EasyIQ text fields."""
    text = html_lib.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if text.lower() in {"none", "null", "undefined", "nan"}:
        return ""
    return text


def _is_plain_image_path(text: str) -> bool:
    """Return true for bare EasyIQ icon/image paths that are not titles."""
    lowered = text.lower()
    if not (
        lowered.startswith("/images/")
        or lowered.startswith("images/")
        or lowered.startswith("http://")
        or lowered.startswith("https://")
    ):
        return False
    return bool(re.search(r"\.(?:png|svg|jpe?g|gif|webp)(?:$|\?)", lowered))


def _event_value(event: dict[str, Any], keys: tuple[str, ...]) -> Any:
    """Return the first non-empty value for any key, case-insensitively."""
    lower_key_map = {str(key).lower(): key for key in event}
    for key in keys:
        actual_key = key if key in event else lower_key_map.get(key.lower())
        if actual_key is None:
            continue
        value = event.get(actual_key)
        if isinstance(value, str):
            if _clean_text(value):
                return value
            continue
        if value not in (None, ""):
            return value
    return None


def _field_text(value: Any) -> str:
    """Return readable text from common EasyIQ scalar/list/dict fields."""
    if value in (None, ""):
        return ""
    if isinstance(value, dict):
        lower_key_map = {str(key).lower(): key for key in value}
        for key in (
            "name",
            "displayName",
            "fullName",
            "shortName",
            "title",
            "text",
            "label",
            "value",
            "description",
            "subject",
            "course",
            "heading",
            "headline",
            "caption",
        ):
            actual_key = key if key in value else lower_key_map.get(key.lower())
            text = _field_text(value.get(actual_key)) if actual_key is not None else ""
            if text:
                return text
        return ""
    if isinstance(value, list):
        parts = [_field_text(item) for item in value]
        return ", ".join(part for part in parts if part)
    text = _clean_text(value)
    if _is_plain_image_path(text):
        return ""
    return text


def _event_title_text(event: dict[str, Any]) -> str:
    """Return the best visible title for a calendar event."""
    for keys in (_COURSE_KEYS, _ACTIVITY_KEYS):
        text = _field_text(_event_value(event, keys)).strip()
        if text:
            return text
    return "School Event"


def _is_generic_calendar_title(value: Any) -> bool:
    """Return true when a title is blank, generic, or agenda/body text."""
    text = _clean_text(value).lower()
    if not text:
        return True
    if text == "school event":
        return True
    if text.startswith("dagsorden"):
        return True
    return False


def _parse_easyiq_datetime(value: Any) -> datetime.datetime | None:
    """Parse EasyIQ calendar date strings in known legacy and ISO formats."""
    if not value:
        return None

    text = str(value).strip()
    if not text:
        return None

    normalized = text.replace("Z", "+00:00")
    try:
        return datetime.datetime.fromisoformat(normalized)
    except ValueError:
        pass

    for date_format in (
        "%Y/%m/%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d",
        "%Y-%m-%d",
    ):
        try:
            return datetime.datetime.strptime(text, date_format)
        except ValueError:
            continue

    return None


def _event_date(value: Any) -> datetime.date | None:
    """Return the calendar date for an EasyIQ event timestamp."""
    parsed = _parse_easyiq_datetime(value)
    if parsed is not None:
        return parsed.date()
    return None


def _event_start_date(event: dict[str, Any]) -> datetime.date | None:
    """Return the calendar date for an event from known EasyIQ fields."""
    parsed = _event_start_datetime(event)
    if parsed is not None:
        return parsed.date()
    return _event_date(event.get("start"))


def _event_time_text(value: Any) -> str:
    """Return a readable time for an EasyIQ event timestamp."""
    parsed = _parse_easyiq_datetime(value)
    if parsed is not None:
        return parsed.strftime("%H:%M")
    text = str(value or "")
    if " " in text:
        return text.split(" ", 1)[1]
    if "T" in text:
        return text.split("T", 1)[1].replace("Z", "")[:5]
    return text


def _event_datetime(
    event: dict[str, Any],
    datetime_keys: tuple[str, ...],
    date_keys: tuple[str, ...],
    time_keys: tuple[str, ...],
) -> datetime.datetime | None:
    """Parse an event timestamp from combined or split EasyIQ fields."""
    for key in datetime_keys:
        value = _event_value(event, (key,))
        parsed = _parse_easyiq_datetime(value)
        if parsed is not None:
            return parsed

    date_value = _event_value(event, date_keys)
    time_value = _event_value(event, time_keys)
    if date_value and time_value:
        for separator in (" ", "T"):
            parsed = _parse_easyiq_datetime(f"{date_value}{separator}{time_value}")
            if parsed is not None:
                return parsed

    return _parse_easyiq_datetime(date_value)


def _event_start_datetime(event: dict[str, Any]) -> datetime.datetime | None:
    """Return the event start timestamp from known EasyIQ fields."""
    return _event_datetime(
        event,
        _START_DATETIME_KEYS,
        _START_DATE_KEYS,
        _START_TIME_KEYS,
    )


def _event_end_datetime(event: dict[str, Any]) -> datetime.datetime | None:
    """Return the event end timestamp from known EasyIQ fields."""
    return _event_datetime(
        event,
        _END_DATETIME_KEYS,
        _END_DATE_KEYS,
        _END_TIME_KEYS,
    )


def _event_item_type(event: dict[str, Any]) -> int | None:
    """Return the EasyIQ item type as an integer when present."""
    for key in (
        "itemType",
        "itemTypeId",
        "type",
        "typeId",
        "eventType",
        "eventTypeId",
        "calendarItemType",
        "calendarItemTypeId",
        "activityType",
        "activityTypeId",
    ):
        value = _event_value(event, (key,))
        if isinstance(value, dict):
            value = value.get("id", value.get("value"))

        if isinstance(value, bool) or value is None:
            continue
        if isinstance(value, int):
            return value
        if isinstance(value, float) and value.is_integer():
            return int(value)
        if isinstance(value, str):
            try:
                return int(value.strip())
            except ValueError:
                continue

    return None


def _events_of_type(events: list[dict[str, Any]], item_type: int) -> list[dict[str, Any]]:
    """Return EasyIQ events matching a normalized item type."""
    return [event for event in events if _event_item_type(event) == item_type]


def _events_of_types(
    events: list[dict[str, Any]],
    item_types: tuple[int, ...],
) -> list[dict[str, Any]]:
    """Return EasyIQ events matching any normalized item type."""
    return [event for event in events if _event_item_type(event) in item_types]


def _event_type_counts(events: list[dict[str, Any]]) -> dict[str, int]:
    """Return a compact item type histogram for diagnostics."""
    counts: dict[str, int] = {}
    for event in events:
        item_type = _event_item_type(event)
        key = "missing" if item_type is None else str(item_type)
        counts[key] = counts.get(key, 0) + 1
    return counts


def _preview_value(value: Any) -> Any:
    """Return a small JSON-friendly preview value for diagnostics."""
    if isinstance(value, dict):
        preview: dict[str, Any] = {}
        for key, nested_value in list(value.items())[:8]:
            preview[str(key)] = _preview_value(nested_value)
        return preview
    if isinstance(value, list):
        return [_preview_value(item) for item in value[:3]]
    text = str(value)
    return text[:160] if len(text) > 160 else text


def _event_preview(event: dict[str, Any]) -> dict[str, Any]:
    """Return a compact event preview for diagnostics."""
    return {
        str(key): _preview_value(value)
        for key, value in list(event.items())[:60]
    }


def _normalize_calendar_event(event: dict[str, Any]) -> dict[str, Any]:
    """Populate the legacy fields this integration expects from newer shapes."""
    normalized = dict(event)
    start = _event_start_datetime(event)
    end = _event_end_datetime(event)

    if start is not None and not normalized.get("start"):
        normalized["start"] = start.isoformat()
    if end is not None and not normalized.get("end"):
        normalized["end"] = end.isoformat()
    elif start is not None and not normalized.get("end"):
        normalized["end"] = (start + datetime.timedelta(hours=1)).isoformat()

    courses = _event_title_text(event)
    if courses and _is_generic_calendar_title(normalized.get("courses")):
        normalized["courses"] = courses

    activities = _field_text(_event_value(event, _ACTIVITY_KEYS))
    if activities and not _clean_text(normalized.get("activities")):
        normalized["activities"] = activities

    description = _field_text(_event_value(event, _DESCRIPTION_KEYS))
    if description and not _clean_text(normalized.get("description")):
        normalized["description"] = description

    if _event_item_type(normalized) is None and start is not None:
        normalized["itemType"] = 9
        normalized["_easyiq_item_type_inferred"] = "weekplan"

    return normalized


def _payload_summary(payload: Any) -> dict[str, Any]:
    """Return a small, serializable description of an API payload."""
    if isinstance(payload, list):
        return {"type": "list", "length": len(payload)}
    if isinstance(payload, dict):
        return {
            "type": "dict",
            "keys": [str(key) for key in list(payload.keys())[:12]],
        }
    return {"type": type(payload).__name__}


def _extract_calendar_event_list(
    payload: Any,
    *,
    normalize: bool = True,
) -> list[dict[str, Any]]:
    """Normalize known EasyIQ calendar response wrappers to a list of events."""
    events: list[dict[str, Any]] = []
    if isinstance(payload, list):
        events = [event for event in payload if isinstance(event, dict)]
    elif isinstance(payload, dict):
        for key in (
            "events",
            "calendarEvents",
            "items",
            "data",
            "value",
            "result",
            "results",
        ):
            value = payload.get(key)
            if isinstance(value, list):
                events = [event for event in value if isinstance(event, dict)]
                break
            if isinstance(value, dict):
                nested_events = _extract_calendar_event_list(
                    value,
                    normalize=normalize,
                )
                if nested_events:
                    return nested_events

    if normalize:
        return [_normalize_calendar_event(event) for event in events]
    return events


class EasyIQAuthError(MitIDAuthError):
    """Raised when EasyIQ cannot authenticate with Aula token state."""


class EasyIQClient:
    """Client for communicating with EasyIQ API using the working CalendarGetWeekplanEvents approach."""

    def __init__(
        self,
        mitid_username: str,
        token_state: AulaTokenState | dict[str, Any] | None,
        *,
        token_refresher: TokenRefresher | None = None,
        on_token_update: Callable[[AulaTokenState], None] | None = None,
        fixture_base_url: str | None = None,
        session_factory: Callable[[], Any] | None = None,
    ) -> None:
        """Initialize the client."""
        self.username = mitid_username
        self.fixture_base_url = fixture_base_url.rstrip("/") if fixture_base_url else None
        self.token_state = (
            None
            if token_state is None
            else token_state
            if isinstance(token_state, AulaTokenState)
            else AulaTokenState.from_entry_data(token_state)
        )
        self._token_refresher = token_refresher or AulaTokenRefresher()
        self._on_token_update = on_token_update
        self.session: aiohttp.ClientSession | None = None
        self._session: requests.Session | None = (
            session_factory()
            if session_factory is not None
            else requests.Session()
            if requests is not None
            else None
        )
        self._authenticated = False
        
        # Authentication data
        self._profiles = []
        self._profile_context = []
        self._institution_profiles = []
        self._children_data = {}
        self._guardian_user_id = ""
        self._guardian_profile_id = ""
        self.api_url = ""
        self.apiurl = ""  # For compatibility with Aula client
        self.widgets = {}
        self.tokens = {}
        self._calendar_login_id_cache = {}
        self._calendar_request_variant_cache = {}
        self._calendar_zero_warning_emitted: set[str] = set()
        
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
        self.update_diagnostics: dict[str, Any] = {}
        self.calendar_diagnostics: dict[str, Any] = {}

    def _now_text(self) -> str:
        """Return a serializable timestamp for diagnostics."""
        return datetime.datetime.now().isoformat()

    def _record_calendar_week_diagnostic(
        self,
        child_id: str,
        weeks_ahead: int,
        **values: Any,
    ) -> None:
        """Store diagnostic details for a single calendar week request."""
        child_diag = self.calendar_diagnostics.setdefault(str(child_id), {})
        week_offsets = child_diag.setdefault("week_offsets", {})
        week_diag = week_offsets.setdefault(str(weeks_ahead), {})
        week_diag.update(values)
        week_diag["last_updated"] = self._now_text()

    def _record_calendar_summary(self, child_id: str, **values: Any) -> None:
        """Store visible calendar diagnostics for a child."""
        child_diag = self.calendar_diagnostics.setdefault(str(child_id), {})
        child_diag.update(values)
        child_diag["last_updated"] = self._now_text()

    def _warn_zero_calendar_once(
        self,
        child_id: str,
        *,
        raw_event_count: int,
        business_day_event_count: int,
        event_type_counts: dict[str, int],
    ) -> None:
        """Emit one warning for silent empty calendar data."""
        key = str(child_id)
        if key in self._calendar_zero_warning_emitted:
            return
        self._calendar_zero_warning_emitted.add(key)
        _LOGGER.warning(
            "EasyIQ calendar returned no business-day events for child %s "
            "(raw=%d, business_days=%d, item_types=%s). Diagnostics are "
            "available on the EasyIQ Status and Weekplan sensor attributes.",
            child_id,
            raw_event_count,
            business_day_event_count,
            event_type_counts,
        )

    def _ensure_sync_session(self) -> Any:
        """Return an initialized synchronous requests-like session."""
        if self._session is None:
            if requests is None:
                raise EasyIQAuthError("requests is not available")
            self._session = requests.Session()
        return self._session

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

    @property
    def fixture_mode(self) -> bool:
        """Return true when the client should load fixture data instead of live APIs."""
        return bool(self.fixture_base_url)

    def _fixture_url(self, path: str) -> str:
        """Build a fixture endpoint URL."""
        if not self.fixture_base_url:
            raise RuntimeError("fixture_base_url is not configured")
        return urljoin(f"{self.fixture_base_url}/", path.lstrip("/"))

    async def _fixture_json(self, path: str, default: Any) -> Any:
        """Load JSON from the configured fixture server."""
        session = await self._ensure_session()
        url = self._fixture_url(path)
        async with session.get(url) as response:
            if response.status == 404:
                _LOGGER.debug("Fixture endpoint %s returned 404; using default", url)
                return default
            response.raise_for_status()
            return await response.json()

    async def _authenticate_fixture(self) -> bool:
        """Load fixture profile data and mark the client authenticated."""
        profile = await self._fixture_json("aula_easyiq/profile", {})
        children = profile.get("children", []) if isinstance(profile, dict) else []
        institution_profiles = profile.get("institution_profiles", []) if isinstance(profile, dict) else []

        self._profiles = [profile] if isinstance(profile, dict) else []
        self._profile_context = profile.get("profile_context", []) if isinstance(profile, dict) else []
        self._profilecontext = self._profile_context
        self._institution_profiles = [str(item) for item in institution_profiles]
        self._children_data = {}
        self._childnames = {}
        self._childuserids = []
        self._childids = []
        self.children = []

        for child in children:
            user_id = str(child.get("id") or child.get("userId") or child.get("user_id"))
            actual_id = str(child.get("actual_id") or child.get("actualId") or child.get("aula_id") or user_id)
            name = child.get("name", "Fixture Child")
            self._childuserids.append(user_id)
            self._childnames[user_id] = name
            self._childids.append(actual_id)
            self._children_data[user_id] = {
                "id": actual_id,
                "userId": user_id,
                "name": name,
            }
            self.children.append({"id": user_id, "name": name})

        self._authenticated = True
        _LOGGER.info("Loaded EasyIQ fixture profile with %d children", len(self.children))
        return True

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()

    def _ensure_valid_token(self) -> None:
        """Refresh token state when the Aula access token is expired."""
        if self.fixture_mode:
            return
        if self.token_state is None:
            raise EasyIQAuthError("Aula token state is missing")
        if not self.token_state.is_expired():
            return

        try:
            _LOGGER.debug("Refreshing Aula access token")
            self.token_state = self._token_refresher.refresh(self.token_state)
            self.tokens.clear()
            if self._on_token_update is not None:
                self._on_token_update(self.token_state)
        except MitIDAuthRejected:
            raise
        except MitIDAuthError:
            raise
        except Exception as err:
            raise EasyIQAuthError(f"Aula token refresh failed: {err}") from err

    def _aula_get(
        self,
        method: str,
        *,
        params: dict[str, Any] | None = None,
        apiurl: str | None = None,
    ) -> Any:
        """Make a token-backed Aula API GET request."""
        self._ensure_valid_token()
        request_params = dict(params or {})
        request_params["method"] = method
        request_params["access_token"] = self.token_state.access_token
        return self._ensure_sync_session().get(
            apiurl or self.apiurl,
            params=request_params,
            verify=True,
        )

    def _authenticate_sync(self) -> bool:
        """Authenticate using stored MitID/Aula token state."""
        self._ensure_valid_token()

        if self._authenticated:
            return True

        try:
            self.apiurl = API + API_VERSION
            self.api_url = self.apiurl
            apiver = int(API_VERSION)
            api_success = False
            while not api_success:
                self.apiurl = API + str(apiver)
                self.api_url = self.apiurl
                _LOGGER.debug("Trying Aula API at %s", self.apiurl)
                ver = self._aula_get(
                    "profiles.getProfilesByLogin",
                    apiurl=self.apiurl,
                )
                if ver.status_code == 410:
                    _LOGGER.debug(
                        "Aula API version %s is gone; trying the next version",
                        apiver,
                    )
                    apiver += 1
                elif ver.status_code in (401, 403):
                    raise MitIDAuthRejected("Aula access token was rejected")
                elif ver.status_code == 200:
                    ver_json = ver.json()
                    self._profiles = ver_json["data"]["profiles"]
                    api_success = True
                else:
                    raise EasyIQAuthError(
                        f"Aula profile discovery failed: HTTP {ver.status_code}"
                    )

            _LOGGER.debug("Found Aula API on %s", self.apiurl)

            profile_response = self._aula_get(
                "profiles.getProfileContext",
                params={"portalrole": "guardian"},
            )
            if profile_response.status_code in (401, 403):
                raise MitIDAuthRejected("Aula profile context token was rejected")
            if profile_response.status_code != 200:
                raise EasyIQAuthError(
                    f"Aula profile context failed: HTTP {profile_response.status_code}"
                )

            profile_json = profile_response.json()
            profile_data = profile_json["data"]
            institution_profile = profile_data.get("institutionProfile", {})
            self._guardian_user_id = str(profile_data.get("userId", "") or "")
            self._guardian_profile_id = str(institution_profile.get("id", "") or "")
            self._profile_context = institution_profile["relations"]
            self._profilecontext = self._profile_context

            self._children_data = {}
            self._childnames = {}
            self._childuserids = []
            self._childids = []
            self._institution_profiles = []
            self.children = []

            for profile in self._profiles:
                for institutioncode in profile.get("institutionProfiles", []):
                    institution_code = str(institutioncode["institutionCode"])
                    if institution_code not in self._institution_profiles:
                        self._institution_profiles.append(institution_code)

                for child in profile.get("children", []):
                    user_id = child["userId"]
                    child_id = child["id"]
                    child_name = child["name"]

                    self._childuserids.append(str(user_id))
                    self._childnames[str(user_id)] = child_name
                    self._childids.append(str(child_id))
                    self._children_data[str(user_id)] = {
                        "id": child_id,
                        "userId": user_id,
                        "name": child_name,
                    }
                    self.children.append(
                        {
                            "id": str(user_id),
                            "name": child_name,
                        }
                    )

            _LOGGER.info(
                "Found %d children: %s",
                len(self.children),
                [child["name"] for child in self.children],
            )
            _LOGGER.debug("Institution codes: %s", self._institution_profiles)

            self._authenticated = True
            return True
        except MitIDAuthError:
            raise
        except Exception as err:
            raise EasyIQAuthError(f"Authentication failed: {err}") from err

    def login(self) -> bool:
        """Validate stored MitID/Aula token state and discover profile context."""
        if self.fixture_mode:
            self._authenticated = True
            return True

        try:
            return self._authenticate_sync()
        except MitIDAuthError as err:
            _LOGGER.error("Authentication failed: %s", err)
            return False

    def get_widgets(self) -> dict[str, str]:
        """Get available widgets."""
        if not self._authenticated:
            _LOGGER.warning("Not authenticated - cannot fetch widgets")
            return {}
        
        try:
            response = self._aula_get("aulaToken.getWidgets")
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
        except MitIDAuthError:
            raise
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
            response = self._aula_get(
                "aulaToken.getAulaToken",
                params={"widgetId": widget_id},
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
        except MitIDAuthError:
            raise
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
            if self.fixture_mode:
                events = await self._fixture_json(f"aula_easyiq/calendar/{child_id}", [])
                return events if isinstance(events, list) else []

            # Run the synchronous calendar request in an executor to avoid blocking
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._sync_get_calendar_events, child_id, weeks_ahead)
        except MitIDAuthError:
            raise
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
            if self.fixture_mode:
                return await self._get_calendar_events(child_id, weeks_ahead)

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
            target_dates = []
            
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
                    target_dates.append(check_date.isoformat())
                    # Find events for this business day
                    day_events = [
                        event for event in all_events 
                        if _event_start_date(event) == check_date
                    ]
                    business_day_events.extend(day_events)
                    business_days_found += 1
                
                # Move to next day
                check_date += datetime.timedelta(days=1)
            
            raw_type_counts = _event_type_counts(all_events)
            business_day_type_counts = _event_type_counts(business_day_events)
            self._record_calendar_summary(
                child_id,
                requested_business_days=days,
                requested_weeks_ahead=weeks_ahead,
                target_dates=target_dates,
                raw_event_count=len(all_events),
                business_day_event_count=len(business_day_events),
                raw_event_type_counts=raw_type_counts,
                business_day_event_type_counts=business_day_type_counts,
            )
            if not business_day_events:
                self._warn_zero_calendar_once(
                    child_id,
                    raw_event_count=len(all_events),
                    business_day_event_count=len(business_day_events),
                    event_type_counts=raw_type_counts,
                )

            week_desc = "current week" if weeks_ahead == 0 else f"{weeks_ahead} week{'s' if weeks_ahead > 1 else ''} ahead"
            _LOGGER.info(
                "Found %d events for next %d business days starting from %s "
                "(raw calendar events: %d)",
                len(business_day_events),
                days,
                week_desc,
                len(all_events),
            )
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
            self._record_calendar_week_diagnostic(
                child_id,
                weeks_ahead,
                stage="widget_token",
                token_available=bool(token),
            )
            if not token:
                _LOGGER.error("Failed to get token for EasyIQ widget")
                self._record_calendar_week_diagnostic(
                    child_id,
                    weeks_ahead,
                    stage="widget_token_failed",
                    token_available=False,
                )
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
                self._record_calendar_week_diagnostic(
                    child_id,
                    weeks_ahead,
                    stage="child_data_missing",
                    available_child_ids=list(self._children_data.keys()),
                )
                return []
            
            # EasyIQ has historically accepted different Aula identifiers in
            # the widget request depending on institution/widget context.
            actual_child_id = str(child_data.get("id", child_id))
            user_child_id = str(child_data.get("userId", child_id))
            cached_login_id = self._calendar_login_id_cache.get(str(child_id))
            x_login_candidates = []
            for candidate in (
                self.username,
                self._guardian_user_id,
                self._guardian_profile_id,
            ):
                candidate = str(candidate or "").strip()
                if candidate and candidate not in x_login_candidates:
                    x_login_candidates.append(candidate)

            request_variants: list[dict[str, str]] = []

            def add_variant(
                name: str,
                *,
                login_id: str,
                x_child: str,
                x_childfilter: str,
                x_login: str,
            ) -> None:
                variant = {
                    "name": name,
                    "login_id": str(login_id),
                    "x_child": str(x_child),
                    "x_childfilter": str(x_childfilter),
                    "x_login": str(x_login),
                }
                key = (
                    variant["login_id"],
                    variant["x_child"],
                    variant["x_childfilter"],
                    variant["x_login"],
                )
                if all(
                    (
                        existing["login_id"],
                        existing["x_child"],
                        existing["x_childfilter"],
                        existing["x_login"],
                    )
                    != key
                    for existing in request_variants
                ):
                    request_variants.append(variant)

            cached_variant = self._calendar_request_variant_cache.get(str(child_id))
            if cached_variant:
                request_variants.append(cached_variant)

            for x_login in x_login_candidates:
                # Legacy Chrome DevTools shape: child profile id as loginId,
                # child user id in the EasyIQ child headers.
                add_variant(
                    "profile-login/user-child",
                    login_id=str(cached_login_id or actual_child_id),
                    x_child=user_child_id,
                    x_childfilter=user_child_id,
                    x_login=x_login,
                )
                # Some MitID-backed accounts expose the child user id as the
                # accepted loginId.
                add_variant(
                    "user-login/user-child",
                    login_id=user_child_id,
                    x_child=user_child_id,
                    x_childfilter=user_child_id,
                    x_login=x_login,
                )
                # Some EasyIQ widgets expect the profile id in both the query
                # and child headers.
                add_variant(
                    "profile-login/profile-child",
                    login_id=actual_child_id,
                    x_child=actual_child_id,
                    x_childfilter=actual_child_id,
                    x_login=x_login,
                )
                # If EasyIQ treats loginId as the current guardian session,
                # use the current x-login candidate as loginId and keep the
                # child filter on the selected child.
                add_variant(
                    "guardian-login/user-child",
                    login_id=x_login,
                    x_child=user_child_id,
                    x_childfilter=user_child_id,
                    x_login=x_login,
                )

            _LOGGER.debug(
                "Child %s calendar request variants: %s",
                child_id,
                [variant["name"] for variant in request_variants],
            )
            
            # Calculate the target date based on weeks_ahead
            target_date = datetime.datetime.now() + datetime.timedelta(weeks=weeks_ahead)
            
            # Headers exactly like Chrome DevTools
            base_headers = {
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
                "x-institutionfilter": ",".join(self._institution_profiles) if self._institution_profiles else "",  # Dynamic institution filter
                "x-login": self.username,
                "x-userprofile": "guardian",
            }

            last_response = None
            last_params = None
            failed_attempts = []
            attempt_summaries = []
            self._record_calendar_week_diagnostic(
                child_id,
                weeks_ahead,
                stage="requesting",
                variant_count=len(request_variants),
                variants=[variant["name"] for variant in request_variants],
                request_date=target_date.isoformat() + "Z",
            )
            for variant in request_variants:
                params = {
                    "loginId": variant["login_id"],
                    "date": target_date.isoformat() + "Z",  # Support different weeks
                    "activityFilter": "-1",  # Try with no filter first
                    "courseFilter": "-1",
                    "textFilter": "",
                    "ownWeekPlan": "false",
                }
                headers = {
                    **base_headers,
                    # Custom headers from Chrome DevTools
                    "x-child": variant["x_child"],
                    "x-childfilter": variant["x_childfilter"],
                    "x-login": variant["x_login"],
                }

                _LOGGER.debug("Calendar events request - URL: %s", url)
                _LOGGER.debug("Calendar events request - Params: %s", params)
                _LOGGER.debug(
                    "Calendar events request variant %s - x-child: %s, "
                    "x-childfilter: %s, x-login: %s",
                    variant["name"],
                    variant["x_child"],
                    variant["x_childfilter"],
                    variant["x_login"],
                )

                # Make the request using the authenticated session
                response = self._ensure_sync_session().get(
                    url, params=params, headers=headers, verify=True
                )
                last_response = response
                last_params = params

                if response.status_code != 200:
                    failed_attempts.append(
                        f"{variant['name']}={response.status_code}"
                    )
                    attempt_summaries.append(
                        {
                            "variant": variant["name"],
                            "status_code": response.status_code,
                            "content_type": response.headers.get("content-type", ""),
                            "events": None,
                        }
                    )
                    _LOGGER.debug(
                        "Calendar events variant %s returned status %s",
                        variant["name"],
                        response.status_code,
                    )
                    continue

                try:
                    # Debug: Log response info
                    _LOGGER.debug(f"Response status: {response.status_code}")
                    _LOGGER.debug(f"Content encoding: {response.headers.get('content-encoding', 'none')}")
                    _LOGGER.debug(f"Content type: {response.headers.get('content-type', 'none')}")

                    # Let requests handle decompression automatically (including Brotli)
                    # This is more reliable than manual decompression
                    json_error_text = None
                    payload_summary: dict[str, Any] = {}
                    manual_brotli_error = None
                    try:
                        payload = response.json()
                        payload_summary = _payload_summary(payload)
                        raw_events = _extract_calendar_event_list(
                            payload,
                            normalize=False,
                        )
                        events = [
                            _normalize_calendar_event(event)
                            for event in raw_events
                        ]
                        if raw_events:
                            payload_summary["sample_event_keys"] = [
                                str(key) for key in list(raw_events[0].keys())[:30]
                            ]
                            payload_summary["sample_event_preview"] = _event_preview(
                                raw_events[0]
                            )
                            payload_summary["normalized_sample_event_preview"] = (
                                _event_preview(events[0])
                            )
                        _LOGGER.debug(f"Successfully parsed JSON response with {len(events)} events")
                    except Exception as json_error:
                        json_error_text = str(json_error)
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
                                payload = json.loads(json_text)
                                payload_summary = _payload_summary(payload)
                                raw_events = _extract_calendar_event_list(
                                    payload,
                                    normalize=False,
                                )
                                events = [
                                    _normalize_calendar_event(event)
                                    for event in raw_events
                                ]
                                if raw_events:
                                    payload_summary["sample_event_keys"] = [
                                        str(key)
                                        for key in list(raw_events[0].keys())[:30]
                                    ]
                                    payload_summary["sample_event_preview"] = (
                                        _event_preview(raw_events[0])
                                    )
                                    payload_summary["normalized_sample_event_preview"] = (
                                        _event_preview(events[0])
                                    )
                                _LOGGER.debug("Manual Brotli decompression successful")
                            except Exception as decomp_error:
                                manual_brotli_error = str(decomp_error)
                                _LOGGER.debug(f"Manual Brotli decompression also failed: {decomp_error}")
                                events = []
                        else:
                            events = []

                    attempt_summaries.append(
                        {
                            "variant": variant["name"],
                            "status_code": response.status_code,
                            "content_type": response.headers.get("content-type", ""),
                            "content_encoding": response.headers.get("content-encoding", ""),
                            "events": len(events),
                            "payload": payload_summary,
                            "json_error": json_error_text,
                            "manual_brotli_error": manual_brotli_error,
                        }
                    )
                    self._calendar_login_id_cache[str(child_id)] = variant["login_id"]
                    self._calendar_request_variant_cache[str(child_id)] = variant
                    self._record_calendar_week_diagnostic(
                        child_id,
                        weeks_ahead,
                        stage="success",
                        successful_variant=variant["name"],
                        status_code=response.status_code,
                        raw_event_count=len(events),
                        event_type_counts=_event_type_counts(events),
                        attempts=attempt_summaries[-8:],
                    )
                    _LOGGER.info("🎉 Successfully retrieved %d calendar events!", len(events))

                    # Log some sample data for debugging
                    if events and len(events) > 0:
                        sample_event = events[0]
                        _LOGGER.debug(f"Sample event keys: {list(sample_event.keys())}")
                        _LOGGER.debug(f"Sample event: {sample_event}")

                    return events
                except Exception as e:
                    _LOGGER.error("Failed to parse calendar events JSON: %s", e)
                    attempt_summaries.append(
                        {
                            "variant": variant["name"],
                            "status_code": response.status_code,
                            "content_type": response.headers.get("content-type", ""),
                            "events": None,
                            "parse_error": str(e),
                        }
                    )
                    self._record_calendar_week_diagnostic(
                        child_id,
                        weeks_ahead,
                        stage="parse_failed",
                        attempts=attempt_summaries[-8:],
                    )
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

            if last_response is not None:
                response_preview = " ".join(last_response.text.split())[:500]
                _LOGGER.error(
                    "Calendar events API returned status %s for week offset %s; "
                    "attempts: %s; response preview: %r",
                    last_response.status_code,
                    weeks_ahead,
                    ", ".join(failed_attempts),
                    response_preview,
                )
                _LOGGER.debug("Calendar events failed request params: %s", last_params)
                self._record_calendar_week_diagnostic(
                    child_id,
                    weeks_ahead,
                    stage="http_failed",
                    status_code=last_response.status_code,
                    failed_attempts=failed_attempts,
                    attempts=attempt_summaries[-8:],
                )
            return []
                
        except MitIDAuthError:
            raise
        except Exception as err:
            _LOGGER.error("Failed to get calendar events: %s", err)
            self._record_calendar_week_diagnostic(
                child_id,
                weeks_ahead,
                stage="exception",
                error=str(err),
            )
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
                return {
                    "week": "No calendar events",
                    "html_content": "<p>No scheduled events found.</p>",
                    "events": [],
                    "raw_data": [],
                    "raw_event_count": 0,
                    "event_type_counts": {},
                }
            
            # Filter for regular calendar events. EasyIQ returns lesson rows
            # as itemType 9 and regular calendar rows as itemType 8.
            weekplan_events = _events_of_types(events, _WEEKPLAN_EVENT_TYPES)
            
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
                "raw_data": events,
                "raw_event_count": len(events),
                "event_type_counts": _event_type_counts(events),
            }
            
        except MitIDAuthError:
            raise
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
                return {
                    "week": "No calendar events",
                    "html_content": "<p>No homework assignments found.</p>",
                    "assignments": [],
                    "raw_data": [],
                    "raw_event_count": 0,
                    "event_type_counts": {},
                }
            
            # Filter for homework/assignment events.
            homework_events = _events_of_types(events, _HOMEWORK_EVENT_TYPES)
            
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
                "raw_data": events,
                "raw_event_count": len(events),
                "event_type_counts": _event_type_counts(events),
            }
            
        except MitIDAuthError:
            raise
        except Exception as err:
            _LOGGER.error("Failed to get homework for child %s: %s", child_id, err)
            return {}

    async def get_messages(self) -> dict[str, Any]:
        """Get messages data from Aula API."""
        if self.fixture_mode:
            message = await self._fixture_json("aula_easyiq/messages", {})
            if isinstance(message, dict):
                self.unread_messages = int(message.get("unread_count", 0) or 0)
                return message
            return {}

        if not self._authenticated:
            _LOGGER.warning("Not authenticated - cannot fetch messages")
            return {}
        
        try:
            # Run the synchronous message request in an executor to avoid blocking
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._sync_get_messages)
        except MitIDAuthError:
            raise
        except Exception as err:
            _LOGGER.error("Failed to get messages: %s", err)
            return {}
    
    def _sync_get_messages(self) -> dict[str, Any]:
        """Synchronous version of messages retrieval."""
        try:
            # Get message threads from Aula API
            _LOGGER.debug("Fetching message threads...")
            mesres = self._aula_get(
                "messaging.getThreads",
                params={
                    "sortOn": "date",
                    "orderDirection": "desc",
                    "page": 0,
                },
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
                threadres = self._aula_get(
                    "messaging.getMessagesForThread",
                    params={
                        "threadId": threadid,
                        "page": 0,
                    },
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
            
        except MitIDAuthError:
            raise
        except Exception as err:
            _LOGGER.error(f"Error getting messages: {err}")
            return {}

    async def get_presence(self, child_id: str) -> dict[str, Any]:
        """Get presence data using the proper Aula API."""
        if self.fixture_mode:
            presence = await self._fixture_json(f"aula_easyiq/presence/{child_id}", {})
            if isinstance(presence, dict):
                presence.setdefault("last_updated", datetime.datetime.now().isoformat())
                return presence
            return {}

        if not self._authenticated:
            _LOGGER.warning("Not authenticated - cannot fetch presence")
            return {}
        
        try:
            # Get the child's actual ID for the API call (same as calendar API)
            child_data = self._children_data.get(child_id)
            if not child_data:
                _LOGGER.error("Child data not found for %s", child_id)
                return {
                    "status": "Error - Child Not Found",
                    "status_code": 0,
                    "last_updated": datetime.datetime.now().isoformat()
                }
            
            # Use the child's actual ID for the API call (this was the bug!)
            actual_child_id = child_data.get("id", child_id)
            _LOGGER.debug(f"Child {child_id} -> using actual_child_id: {actual_child_id} for presence API call")
            
            params = {f"childIds[]": actual_child_id}
            
            _LOGGER.debug("Fetching presence data for child %s (actual ID: %s)", child_id, actual_child_id)
            
            # Use synchronous session in thread pool to maintain authentication cookies
            import asyncio
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._aula_get("presence.getDailyOverview", params=params)
            )
            
            if response.status_code != 200:
                _LOGGER.error("Failed to fetch presence data: HTTP %s", response.status_code)
                return {
                    "status": "Error - API Failed",
                    "status_code": 0,
                    "last_updated": datetime.datetime.now().isoformat()
                }
            
            data = response.json()
            
            if data.get("status", {}).get("code") != 0:
                _LOGGER.error("API returned error: %s", data.get("status", {}).get("message", "Unknown"))
                return {
                    "status": "Error - API Error",
                    "status_code": 0,
                    "last_updated": datetime.datetime.now().isoformat()
                }
            
            # Extract presence data for this child
            presence_entries = data.get("data", [])
            for entry in presence_entries:
                if str(entry.get("institutionProfile", {}).get("id")) == str(actual_child_id):
                        # Extract the relevant information
                        status_code = entry.get("status", 0)
                        check_in_time = entry.get("checkInTime", "")
                        check_out_time = entry.get("checkOutTime", "")
                        entry_time = entry.get("entryTime", "")
                        exit_time = entry.get("exitTime", "")
                        comment = entry.get("comment", "")
                        exit_with = entry.get("exitWith", "")
                        
                        # Format status text based on status code
                        try:
                            from .const import PRESENCE_STATUS
                        except ImportError:
                            # Fallback for testing
                            PRESENCE_STATUS = {
                                0: "IKKE KOMMET",      # Not arrived
                                1: "SYG",              # Sick
                                2: "FERIE/FRI",        # Holiday/Free
                                3: "KOMMET/TIL STEDE", # Arrived/Present
                                4: "PÅ TUR",           # On trip
                                5: "SOVER",            # Sleeping
                                8: "HENTET/GÅET",      # Picked up/Gone
                            }
                        status_text = PRESENCE_STATUS.get(status_code, f"Unknown Status ({status_code})")
                        
                        return {
                            "status": status_text,
                            "status_code": status_code,
                            "check_in_time": check_in_time,
                            "check_out_time": check_out_time,
                            "entry_time": entry_time,
                            "exit_time": exit_time,
                            "comment": comment,
                            "exit_with": exit_with,
                            "last_updated": datetime.datetime.now().isoformat()
                        }
            
            # Child not found in response
            _LOGGER.warning("Child %s not found in presence data", child_id)
            return {
                "status": "No Data",
                "status_code": 0,
                "last_updated": datetime.datetime.now().isoformat()
            }
            
        except MitIDAuthError:
            raise
        except Exception as err:
            _LOGGER.error("Failed to get presence for child %s: %s", child_id, err)
            return {
                "status": "Error",
                "status_code": 0,
                "last_updated": datetime.datetime.now().isoformat()
            }

    async def update_data(self, weekplan_days: int = 5, homework_days: int = 5) -> None:
        """Update all data from the API using business days approach."""
        try:
            self.update_diagnostics = {
                "last_update_started": self._now_text(),
                "mode": "full",
                "weekplan_days": weekplan_days,
                "homework_days": homework_days,
            }
            # First authenticate if not already authenticated
            await self.authenticate()
            
            # Update children data
            self.children = await self.get_children()
            self.update_diagnostics.update(
                {
                    "children_count": len(self.children),
                    "children": [
                        child.get("name", "Unknown") for child in self.children
                    ],
                }
            )
            if not self.children:
                _LOGGER.warning("EasyIQ update found no children after authentication")
            
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
                    
                    # Get events for configured number of business days
                    try:
                        # Use the maximum of weekplan_days and homework_days to get all needed events
                        max_days = max(weekplan_days, homework_days)
                        business_day_events = await self.get_calendar_events_for_business_days(child_id, max_days)
                        
                        # Separate weekplan and homework events
                        all_weekplan_events = _events_of_types(
                            business_day_events,
                            _WEEKPLAN_EVENT_TYPES,
                        )
                        all_homework_events = _events_of_types(
                            business_day_events,
                            _HOMEWORK_EVENT_TYPES,
                        )
                        
                        # Filter events based on configured days
                        weekplan_events = self._filter_events_by_days(all_weekplan_events, weekplan_days)
                        homework_events = self._filter_events_by_days(all_homework_events, homework_days)
                        
                        # Store weekplan data
                        weekplan_desc = f"Next {weekplan_days} Business Day{'s' if weekplan_days != 1 else ''}"
                        self.weekplan_data[child_id] = {
                            "week": weekplan_desc,
                            "events": weekplan_events,
                            "html_content": self._build_weekplan_html(weekplan_events, weekplan_days),
                            "raw_data": business_day_events,
                            "raw_event_count": len(business_day_events),
                            "event_type_counts": _event_type_counts(business_day_events),
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
                        
                        homework_desc = f"Next {homework_days} Business Day{'s' if homework_days != 1 else ''}"
                        self.homework_data[child_id] = {
                            "week": homework_desc,
                            "assignments": homework_assignments,
                            "html_content": self._build_homework_html(homework_assignments, homework_days),
                            "raw_data": business_day_events,
                            "raw_event_count": len(business_day_events),
                            "event_type_counts": _event_type_counts(business_day_events),
                        }
                        
                        # Get presence data for this child
                        self.presence_data[child_id] = await self.get_presence(child_id)
                        
                        _LOGGER.info(
                            "Updated data for %s: %d raw events, %d weekplan "
                            "events, %d homework events, item types: %s",
                            child_name,
                            len(business_day_events),
                            len(weekplan_events),
                            len(homework_events),
                            _event_type_counts(business_day_events),
                        )
                        
                    except MitIDAuthError:
                        raise
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
            self.update_diagnostics["last_update_finished"] = self._now_text()
            
        except MitIDAuthError:
            raise
        except Exception as err:
            _LOGGER.error("Failed to update data: %s", err)
            self.update_diagnostics.update(
                {
                    "last_update_finished": self._now_text(),
                    "error": str(err),
                }
            )
            raise

    async def update_data_selective(
        self,
        update_weekplan: bool = True,
        update_homework: bool = True,
        update_presence: bool = True,
        update_messages: bool = True,
        weekplan_days: int = 5,
        homework_days: int = 5
    ) -> None:
        """Update specific data types from the API based on flags."""
        try:
            self.update_diagnostics = {
                "last_update_started": self._now_text(),
                "mode": "selective",
                "update_weekplan": update_weekplan,
                "update_homework": update_homework,
                "update_presence": update_presence,
                "update_messages": update_messages,
                "weekplan_days": weekplan_days,
                "homework_days": homework_days,
            }
            # First authenticate if not already authenticated
            await self.authenticate()
            
            # Always update children data (lightweight operation)
            self.children = await self.get_children()
            self.update_diagnostics.update(
                {
                    "children_count": len(self.children),
                    "children": [
                        child.get("name", "Unknown") for child in self.children
                    ],
                }
            )
            if not self.children:
                _LOGGER.warning("EasyIQ update found no children after authentication")
            
            # Initialize data structures if they don't exist
            if not hasattr(self, 'weekplan_data'):
                self.weekplan_data = {}
            if not hasattr(self, 'homework_data'):
                self.homework_data = {}
            if not hasattr(self, 'presence_data'):
                self.presence_data = {}
            
            # Update data selectively for each child
            for child in self.children:
                child_id = child.get("id", "")
                child_name = child.get("name", "Unknown")
                if child_id:
                    _LOGGER.debug(f"Selective update for child: {child_name} (ID: {child_id})")
                    _LOGGER.debug(f"  Flags - weekplan: {update_weekplan}, homework: {update_homework}, presence: {update_presence}")
                    _LOGGER.debug(f"  Days - weekplan: {weekplan_days}, homework: {homework_days}")
                    
                    # Update weekplan and/or homework data if requested
                    if update_weekplan or update_homework:
                        try:
                            # Use the maximum of weekplan_days and homework_days to get all needed events
                            max_days = max(weekplan_days, homework_days)
                            business_day_events = await self.get_calendar_events_for_business_days(child_id, max_days)
                            _LOGGER.info(
                                "Calendar data for %s: %d raw business-day events",
                                child_name,
                                len(business_day_events),
                            )
                            
                            if update_weekplan:
                                # Separate and filter weekplan events
                                all_weekplan_events = _events_of_types(
                                    business_day_events,
                                    _WEEKPLAN_EVENT_TYPES,
                                )
                                weekplan_events = self._filter_events_by_days(all_weekplan_events, weekplan_days)
                                weekplan_desc = f"Next {weekplan_days} Business Day{'s' if weekplan_days != 1 else ''}"
                                self.weekplan_data[child_id] = {
                                    "week": weekplan_desc,
                                    "events": weekplan_events,
                                    "html_content": self._build_weekplan_html(weekplan_events, weekplan_days),
                                    "raw_data": business_day_events,
                                    "raw_event_count": len(business_day_events),
                                    "event_type_counts": _event_type_counts(business_day_events),
                                    "last_updated": datetime.datetime.now().isoformat()
                                }
                                _LOGGER.info(
                                    "Updated weekplan for %s: %d events after filtering",
                                    child_name,
                                    len(weekplan_events),
                                )
                            
                            if update_homework:
                                # Separate and filter homework events
                                all_homework_events = _events_of_types(
                                    business_day_events,
                                    _HOMEWORK_EVENT_TYPES,
                                )
                                homework_events = self._filter_events_by_days(all_homework_events, homework_days)
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
                                
                                homework_desc = f"Next {homework_days} Business Day{'s' if homework_days != 1 else ''}"
                                self.homework_data[child_id] = {
                                    "week": homework_desc,
                                    "assignments": homework_assignments,
                                    "html_content": self._build_homework_html(homework_assignments, homework_days),
                                    "raw_data": business_day_events,
                                    "raw_event_count": len(business_day_events),
                                    "event_type_counts": _event_type_counts(business_day_events),
                                    "last_updated": datetime.datetime.now().isoformat()
                                }
                                _LOGGER.info(
                                    "Updated homework for %s: %d assignments after filtering",
                                    child_name,
                                    len(homework_events),
                                )
                                
                        except MitIDAuthError:
                            raise
                        except Exception as calendar_err:
                            _LOGGER.error(f"Failed to update calendar data for child {child_name}: {calendar_err}")
                    
                    # Update presence data if requested
                    if update_presence:
                        try:
                            self.presence_data[child_id] = await self.get_presence(child_id)
                            _LOGGER.debug(f"Updated presence for {child_name}")
                        except MitIDAuthError:
                            raise
                        except Exception as presence_err:
                            _LOGGER.error(f"Failed to update presence for child {child_name}: {presence_err}")
            
            # Update messages if requested
            if update_messages:
                try:
                    self.message = await self.get_messages()
                    self.unread_messages = self.message.get("unread_count", 0) if isinstance(self.message, dict) else 0
                    _LOGGER.debug(f"Updated messages: {self.unread_messages} unread")
                except MitIDAuthError:
                    raise
                except Exception as messages_err:
                    _LOGGER.error(f"Failed to update messages: {messages_err}")
            
            _LOGGER.debug("Selective data update completed successfully")
            self.update_diagnostics["last_update_finished"] = self._now_text()
            
        except MitIDAuthError:
            raise
        except Exception as err:
            _LOGGER.error("Failed to update data selectively: %s", err)
            self.update_diagnostics.update(
                {
                    "last_update_finished": self._now_text(),
                    "error": str(err),
                }
            )
            raise

    def _filter_events_by_days(self, events: list[dict[str, Any]], days: int) -> list[dict[str, Any]]:
        """Filter events to only include those within the specified number of business days."""
        if self.fixture_mode:
            return events

        if not events or days <= 0:
            return []
        
        # Get current date
        current_date = datetime.datetime.now().date()
        
        # Calculate the target business days
        business_days_found = 0
        check_date = current_date
        target_dates = []
        
        while business_days_found < days:
            # Skip weekends (Saturday=5, Sunday=6)
            if check_date.weekday() < 5:  # Monday=0 to Friday=4
                target_dates.append(check_date)
                business_days_found += 1
            check_date += datetime.timedelta(days=1)
        
        # Filter events to only include those on target dates
        filtered_events = []
        for event in events:
            event_start_date = _event_start_date(event)
            if event_start_date in target_dates:
                filtered_events.append(event)
        
        return filtered_events

    def _build_weekplan_html(self, weekplan_events: list[dict[str, Any]], days: int = 5) -> str:
        """Build HTML content for weekplan events."""
        day_text = f"{days} Business Day{'s' if days != 1 else ''}"
        html = f"<h2>Next {day_text} - Schedule</h2>"
        
        if not weekplan_events:
            html += "<p>No scheduled events found.</p>"
            return html
        
        # Group events by date
        events_by_date = {}
        for event in weekplan_events:
            event_start_date = _event_start_date(event)
            if event_start_date:
                events_by_date.setdefault(event_start_date, []).append(event)
        
        # Sort dates and build HTML
        for date_obj in sorted(events_by_date.keys()):
            try:
                # Convert to readable date format
                readable_date = date_obj.strftime("%A, %B %d, %Y")
                html += f"<h3>{readable_date}</h3>"
                
                # Sort events by time for this date
                day_events = sorted(events_by_date[date_obj], key=lambda x: str(x.get("start", "")))
                
                for event in day_events:
                    start_time = event.get("start", "")
                    end_time = event.get("end", "")
                    courses = event.get("courses", "")
                    activities = event.get("activities", "")
                    description = event.get("description", "")
                    
                    # Extract time part
                    start_time_part = _event_time_text(start_time)
                    end_time_part = _event_time_text(end_time)
                    
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
    
    def _build_homework_html(self, homework_assignments: list[dict[str, Any]], days: int = 5) -> str:
        """Build HTML content for homework assignments."""
        day_text = f"{days} Business Day{'s' if days != 1 else ''}"
        html = f"<h2>Next {day_text} - Homework</h2>"
        
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
            if self.fixture_mode:
                return await self._authenticate_fixture()

            # Run synchronous token validation/profile discovery in an executor.
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._authenticate_sync)
            return result
        except MitIDAuthError:
            raise
        except Exception as err:
            _LOGGER.error("Unexpected error during authentication: %s", err)
            raise EasyIQAuthError(f"Unexpected auth error: {err}") from err
