from __future__ import annotations

import importlib.util
import unittest
from datetime import datetime, timedelta
from pathlib import Path


def load_update_policy_module():
    module_path = (
        Path(__file__).resolve().parents[2]
        / "custom_components"
        / "aula_easyiq"
        / "update_policy.py"
    )
    spec = importlib.util.spec_from_file_location("easyiq_update_policy", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


update_policy = load_update_policy_module()


class ShouldUpdateDataTypeTests(unittest.TestCase):
    def test_unknown_data_type_updates_by_default(self) -> None:
        self.assertTrue(
            update_policy.should_update_data_type(
                "calendar",
                {"weekplan": 900},
                {"weekplan": datetime(2026, 6, 20, 12, 0, 0)},
                now=datetime(2026, 6, 20, 12, 1, 0),
            )
        )

    def test_missing_last_update_is_due(self) -> None:
        self.assertTrue(
            update_policy.should_update_data_type(
                "weekplan",
                {"weekplan": 900},
                {"weekplan": None},
                now=datetime(2026, 6, 20, 12, 0, 0),
            )
        )

    def test_skips_before_interval_elapsed(self) -> None:
        now = datetime(2026, 6, 20, 12, 10, 0)

        self.assertFalse(
            update_policy.should_update_data_type(
                "presence",
                {"presence": 300},
                {"presence": now - timedelta(seconds=299)},
                now=now,
            )
        )

    def test_updates_when_interval_elapsed(self) -> None:
        now = datetime(2026, 6, 20, 12, 10, 0)

        self.assertTrue(
            update_policy.should_update_data_type(
                "presence",
                {"presence": 300},
                {"presence": now - timedelta(seconds=300)},
                now=now,
            )
        )

    def test_zero_or_negative_interval_updates_defensively(self) -> None:
        now = datetime(2026, 6, 20, 12, 10, 0)

        self.assertTrue(
            update_policy.should_update_data_type(
                "messages",
                {"messages": 0},
                {"messages": now},
                now=now,
            )
        )


if __name__ == "__main__":
    unittest.main()
