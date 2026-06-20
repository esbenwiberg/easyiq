from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
INTEGRATION_DIR = ROOT / "custom_components" / "aula_easyiq"


def install_dependency_stubs() -> None:
    """Install tiny stubs for Home Assistant and integration dependencies."""
    homeassistant = types.ModuleType("homeassistant")
    config_entries = types.ModuleType("homeassistant.config_entries")
    config_entries.ConfigEntry = object
    sys.modules["homeassistant"] = homeassistant
    sys.modules["homeassistant.config_entries"] = config_entries

    const = types.ModuleType("homeassistant.const")

    class Platform:
        SENSOR = "sensor"
        BINARY_SENSOR = "binary_sensor"
        CALENDAR = "calendar"

    const.Platform = Platform
    sys.modules["homeassistant.const"] = const

    core = types.ModuleType("homeassistant.core")
    core.HomeAssistant = object
    sys.modules["homeassistant.core"] = core

    loader = types.ModuleType("homeassistant.loader")

    async def async_get_integration(*_: Any) -> Any:
        return types.SimpleNamespace(version="test")

    loader.async_get_integration = async_get_integration
    sys.modules["homeassistant.loader"] = loader

    exceptions = types.ModuleType("homeassistant.exceptions")

    class ConfigEntryAuthFailed(Exception):
        pass

    class ConfigEntryNotReady(Exception):
        pass

    class HomeAssistantError(Exception):
        pass

    exceptions.ConfigEntryAuthFailed = ConfigEntryAuthFailed
    exceptions.ConfigEntryNotReady = ConfigEntryNotReady
    exceptions.HomeAssistantError = HomeAssistantError
    sys.modules["homeassistant.exceptions"] = exceptions

    custom_components = types.ModuleType("custom_components")
    custom_components.__path__ = [str(ROOT / "custom_components")]
    aula_easyiq = types.ModuleType("custom_components.aula_easyiq")
    aula_easyiq.__path__ = [str(INTEGRATION_DIR)]
    sys.modules["custom_components"] = custom_components
    sys.modules["custom_components.aula_easyiq"] = aula_easyiq

    integration_const = types.ModuleType("custom_components.aula_easyiq.const")
    integration_const.CONF_FIXTURE_BASE_URL = "fixture_base_url"
    integration_const.CONF_MITID_USERNAME = "mitid_username"
    integration_const.CONF_PASSWORD = "password"
    integration_const.CONF_REAUTH_REQUIRED = "reauth_required"
    integration_const.DOMAIN = "aula_easyiq"
    integration_const.STARTUP = "startup %s"
    sys.modules["custom_components.aula_easyiq.const"] = integration_const

    client = types.ModuleType("custom_components.aula_easyiq.client")

    class EasyIQAuthError(Exception):
        pass

    class EasyIQClient:
        pass

    client.EasyIQAuthError = EasyIQAuthError
    client.EasyIQClient = EasyIQClient
    sys.modules["custom_components.aula_easyiq.client"] = client

    migration = types.ModuleType("custom_components.aula_easyiq.migration")
    migration.migrate_legacy_password_entry_data = lambda data: data
    sys.modules["custom_components.aula_easyiq.migration"] = migration

    mitid_auth = types.ModuleType("custom_components.aula_easyiq.mitid_auth")

    class AulaTokenRefresher:
        pass

    class AulaTokenState:
        pass

    class MitIDAuthError(Exception):
        pass

    mitid_auth.AulaTokenRefresher = AulaTokenRefresher
    mitid_auth.AulaTokenState = AulaTokenState
    mitid_auth.MitIDAuthError = MitIDAuthError
    sys.modules["custom_components.aula_easyiq.mitid_auth"] = mitid_auth

    sensor = types.ModuleType("custom_components.aula_easyiq.sensor")

    class EasyIQDataUpdateCoordinator:
        pass

    sensor.EasyIQDataUpdateCoordinator = EasyIQDataUpdateCoordinator
    sys.modules["custom_components.aula_easyiq.sensor"] = sensor


def load_integration_init():
    stub_names = [
        "homeassistant",
        "homeassistant.config_entries",
        "homeassistant.const",
        "homeassistant.core",
        "homeassistant.loader",
        "homeassistant.exceptions",
        "custom_components",
        "custom_components.aula_easyiq",
        "custom_components.aula_easyiq.const",
        "custom_components.aula_easyiq.client",
        "custom_components.aula_easyiq.migration",
        "custom_components.aula_easyiq.mitid_auth",
        "custom_components.aula_easyiq.sensor",
    ]
    previous_modules = {name: sys.modules.get(name) for name in stub_names}

    try:
        install_dependency_stubs()
        module_name = "custom_components.aula_easyiq"
        spec = importlib.util.spec_from_file_location(
            module_name,
            INTEGRATION_DIR / "__init__.py",
            submodule_search_locations=[str(INTEGRATION_DIR)],
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        for name, previous in previous_modules.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous


integration_init = load_integration_init()


class FakeLoop:
    def __init__(self) -> None:
        self.callbacks: list[tuple[Any, tuple[Any, ...]]] = []

    def call_soon_threadsafe(self, callback: Any, *args: Any, **kwargs: Any) -> None:
        if kwargs:
            raise AssertionError(f"Unexpected loop kwargs: {kwargs}")
        self.callbacks.append((callback, args))
        callback(*args)


class FakeConfigEntries:
    def __init__(self) -> None:
        self.updates: list[tuple[Any, dict[str, Any]]] = []

    def async_update_entry(self, entry: Any, *, data: dict[str, Any]) -> None:
        self.updates.append((entry, data))


class FakeHass:
    def __init__(self) -> None:
        self.loop = FakeLoop()
        self.config_entries = FakeConfigEntries()


class FakeEntry:
    def __init__(self) -> None:
        self.data = {
            "mitid_username": "guardian@example.test",
            "access_token": "old-access",
            "refresh_token": "old-refresh",
            "token_expires_at": 1.0,
            "weekplan": True,
        }


class FakeTokenState:
    def as_entry_data(self) -> dict[str, Any]:
        return {
            "access_token": "new-access",
            "refresh_token": "new-refresh",
            "token_expires_at": 2.0,
        }


class InitTokenPersistenceTests(unittest.TestCase):
    def test_token_state_persist_schedules_partial_without_loop_kwargs(self) -> None:
        hass = FakeHass()
        entry = FakeEntry()

        integration_init._schedule_token_state_persist(hass, entry, FakeTokenState())

        self.assertEqual(1, len(hass.loop.callbacks))
        self.assertEqual(1, len(hass.config_entries.updates))
        updated_entry, data = hass.config_entries.updates[0]
        self.assertIs(entry, updated_entry)
        self.assertEqual("guardian@example.test", data["mitid_username"])
        self.assertEqual("new-access", data["access_token"])
        self.assertEqual("new-refresh", data["refresh_token"])
        self.assertEqual(2.0, data["token_expires_at"])
        self.assertTrue(data["weekplan"])


if __name__ == "__main__":
    unittest.main()
