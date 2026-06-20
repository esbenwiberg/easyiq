from __future__ import annotations

import asyncio
import datetime
import importlib.util
import sys
import time
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
INTEGRATION_DIR = ROOT / "custom_components" / "aula_easyiq"


def load_module(name: str, filename: str):
    sys.path.insert(0, str(INTEGRATION_DIR))
    spec = importlib.util.spec_from_file_location(name, INTEGRATION_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


mitid_auth = load_module("mitid_auth", "mitid_auth.py")
client_module = load_module("easyiq_client_token_test", "client.py")


class FakeResponse:
    def __init__(
        self,
        payload: dict[str, Any] | list[dict[str, Any]],
        status_code: int = 200,
        text: str = "",
    ) -> None:
        self._payload = payload
        self.status_code = status_code
        self.headers: dict[str, str] = {}
        self.content = b""
        self.text = text

    def json(self) -> dict[str, Any] | list[dict[str, Any]]:
        return self._payload


class FakeSession:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        params = dict(kwargs.get("params") or {})
        self.calls.append({"url": url, "params": params, "headers": kwargs.get("headers")})
        method = params.get("method")

        if method == "profiles.getProfilesByLogin":
            return FakeResponse(
                {
                    "data": {
                        "profiles": [
                            {
                                "institutionProfiles": [{"institutionCode": 123}],
                                "children": [
                                    {"userId": 100, "id": 200, "name": "Ada"}
                                ],
                            }
                        ]
                    }
                }
            )

        if method == "profiles.getProfileContext":
            return FakeResponse(
                {"data": {"institutionProfile": {"relations": [{"id": 200}]}}}
            )

        if method == "aulaToken.getWidgets":
            return FakeResponse(
                {"data": [{"widgetId": "0128", "widgetName": "Weekplan"}]}
            )

        if method == "aulaToken.getAulaToken":
            return FakeResponse({"data": "widget-token"})

        if method == "messaging.getThreads":
            return FakeResponse({"data": {"threads": [{"id": 55, "read": False}]}})

        if method == "messaging.getMessagesForThread":
            return FakeResponse(
                {
                    "data": {
                        "subject": "Hello",
                        "messages": [
                            {
                                "messageType": "Message",
                                "text": {"html": "Body"},
                                "sender": {"fullName": "Teacher"},
                            }
                        ],
                    }
                }
            )

        if method == "presence.getDailyOverview":
            return FakeResponse(
                {
                    "status": {"code": 0},
                    "data": [
                        {
                            "institutionProfile": {"id": 200},
                            "status": 3,
                            "checkInTime": "08:00:00",
                        }
                    ],
                }
            )

        return FakeResponse({}, status_code=404)


class CalendarFallbackSession(FakeSession):
    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        params = dict(kwargs.get("params") or {})
        if "CalendarGetWeekplanEvents" in url:
            self.calls.append(
                {
                    "url": url,
                    "params": params,
                    "headers": kwargs.get("headers"),
                }
            )
            if params.get("loginId") == "200":
                return FakeResponse({}, status_code=500, text="wrong child identity")
            if params.get("loginId") == "100":
                return FakeResponse(
                    [
                        {
                            "itemType": 9,
                            "start": "2026/06/22 08:00",
                            "end": "2026/06/22 09:00",
                            "courses": "Math",
                        }
                    ]
                )
        return super().get(url, **kwargs)


class CalendarGuardianLoginSession(FakeSession):
    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        params = dict(kwargs.get("params") or {})
        if params.get("method") == "profiles.getProfileContext":
            return FakeResponse(
                {
                    "data": {
                        "userId": "guardian-42",
                        "institutionProfile": {
                            "id": "guardian-profile-99",
                            "relations": [{"id": 200}],
                        },
                    }
                }
            )

        if "CalendarGetWeekplanEvents" in url:
            headers = kwargs.get("headers") or {}
            self.calls.append(
                {
                    "url": url,
                    "params": params,
                    "headers": headers,
                }
            )
            if headers.get("x-login") == "guardian-42" and params.get("loginId") == "200":
                return FakeResponse(
                    [
                        {
                            "itemType": 9,
                            "start": "2026/06/22 10:00",
                            "end": "2026/06/22 11:00",
                            "courses": "Danish",
                        }
                    ]
                )
            return FakeResponse({}, status_code=500, text="wrong login context")

        return super().get(url, **kwargs)


class RecordingRefresher:
    def __init__(self, token_state: Any | None = None, fail: Exception | None = None) -> None:
        self.token_state = token_state
        self.fail = fail
        self.calls = 0

    def refresh(self, token_state: Any) -> Any:
        self.calls += 1
        if self.fail is not None:
            raise self.fail
        return self.token_state


class EasyIQTokenAuthTests(unittest.TestCase):
    def _next_business_date(self) -> datetime.date:
        check_date = datetime.datetime.now().date()
        while check_date.weekday() >= 5:
            check_date += datetime.timedelta(days=1)
        return check_date

    def test_token_backed_aula_api_requests_include_access_token(self) -> None:
        fake_session = FakeSession()
        token_state = mitid_auth.AulaTokenState(
            access_token="access-123",
            refresh_token="refresh-123",
            expires_at=time.time() + 3600,
        )
        client = client_module.EasyIQClient(
            "guardian@example.test",
            token_state,
            session_factory=lambda: fake_session,
        )

        self.assertTrue(client.login())
        client.get_widgets()
        self.assertEqual("Bearer widget-token", client.get_token("0128"))
        asyncio.run(client.get_messages())
        presence = asyncio.run(client.get_presence("100"))

        self.assertEqual("KOMMET/TIL STEDE", presence["status"])
        methods = {
            call["params"].get("method"): call["params"].get("access_token")
            for call in fake_session.calls
            if call["params"].get("method")
        }
        self.assertEqual("access-123", methods["profiles.getProfilesByLogin"])
        self.assertEqual("access-123", methods["profiles.getProfileContext"])
        self.assertEqual("access-123", methods["aulaToken.getWidgets"])
        self.assertEqual("access-123", methods["aulaToken.getAulaToken"])
        self.assertEqual("access-123", methods["messaging.getThreads"])
        self.assertEqual("access-123", methods["messaging.getMessagesForThread"])
        self.assertEqual("access-123", methods["presence.getDailyOverview"])
        self.assertEqual([{"id": "100", "name": "Ada"}], client.children)

    def test_token_refresh_and_reauth(self) -> None:
        fake_session = FakeSession()
        refreshed = mitid_auth.AulaTokenState(
            access_token="new-access",
            refresh_token="new-refresh",
            expires_at=time.time() + 3600,
        )
        updates: list[Any] = []
        refresher = RecordingRefresher(refreshed)
        client = client_module.EasyIQClient(
            "guardian@example.test",
            mitid_auth.AulaTokenState(
                access_token="old-access",
                refresh_token="old-refresh",
                expires_at=time.time() - 10,
            ),
            token_refresher=refresher,
            on_token_update=updates.append,
            session_factory=lambda: fake_session,
        )

        self.assertTrue(client.login())
        self.assertEqual(1, refresher.calls)
        self.assertEqual([refreshed], updates)
        self.assertEqual("new-access", fake_session.calls[0]["params"]["access_token"])

        failing_client = client_module.EasyIQClient(
            "guardian@example.test",
            mitid_auth.AulaTokenState(
                access_token="old-access",
                refresh_token="old-refresh",
                expires_at=time.time() - 10,
            ),
            token_refresher=RecordingRefresher(
                fail=mitid_auth.MitIDAuthRejected("refresh rejected")
            ),
            session_factory=lambda: FakeSession(),
        )

        with self.assertRaises(mitid_auth.MitIDAuthRejected):
            failing_client._authenticate_sync()

    def test_calendar_events_fall_back_to_child_user_id_when_profile_id_fails(self) -> None:
        fake_session = CalendarFallbackSession()
        token_state = mitid_auth.AulaTokenState(
            access_token="access-123",
            refresh_token="refresh-123",
            expires_at=time.time() + 3600,
        )
        client = client_module.EasyIQClient(
            "guardian@example.test",
            token_state,
            session_factory=lambda: fake_session,
        )

        self.assertTrue(client.login())

        events = client._sync_get_calendar_events("100")

        calendar_login_ids = [
            call["params"]["loginId"]
            for call in fake_session.calls
            if "CalendarGetWeekplanEvents" in call["url"]
        ]
        self.assertEqual(["200", "100"], calendar_login_ids)
        self.assertEqual("Math", events[0]["courses"])
        self.assertEqual("100", client._calendar_login_id_cache["100"])

    def test_calendar_events_fall_back_to_guardian_login_context(self) -> None:
        fake_session = CalendarGuardianLoginSession()
        token_state = mitid_auth.AulaTokenState(
            access_token="access-123",
            refresh_token="refresh-123",
            expires_at=time.time() + 3600,
        )
        client = client_module.EasyIQClient(
            "guardian@example.test",
            token_state,
            session_factory=lambda: fake_session,
        )

        self.assertTrue(client.login())

        events = client._sync_get_calendar_events("100")

        calendar_calls = [
            call
            for call in fake_session.calls
            if "CalendarGetWeekplanEvents" in call["url"]
        ]
        self.assertEqual("Danish", events[0]["courses"])
        self.assertIn(
            "guardian-42",
            {call["headers"]["x-login"] for call in calendar_calls},
        )
        self.assertEqual(
            "guardian-42",
            client._calendar_request_variant_cache["100"]["x_login"],
        )

    def test_calendar_filter_accepts_iso_event_dates(self) -> None:
        client = client_module.EasyIQClient(
            "guardian@example.test",
            mitid_auth.AulaTokenState(
                access_token="access-123",
                refresh_token="refresh-123",
                expires_at=time.time() + 3600,
            ),
            session_factory=lambda: FakeSession(),
        )
        next_business_date = self._next_business_date()

        events = client._filter_events_by_days(
            [
                {
                    "itemType": 9,
                    "start": f"{next_business_date.isoformat()}T08:00:00Z",
                    "courses": "Math",
                }
            ],
            1,
        )

        self.assertEqual(1, len(events))
        self.assertEqual("Math", events[0]["courses"])

    def test_event_type_filter_accepts_string_item_type(self) -> None:
        events = client_module._events_of_type(
            [
                {
                    "itemType": "9",
                    "start": "2026-06-22T08:00:00Z",
                    "courses": "Math",
                }
            ],
            9,
        )

        self.assertEqual(1, len(events))
        self.assertEqual("Math", events[0]["courses"])

    def test_weekplan_html_groups_iso_event_dates(self) -> None:
        client = client_module.EasyIQClient(
            "guardian@example.test",
            mitid_auth.AulaTokenState(
                access_token="access-123",
                refresh_token="refresh-123",
                expires_at=time.time() + 3600,
            ),
            session_factory=lambda: FakeSession(),
        )
        next_business_date = self._next_business_date()

        html = client._build_weekplan_html(
            [
                {
                    "itemType": 9,
                    "start": f"{next_business_date.isoformat()}T08:00:00Z",
                    "end": f"{next_business_date.isoformat()}T09:00:00Z",
                    "courses": "Math",
                }
            ],
            1,
        )

        self.assertIn("Math", html)
        self.assertIn("08:00", html)

    def test_calendar_response_wrapper_extracts_event_list(self) -> None:
        events = client_module._extract_calendar_event_list(
            {
                "data": [
                    {
                        "itemType": 9,
                        "start": "2026-06-22T08:00:00Z",
                        "courses": "Math",
                    }
                ]
            }
        )

        self.assertEqual("Math", events[0]["courses"])

    def test_calendar_response_nested_wrapper_extracts_event_list(self) -> None:
        events = client_module._extract_calendar_event_list(
            {
                "result": {
                    "calendarEvents": [
                        {
                            "itemType": 9,
                            "start": "2026-06-22T08:00:00Z",
                            "courses": "Math",
                        }
                    ]
                }
            }
        )

        self.assertEqual("Math", events[0]["courses"])


if __name__ == "__main__":
    unittest.main()
