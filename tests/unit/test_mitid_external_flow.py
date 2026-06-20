from __future__ import annotations

import asyncio
import importlib.util
import sys
import time
import types
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
INTEGRATION_DIR = ROOT / "custom_components" / "aula_easyiq"


def install_dependency_stubs() -> None:
    """Install tiny stubs for dependencies not present in this unit-test shell."""
    voluptuous = types.ModuleType("voluptuous")

    class Schema:
        def __init__(self, schema: Any) -> None:
            self.schema = schema

        def __call__(self, data: Any) -> Any:
            return data

    voluptuous.Schema = Schema
    voluptuous.Required = lambda key, **_: key
    voluptuous.Optional = lambda key, **_: key
    voluptuous.All = lambda *validators: validators[-1] if validators else (lambda value: value)
    voluptuous.Coerce = lambda value_type: value_type
    voluptuous.Range = lambda **_: (lambda value: value)
    sys.modules.setdefault("voluptuous", voluptuous)

    homeassistant = types.ModuleType("homeassistant")
    config_entries = types.ModuleType("homeassistant.config_entries")

    class ConfigFlow:
        flow_id = "ha-flow-id"
        handler = "aula_easyiq"

        def __init_subclass__(cls, **_: Any) -> None:
            super().__init_subclass__()

        def async_external_step(
            self,
            *,
            step_id: str | None = None,
            url: str,
            description_placeholders: dict[str, str] | None = None,
        ) -> dict[str, Any]:
            result = {
                "type": "external",
                "flow_id": self.flow_id,
                "handler": self.handler,
                "url": url,
            }
            if step_id is not None:
                result["step_id"] = step_id
            if description_placeholders is not None:
                result["description_placeholders"] = description_placeholders
            return result

        def async_external_step_done(self, *, next_step_id: str) -> dict[str, Any]:
            return {
                "type": "external_done",
                "flow_id": self.flow_id,
                "handler": self.handler,
                "step_id": next_step_id,
            }

        def async_create_entry(self, *, title: str, data: dict[str, Any]) -> dict[str, Any]:
            return {
                "type": "create_entry",
                "flow_id": self.flow_id,
                "handler": self.handler,
                "title": title,
                "data": data,
            }

        def async_abort(self, *, reason: str) -> dict[str, Any]:
            return {
                "type": "abort",
                "flow_id": self.flow_id,
                "handler": self.handler,
                "reason": reason,
            }

        def async_show_form(
            self,
            *,
            step_id: str,
            data_schema: Any | None = None,
            errors: dict[str, str] | None = None,
        ) -> dict[str, Any]:
            return {
                "type": "form",
                "flow_id": self.flow_id,
                "handler": self.handler,
                "step_id": step_id,
                "data_schema": data_schema,
                "errors": errors or {},
            }

    class OptionsFlow:
        def async_create_entry(self, *, title: str, data: dict[str, Any]) -> dict[str, Any]:
            return {"type": "create_entry", "title": title, "data": data}

        def async_show_form(self, *, step_id: str, data_schema: Any) -> dict[str, Any]:
            return {"type": "form", "step_id": step_id, "data_schema": data_schema}

    config_entries.ConfigFlow = ConfigFlow
    config_entries.OptionsFlow = OptionsFlow
    config_entries.ConfigEntry = object
    homeassistant.config_entries = config_entries
    sys.modules.setdefault("homeassistant", homeassistant)
    sys.modules.setdefault("homeassistant.config_entries", config_entries)

    core = types.ModuleType("homeassistant.core")
    core.HomeAssistant = object
    sys.modules.setdefault("homeassistant.core", core)

    data_entry_flow = types.ModuleType("homeassistant.data_entry_flow")
    data_entry_flow.FlowResult = dict
    sys.modules.setdefault("homeassistant.data_entry_flow", data_entry_flow)

    exceptions = types.ModuleType("homeassistant.exceptions")

    class HomeAssistantError(Exception):
        pass

    exceptions.HomeAssistantError = HomeAssistantError
    sys.modules.setdefault("homeassistant.exceptions", exceptions)

    custom_components = types.ModuleType("custom_components")
    custom_components.__path__ = [str(ROOT / "custom_components")]
    aula_easyiq = types.ModuleType("custom_components.aula_easyiq")
    aula_easyiq.__path__ = [str(INTEGRATION_DIR)]
    sys.modules.setdefault("custom_components", custom_components)
    sys.modules.setdefault("custom_components.aula_easyiq", aula_easyiq)


def load_integration_module(name: str, filename: str):
    install_dependency_stubs()
    full_name = f"custom_components.aula_easyiq.{name}"
    spec = importlib.util.spec_from_file_location(full_name, INTEGRATION_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


config_flow = load_integration_module("config_flow_external_test", "config_flow.py")
mitid_auth = sys.modules["custom_components.aula_easyiq.mitid_auth"]


class FakeHass:
    def __init__(self, manager: Any) -> None:
        self.data = {"aula_easyiq": {"mitid_auth_manager": manager}}


class MitIDExternalFlowTests(unittest.TestCase):
    def test_completed_external_step_reports_done_before_creating_entry(self) -> None:
        manager = mitid_auth.MitIDAuthManager()
        session = manager.start_session(
            "guardian@example.test",
            ha_flow_id="ha-flow-id",
        )
        token_state = mitid_auth.AulaTokenState(
            access_token="access-token",
            refresh_token="refresh-token",
            expires_at=time.time() + 3600,
        )
        manager.complete_session(session.flow_id, token_state)

        flow = config_flow.ConfigFlow()
        flow.hass = FakeHass(manager)
        flow.flow_id = "ha-flow-id"
        flow.handler = "aula_easyiq"
        flow._auth_session_id = session.flow_id
        flow._pending_user_input = {
            "mitid_username": "guardian@example.test",
            "schoolschedule": True,
            "weekplan": True,
            "homework": True,
            "presence": True,
        }

        result = asyncio.run(flow.async_step_mitid())

        self.assertEqual("external_done", result["type"])
        self.assertEqual("mitid_finish", result["step_id"])

        finish = asyncio.run(flow.async_step_mitid_finish())

        self.assertEqual("create_entry", finish["type"])
        self.assertEqual("EasyIQ (guardian@example.test)", finish["title"])
        self.assertEqual("access-token", finish["data"]["access_token"])


if __name__ == "__main__":
    unittest.main()
