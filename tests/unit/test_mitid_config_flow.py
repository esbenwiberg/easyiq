from __future__ import annotations

import importlib.util
import sys
import time
import unittest
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main()
