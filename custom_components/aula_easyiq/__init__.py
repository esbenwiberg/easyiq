"""The EasyIQ integration."""
from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration
from homeassistant.exceptions import ConfigEntryNotReady, ConfigEntryAuthFailed

from .const import (
    AUTH_METHOD_APP,
    CONF_ACCESS_TOKEN,
    CONF_AUTH_METHOD,
    CONF_MITID_IDENTITY,
    CONF_MITID_PASSWORD,
    CONF_MITID_TOKEN,
    CONF_MITID_USERNAME,
    CONF_REFRESH_TOKEN,
    CONF_TOKEN_EXPIRES_AT,
    DOMAIN,
    STARTUP,
)
from .client import EasyIQClient
from .sensor import EasyIQDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.CALENDAR,
]


def _stored_tokens_from_entry(entry: ConfigEntry) -> dict | None:
    """Build the tokens dict the client expects from a config entry."""
    if CONF_ACCESS_TOKEN not in entry.data:
        return None
    return {
        "access_token": entry.data[CONF_ACCESS_TOKEN],
        "refresh_token": entry.data.get(CONF_REFRESH_TOKEN, ""),
        "expires_at": entry.data.get(CONF_TOKEN_EXPIRES_AT, 0),
        "token_type": "Bearer",
    }


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up EasyIQ from a config entry."""
    integration = await async_get_integration(hass, DOMAIN)
    _LOGGER.info(STARTUP, integration.version)

    hass.data.setdefault(DOMAIN, {})

    mitid_username = entry.data.get(CONF_MITID_USERNAME)
    if not mitid_username:
        # Old config entries from the unilogin era have no MitID username and
        # cannot work anymore. Trigger a reauth so the user can re-enter MitID.
        _LOGGER.warning(
            "Config entry has no MitID username (legacy unilogin entry?); "
            "triggering reauth"
        )
        raise ConfigEntryAuthFailed(
            "Aula now requires MitID; please re-authenticate the EasyIQ integration."
        )

    auth_method = entry.data.get(CONF_AUTH_METHOD, AUTH_METHOD_APP)
    mitid_password = entry.data.get(CONF_MITID_PASSWORD)
    mitid_token = entry.data.get(CONF_MITID_TOKEN)
    mitid_identity = entry.data.get(CONF_MITID_IDENTITY, 1)
    stored_tokens = _stored_tokens_from_entry(entry)

    def token_update_callback(tokens: dict) -> None:
        """Persist refreshed tokens back into the config entry (thread-safe)."""
        try:
            asyncio.run_coroutine_threadsafe(
                async_update_tokens(hass, entry, tokens),
                hass.loop,
            ).result(timeout=5)
        except Exception as err:  # pragma: no cover - best-effort persistence
            _LOGGER.warning("Failed to persist refreshed tokens: %s", err)

    client = EasyIQClient(
        mitid_username=mitid_username,
        auth_method=auth_method,
        mitid_password=mitid_password,
        mitid_token=mitid_token,
        mitid_identity=mitid_identity,
        stored_tokens=stored_tokens,
        token_update_callback=token_update_callback,
    )

    try:
        login_ok = await hass.async_add_executor_job(client.login)
    except Exception as err:
        _LOGGER.error("MitID login failed: %s", err)
        raise ConfigEntryAuthFailed(
            "MitID re-authentication required. Please reconfigure EasyIQ."
        ) from err
    if not login_ok:
        raise ConfigEntryAuthFailed(
            "MitID re-authentication required. Please reconfigure EasyIQ."
        )

    coordinator = EasyIQDataUpdateCoordinator(hass, client, entry)

    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        _LOGGER.error("Failed to perform initial data fetch: %s", err)
        raise ConfigEntryNotReady from err

    hass_data = {
        "coordinator": coordinator,
        "client": client,
    }

    # Registers update listener to update config entry when options are updated.
    unsub_options_update_listener = entry.add_update_listener(options_update_listener)
    hass_data["unsub_options_update_listener"] = unsub_options_update_listener
    hass.data[DOMAIN][entry.entry_id] = hass_data

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_update_tokens(
    hass: HomeAssistant, entry: ConfigEntry, tokens: dict
) -> None:
    """Persist refreshed OAuth tokens into the config entry without reloading."""
    new_data = dict(entry.data)
    new_data[CONF_ACCESS_TOKEN] = tokens.get("access_token", "")
    new_data[CONF_REFRESH_TOKEN] = tokens.get("refresh_token", "")
    new_data[CONF_TOKEN_EXPIRES_AT] = tokens.get("expires_at", 0)
    hass.config_entries.async_update_entry(entry, data=new_data)
    _LOGGER.debug("Refreshed Aula tokens persisted to config entry")


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
