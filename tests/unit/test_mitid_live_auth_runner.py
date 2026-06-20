from __future__ import annotations

import asyncio
import importlib.util
import sys
import time
import unittest
from pathlib import Path
from types import SimpleNamespace


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


mitid_auth = load_module("mitid_auth_live_runner", "mitid_auth.py")


class FakeFlowManager:
    def __init__(self) -> None:
        self.configured_flow_ids: list[str] = []

    async def async_configure(self, flow_id: str) -> None:
        self.configured_flow_ids.append(flow_id)


class FakeHass:
    def __init__(self) -> None:
        self.flow = FakeFlowManager()
        self.config_entries = SimpleNamespace(flow=self.flow)

    async def async_add_executor_job(self, func):
        return func()


class FakeAulaLoginClient:
    def __init__(self, *, mitid_username: str, **_: object) -> None:
        self.mitid_username = mitid_username

    def authenticate(self) -> dict:
        return {
            "success": True,
            "tokens": {
                "access_token": "access-token",
                "refresh_token": "refresh-token",
                "expires_in": 3600,
            },
        }

    def get_qr_codes_svg(self) -> tuple[str, str]:
        return ("<svg>one</svg>", "<svg>two</svg>")


def failing_client_factory(**_: object) -> object:
    raise RuntimeError("client setup failed")


class MitIDLiveAuthRunnerTests(unittest.TestCase):
    def test_public_status_exposes_live_qr_svg(self) -> None:
        manager = mitid_auth.MitIDAuthManager()
        session = manager.start_session("guardian@example.test")
        manager.attach_client(
            session.flow_id,
            FakeAulaLoginClient(mitid_username="guardian@example.test"),
        )

        status = manager.public_status(session.flow_id)

        self.assertIsNotNone(status)
        assert status is not None
        self.assertEqual("pending", status["status"])
        self.assertIn(status["qr_svg"], ("<svg>one</svg>", "<svg>two</svg>"))

    def test_live_auth_runner_completes_pending_session(self) -> None:
        manager = mitid_auth.MitIDAuthManager()
        session = manager.start_session(
            "guardian@example.test",
            ha_flow_id="ha-flow-id",
        )

        hass = FakeHass()
        asyncio.run(
            mitid_auth.run_live_mitid_auth(
                hass,
                manager,
                session.flow_id,
                client_factory=FakeAulaLoginClient,
            )
        )

        completed = manager.get_session(session.flow_id)
        self.assertIsNotNone(completed)
        assert completed is not None
        self.assertTrue(completed.complete)
        self.assertEqual("access-token", completed.token_state.access_token)
        self.assertEqual("refresh-token", completed.token_state.refresh_token)
        self.assertGreater(completed.token_state.expires_at, time.time())
        self.assertEqual(["ha-flow-id"], hass.flow.configured_flow_ids)

    def test_live_auth_runner_marks_session_failed_when_client_setup_fails(self) -> None:
        manager = mitid_auth.MitIDAuthManager()
        session = manager.start_session(
            "guardian@example.test",
            ha_flow_id="ha-flow-id",
        )

        hass = FakeHass()
        asyncio.run(
            mitid_auth.run_live_mitid_auth(
                hass,
                manager,
                session.flow_id,
                client_factory=failing_client_factory,
            )
        )

        failed = manager.get_session(session.flow_id)
        self.assertIsNotNone(failed)
        assert failed is not None
        self.assertEqual("failed", failed.status)
        self.assertEqual("client setup failed", failed.message)
        self.assertEqual(["ha-flow-id"], hass.flow.configured_flow_ids)


if __name__ == "__main__":
    unittest.main()
