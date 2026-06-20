"""Config flow for EasyIQ integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import (
    CONF_ACCESS_TOKEN,
    CONF_HOMEWORK,
    CONF_HOMEWORK_DAYS,
    CONF_HOMEWORK_INTERVAL,
    CONF_MITID_USERNAME,
    CONF_PASSWORD,
    CONF_PRESENCE,
    CONF_PRESENCE_INTERVAL,
    CONF_REAUTH_REQUIRED,
    CONF_REFRESH_TOKEN,
    CONF_SCHOOLSCHEDULE,
    CONF_TOKEN_EXPIRES_AT,
    CONF_USERNAME,
    CONF_WEEKPLAN,
    CONF_WEEKPLAN_DAYS,
    CONF_WEEKPLAN_INTERVAL,
    DEFAULT_HOMEWORK_DAYS,
    DEFAULT_HOMEWORK_INTERVAL,
    DEFAULT_MESSAGES_INTERVAL,
    DEFAULT_PRESENCE_INTERVAL,
    DEFAULT_WEEKPLAN_DAYS,
    DEFAULT_WEEKPLAN_INTERVAL,
    DOMAIN,
    CONF_MESSAGES_INTERVAL,
)
from .mitid_auth import (
    AulaTokenState,
    MitIDAuthRejected,
    MitIDAuthSession,
    build_config_entry_data,
    get_auth_manager,
)

_LOGGER = logging.getLogger(__name__)


STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MITID_USERNAME): str,
        vol.Optional(CONF_SCHOOLSCHEDULE, default=True): bool,
        vol.Optional(CONF_WEEKPLAN, default=True): bool,
        vol.Optional(CONF_HOMEWORK, default=True): bool,
        vol.Optional(CONF_PRESENCE, default=True): bool,
    }
)


def _feature_data(data: dict[str, Any]) -> dict[str, Any]:
    """Return feature toggles from config flow input."""
    return {
        CONF_SCHOOLSCHEDULE: data.get(CONF_SCHOOLSCHEDULE, True),
        CONF_WEEKPLAN: data.get(CONF_WEEKPLAN, True),
        CONF_HOMEWORK: data.get(CONF_HOMEWORK, True),
        CONF_PRESENCE: data.get(CONF_PRESENCE, True),
    }


def entry_data_from_auth(
    user_input: dict[str, Any],
    session: MitIDAuthSession,
) -> dict[str, Any]:
    """Build config entry data from user input and a completed MitID session."""
    return build_config_entry_data(user_input, session)


async def validate_input(
    hass: HomeAssistant,
    data: dict[str, Any],
    *,
    auth_manager: Any | None = None,
    ha_flow_id: str | None = None,
) -> dict[str, Any]:
    """Validate config flow input and return title/session metadata."""
    username = data.get(CONF_MITID_USERNAME)
    if not username:
        raise InvalidAuth("MitID username is required")

    manager = auth_manager or get_auth_manager(hass)

    if {
        CONF_ACCESS_TOKEN,
        CONF_REFRESH_TOKEN,
        CONF_TOKEN_EXPIRES_AT,
    }.issubset(data):
        token_state = AulaTokenState.from_entry_data(data)
        session = manager.start_session(username, ha_flow_id=ha_flow_id)
        session = manager.complete_session(session.flow_id, token_state, username=username)
    else:
        session = manager.start_session(username, ha_flow_id=ha_flow_id)

    return {
        "title": f"EasyIQ ({username})",
        "session": session,
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for EasyIQ."""

    VERSION = 2

    def __init__(self) -> None:
        """Initialize flow state."""
        self._pending_user_input: dict[str, Any] = {}
        self._auth_session_id: str | None = None
        self._reauth_entry: ConfigEntry | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial MitID setup step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors: dict[str, str] = {}

        try:
            await self._async_register_auth_views()
            info = await validate_input(
                self.hass,
                user_input,
                ha_flow_id=getattr(self, "flow_id", None),
            )
            session = info["session"]
        except MitIDAuthRejected:
            errors["base"] = "invalid_auth"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            self._pending_user_input = user_input
            self._auth_session_id = session.flow_id

            if session.complete:
                return await self._create_entry_from_session(session, info["title"])

            return self.async_external_step(
                step_id="mitid",
                url=session.external_url,
            )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def _async_register_auth_views(self) -> None:
        """Register local MitID auth views for the external config-flow step."""
        from .views import async_register_auth_views

        await async_register_auth_views(self.hass)

    async def async_step_mitid(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Complete the external MitID auth step."""
        if not self._auth_session_id:
            return self.async_abort(reason="missing_auth_session")

        session = get_auth_manager(self.hass).get_session(self._auth_session_id)
        if session is None:
            return self.async_abort(reason="missing_auth_session")

        if session.status == "failed":
            return self.async_show_form(
                step_id="user",
                data_schema=STEP_USER_DATA_SCHEMA,
                errors={"base": "invalid_auth"},
            )

        if not session.complete:
            return self.async_external_step(
                step_id="mitid",
                url=session.external_url,
            )

        return await self._create_entry_from_session(
            session, f"EasyIQ ({session.username})"
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> FlowResult:
        """Handle reauthentication requests."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        defaults = {
            CONF_MITID_USERNAME: entry_data.get(
                CONF_MITID_USERNAME, entry_data.get(CONF_USERNAME, "")
            ),
            **_feature_data(entry_data),
        }
        return await self.async_step_user(defaults)

    async def _create_entry_from_session(
        self,
        session: MitIDAuthSession,
        title: str,
    ) -> FlowResult:
        """Create or update a config entry from completed MitID auth."""
        entry_data = entry_data_from_auth(self._pending_user_input, session)

        if self._reauth_entry is not None:
            existing = dict(self._reauth_entry.data)
            existing.update(entry_data)
            existing.pop(CONF_PASSWORD, None)
            existing.pop(CONF_USERNAME, None)
            existing.pop(CONF_REAUTH_REQUIRED, None)
            self.hass.config_entries.async_update_entry(
                self._reauth_entry,
                data=existing,
                version=self.VERSION,
                title=title,
            )
            return self.async_abort(reason="reauth_successful")

        return self.async_create_entry(title=title, data=entry_data)

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
        self.config_entry = config_entry

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
                    vol.Optional(
                        CONF_WEEKPLAN_INTERVAL,
                        default=self._get_option(
                            CONF_WEEKPLAN_INTERVAL, DEFAULT_WEEKPLAN_INTERVAL
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=60, max=3600)),
                    vol.Optional(
                        CONF_HOMEWORK_INTERVAL,
                        default=self._get_option(
                            CONF_HOMEWORK_INTERVAL, DEFAULT_HOMEWORK_INTERVAL
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=60, max=3600)),
                    vol.Optional(
                        CONF_PRESENCE_INTERVAL,
                        default=self._get_option(
                            CONF_PRESENCE_INTERVAL, DEFAULT_PRESENCE_INTERVAL
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=60, max=3600)),
                    vol.Optional(
                        CONF_MESSAGES_INTERVAL,
                        default=self._get_option(
                            CONF_MESSAGES_INTERVAL, DEFAULT_MESSAGES_INTERVAL
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=60, max=3600)),
                    vol.Optional(
                        CONF_WEEKPLAN_DAYS,
                        default=self._get_option(
                            CONF_WEEKPLAN_DAYS, DEFAULT_WEEKPLAN_DAYS
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=14)),
                    vol.Optional(
                        CONF_HOMEWORK_DAYS,
                        default=self._get_option(
                            CONF_HOMEWORK_DAYS, DEFAULT_HOMEWORK_DAYS
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=14)),
                }
            ),
        )

    def _get_option(self, key: str, default: Any) -> Any:
        """Get option value from config entry."""
        return self.config_entry.options.get(key, self.config_entry.data.get(key, default))


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate invalid auth input."""
