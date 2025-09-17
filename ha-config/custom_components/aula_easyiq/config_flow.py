"""Config flow for EasyIQ integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_SCHOOLSCHEDULE,
    CONF_WEEKPLAN,
    CONF_HOMEWORK,
    CONF_PRESENCE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

# Schema for user input
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_SCHOOLSCHEDULE, default=True): bool,
        vol.Optional(CONF_WEEKPLAN, default=True): bool,
        vol.Optional(CONF_HOMEWORK, default=True): bool,
        vol.Optional(CONF_PRESENCE, default=True): bool,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    # Basic validation - check that username and password are provided
    username = data.get(CONF_USERNAME)
    password = data.get(CONF_PASSWORD)
    
    if not username or not password:
        raise InvalidAuth("Username and password are required")
    
    # For production use, this could validate credentials against the EasyIQ API
    # Currently we rely on runtime authentication validation in the client
    
    # Return info that you want to store in the config entry.
    return {"title": f"EasyIQ ({username})"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for EasyIQ."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """EasyIQ config flow options handler."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        super().__init__()

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCHOOLSCHEDULE,
                        default=self._get_option(CONF_SCHOOLSCHEDULE, True),
                    ): bool,
                    vol.Optional(
                        CONF_WEEKPLAN,
                        default=self._get_option(CONF_WEEKPLAN, True),
                    ): bool,
                    vol.Optional(
                        CONF_HOMEWORK,
                        default=self._get_option(CONF_HOMEWORK, True),
                    ): bool,
                    vol.Optional(
                        CONF_PRESENCE,
                        default=self._get_option(CONF_PRESENCE, True),
                    ): bool,
                }
            ),
        )

    def _get_option(self, key: str, default: Any) -> Any:
        """Get option value from config entry."""
        return self.config_entry.options.get(key, default)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""