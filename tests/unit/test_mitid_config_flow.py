from __future__ import annotations

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


class FakeRefreshResponse:
    def __init__(
        self,
        payload: dict[str, Any],
        *,
        status_code: int = 200,
        text: str = "",
    ) -> None:
        self._payload = payload
        self.status_code = status_code
        self.text = text

    def json(self) -> dict[str, Any]:
        return self._payload


class FakeRefreshSession:
    def __init__(self, response: FakeRefreshResponse) -> None:
        self.response = response
        self.posts: list[dict[str, Any]] = []

    def post(self, url: str, **kwargs: Any) -> FakeRefreshResponse:
        self.posts.append({"url": url, **kwargs})
        return self.response


class MitIDConfigEntryDataTests(unittest.TestCase):
    def test_new_setup_data_stores_tokens_and_omits_password(self) -> None:
        manager = mitid_auth.MitIDAuthManager()
        session = manager.start_session("guardian@example.test")
        token_state = mitid_auth.AulaTokenState(
            access_token="access-token",
            refresh_token="refresh-token",
            expires_at=time.time() + 3600,
        )
        session = manager.complete_session(session.flow_id, token_state)

        entry_data = mitid_auth.build_config_entry_data(
            {
                "schoolschedule": True,
                "weekplan": False,
                "homework": True,
                "presence": False,
            },
            session,
        )

        self.assertEqual("guardian@example.test", entry_data["mitid_username"])
        self.assertEqual("mitid", entry_data["auth_method"])
        self.assertEqual("access-token", entry_data["access_token"])
        self.assertEqual("refresh-token", entry_data["refresh_token"])
        self.assertNotIn("password", entry_data)
        self.assertTrue(entry_data["schoolschedule"])
        self.assertFalse(entry_data["weekplan"])
        self.assertTrue(entry_data["homework"])
        self.assertFalse(entry_data["presence"])

    def test_aula_token_refresher_uses_oidc_refresh_token_grant(self) -> None:
        fake_session = FakeRefreshSession(
            FakeRefreshResponse(
                {
                    "access_token": "new-access",
                    "refresh_token": "new-refresh",
                    "expires_in": 1800,
                }
            )
        )
        refresher = mitid_auth.AulaTokenRefresher(
            session_factory=lambda: fake_session,
        )

        refreshed = refresher.refresh(
            mitid_auth.AulaTokenState(
                access_token="old-access",
                refresh_token="old-refresh",
                expires_at=time.time() - 10,
            )
        )

        self.assertEqual("new-access", refreshed.access_token)
        self.assertEqual("new-refresh", refreshed.refresh_token)
        self.assertGreater(refreshed.expires_at, time.time())
        self.assertEqual(
            "https://login.aula.dk/simplesaml/module.php/oidc/token.php",
            fake_session.posts[0]["url"],
        )
        self.assertEqual(
            {
                "grant_type": "refresh_token",
                "refresh_token": "old-refresh",
                "client_id": "_99949a54b8b65423862aac1bf629599ed64231607a",
            },
            fake_session.posts[0]["data"],
        )
        self.assertNotIn("json", fake_session.posts[0])
        self.assertEqual(30, fake_session.posts[0]["timeout"])
        self.assertTrue(fake_session.posts[0]["verify"])

    def test_aula_token_refresher_treats_invalid_grant_as_reauth(self) -> None:
        fake_session = FakeRefreshSession(
            FakeRefreshResponse(
                {"error": "invalid_grant"},
                status_code=400,
                text='{"error":"invalid_grant"}',
            )
        )
        refresher = mitid_auth.AulaTokenRefresher(
            session_factory=lambda: fake_session,
        )

        with self.assertRaises(mitid_auth.MitIDAuthRejected):
            refresher.refresh(
                mitid_auth.AulaTokenState(
                    access_token="old-access",
                    refresh_token="old-refresh",
                    expires_at=time.time() - 10,
                )
            )


if __name__ == "__main__":
    unittest.main()
