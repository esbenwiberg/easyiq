"""The EasyIQ integration."""
from __future__ import annotations

import asyncio
from functools import partial
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .const import (
    CONF_FIXTURE_BASE_URL,
    CONF_MITID_USERNAME,
    CONF_PASSWORD,
    CONF_REAUTH_REQUIRED,
    DOMAIN,
    STARTUP,
)
from .client import EasyIQAuthError, EasyIQClient
from .migration import migrate_legacy_password_entry_data
from .mitid_auth import AulaTokenRefresher, AulaTokenState, MitIDAuthError
from .sensor import EasyIQDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.CALENDAR,
]


def _schedule_token_state_persist(
    hass: HomeAssistant,
    entry: ConfigEntry,
    new_token_state: AulaTokenState,
) -> None:
    """Persist refreshed Aula token state back on the Home Assistant loop."""
    data = dict(entry.data)
    data.update(new_token_state.as_entry_data())
    hass.loop.call_soon_threadsafe(
        partial(hass.config_entries.async_update_entry, entry, data=data)
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up EasyIQ from a config entry."""
    integration = await async_get_integration(hass, DOMAIN)
    _LOGGER.info(STARTUP, integration.version)
    
    hass.data.setdefault(DOMAIN, {})

    try:
        from .views import async_register_auth_views

        await async_register_auth_views(hass)
    except Exception as err:  # pylint: disable=broad-except
        _LOGGER.debug("Could not register MitID auth views during setup: %s", err)

    fixture_base_url = entry.data.get(CONF_FIXTURE_BASE_URL)

    if fixture_base_url:
        mitid_username = entry.data.get(CONF_MITID_USERNAME, "fixture")
        token_state = None
    else:
        if entry.data.get(CONF_REAUTH_REQUIRED) or CONF_PASSWORD in entry.data:
            raise ConfigEntryAuthFailed("EasyIQ requires MitID reauthentication")

        mitid_username = entry.data.get(CONF_MITID_USERNAME)
        if not mitid_username:
            raise ConfigEntryAuthFailed("EasyIQ MitID username is missing")

        try:
            token_state = AulaTokenState.from_entry_data(entry.data)
        except MitIDAuthError as err:
            raise ConfigEntryAuthFailed("EasyIQ Aula token state is missing") from err

    runtime_data = hass.data[DOMAIN].setdefault(entry.entry_id, {})

    def _handle_token_update(new_token_state: AulaTokenState) -> None:
        runtime_data["token_state"] = new_token_state
        _schedule_token_state_persist(hass, entry, new_token_state)
    
    # Create the EasyIQ client
    client = EasyIQClient(
        mitid_username=mitid_username,
        token_state=token_state,
        token_refresher=AulaTokenRefresher(),
        on_token_update=_handle_token_update,
        fixture_base_url=fixture_base_url,
    )
    
    # Create the data update coordinator
    coordinator = EasyIQDataUpdateCoordinator(hass, client, entry)
    
    # Perform initial data fetch
    try:
        await coordinator.async_config_entry_first_refresh()
    except (EasyIQAuthError, MitIDAuthError) as err:
        _LOGGER.error("EasyIQ authentication failed during setup: %s", err)
        raise ConfigEntryAuthFailed from err
    except Exception as err:
        _LOGGER.error("Failed to perform initial data fetch: %s", err)
        raise ConfigEntryNotReady from err
    
    # Store coordinator and client in hass data
    hass_data = {
        "coordinator": coordinator,
        "client": client,
    }
    
    # Registers update listener to update config entry when options are updated.
    unsub_options_update_listener = entry.add_update_listener(options_update_listener)
    # Store a reference to the unsubscribe function to cleanup if an entry is unloaded.
    hass_data["unsub_options_update_listener"] = unsub_options_update_listener
    runtime_data.update(hass_data)

    # Forward the setup to the sensor, binary_sensor, and calendar platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate legacy credential entries to a MitID reauth-required state."""
    if entry.version >= 2:
        return True

    data = migrate_legacy_password_entry_data(dict(entry.data))

    hass.config_entries.async_update_entry(entry, data=data, version=2)
    _LOGGER.info("Migrated EasyIQ entry %s to MitID reauthentication", entry.entry_id)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    # Remove options_update_listener.
    hass.data[DOMAIN][entry.entry_id]["unsub_options_update_listener"]()

    # Remove config entry from domain.
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def options_update_listener(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)
