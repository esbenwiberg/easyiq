from __future__ import annotations

import importlib.util
import sys
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


migration = load_module("easyiq_migration_test", "migration.py")


class ConfigEntryMigrationTests(unittest.TestCase):
    def test_old_username_password_entry_requires_mitid_reauth_without_password(self) -> None:
        migrated = migration.migrate_legacy_password_entry_data(
            {
                "username": "legacy-user",
                "password": "legacy-password",
                "schoolschedule": True,
                "weekplan": False,
                "homework": True,
                "presence": True,
            }
        )

        self.assertNotIn("password", migrated)
        self.assertNotIn("username", migrated)
        self.assertEqual("legacy-user", migrated["mitid_username"])
        self.assertEqual("mitid", migrated["auth_method"])
        self.assertTrue(migrated["reauth_required"])
        self.assertTrue(migrated["schoolschedule"])
        self.assertFalse(migrated["weekplan"])
        self.assertTrue(migrated["homework"])
        self.assertTrue(migrated["presence"])


if __name__ == "__main__":
    unittest.main()
