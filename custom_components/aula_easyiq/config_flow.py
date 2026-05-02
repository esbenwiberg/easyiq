"""Config flow for the EasyIQ integration (MitID)."""
from __future__ import annotations

import asyncio
import concurrent.futures
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .aula_login_client.client import AulaLoginClient
from .const import (
    AUTH_METHOD_APP,
    AUTH_METHOD_TOKEN,
    CONF_ACCESS_TOKEN,
    CONF_AUTH_METHOD,
    CONF_HOMEWORK,
    CONF_HOMEWORK_DAYS,
    CONF_HOMEWORK_INTERVAL,
    CONF_MESSAGES_INTERVAL,
    CONF_MITID_IDENTITY,
    CONF_MITID_PASSWORD,
    CONF_MITID_TOKEN,
    CONF_MITID_USE_TOKEN,
    CONF_MITID_USERNAME,
    CONF_PRESENCE,
    CONF_PRESENCE_INTERVAL,
    CONF_REFRESH_TOKEN,
    CONF_SCHOOLSCHEDULE,
    CONF_TOKEN_EXPIRES_AT,
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
)
from .views import (
    EasyIQAuthSelectIdentityView,
    EasyIQAuthStatusView,
    EasyIQAuthView,
)

_LOGGER = logging.getLogger(__name__)


USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MITID_USERNAME): str,
        vol.Optional(CONF_MITID_USE_TOKEN, default=False): bool,
        vol.Optional(CONF_MITID_IDENTITY, default=1): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=10)
        ),
        vol.Optional(CONF_SCHOOLSCHEDULE, default=True): bool,
        vol.Optional(CONF_WEEKPLAN, default=True): bool,
        vol.Optional(CONF_HOMEWORK, default=True): bool,
        vol.Optional(CONF_PRESENCE, default=True): bool,
    }
)


TOKEN_CREDENTIALS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MITID_PASSWORD): str,
        vol.Required(CONF_MITID_TOKEN): str,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the EasyIQ MitID config flow."""

    VERSION = 2

    def __init__(self) -> None:
        self._mitid_username: str | None = None
        self._auth_method: str = AUTH_METHOD_APP
        self._mitid_password: str | None = None
        self._mitid_token: str | None = None
        self._mitid_identity: int = 1
        self._feature_flags: dict[str, Any] = {}
        self._auth_client: AulaLoginClient | None = None
        self._tokens: dict | None = None
        self._reauth_entry: config_entries.ConfigEntry | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Collect MitID username + feature flags."""
        if user_input is not None:
            self._mitid_username = user_input[CONF_MITID_USERNAME]
            use_token = user_input.get(CONF_MITID_USE_TOKEN, False)
            self._auth_method = AUTH_METHOD_TOKEN if use_token else AUTH_METHOD_APP
            self._mitid_identity = user_input.get(CONF_MITID_IDENTITY, 1)
            self._feature_flags = {
                CONF_SCHOOLSCHEDULE: user_input.get(CONF_SCHOOLSCHEDULE, True),
                CONF_WEEKPLAN: user_input.get(CONF_WEEKPLAN, True),
                CONF_HOMEWORK: user_input.get(CONF_HOMEWORK, True),
                CONF_PRESENCE: user_input.get(CONF_PRESENCE, True),
                CONF_MITID_USE_TOKEN: use_token,
                CONF_MITID_IDENTITY: self._mitid_identity,
            }

            if use_token:
                return await self.async_step_token_credentials()
            return await self.async_step_authenticate()

        return self.async_show_form(step_id="user", data_schema=USER_SCHEMA)

    async def async_step_token_credentials(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Collect MitID password + 6-digit code from a code reader (TOKEN method)."""
        if user_input is not None:
            self._mitid_password = user_input[CONF_MITID_PASSWORD]
            self._mitid_token = user_input[CONF_MITID_TOKEN]
            return await self.async_step_authenticate()

        return self.async_show_form(
            step_id="token_credentials", data_schema=TOKEN_CREDENTIALS_SCHEMA
        )

    async def async_step_authenticate(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Run the actual MitID OAuth flow, surfacing QR codes via a web view."""
        session_data = None
        if (
            DOMAIN in self.hass.data
            and "auth_sessions" in self.hass.data[DOMAIN]
            and self.flow_id in self.hass.data[DOMAIN]["auth_sessions"]
        ):
            session_data = self.hass.data[DOMAIN]["auth_sessions"][self.flow_id]

        # Start (or restart on retry) when we have no session yet, or the previous
        # attempt errored and the user clicked submit on the error step.
        should_start = session_data is None or (
            user_input is not None and session_data.get("error")
        )

        if should_start:
            self.hass.data.setdefault(DOMAIN, {})
            self.hass.data[DOMAIN].setdefault("auth_sessions", {})

            if not self._auth_client:
                # Register HTTP views once per HA process; re-registering raises.
                if not self.hass.data[DOMAIN].get("views_registered"):
                    self.hass.http.register_view(EasyIQAuthView(self.hass))
                    self.hass.http.register_view(EasyIQAuthStatusView(self.hass))
                    self.hass.http.register_view(
                        EasyIQAuthSelectIdentityView(self.hass)
                    )
                    self.hass.data[DOMAIN]["views_registered"] = True

            self._auth_client = AulaLoginClient(
                mitid_username=self._mitid_username,
                mitid_password=self._mitid_password,
                mitid_token=self._mitid_token,
                auth_method=self._auth_method,
                verbose=False,
                debug=False,
            )

            session_data = {
                "client": self._auth_client,
                "status_message": "Open your MitID app now...",
                "completed": False,
                "error": None,
                "identity_future": None,
                "available_identities": None,
            }
            self.hass.data[DOMAIN]["auth_sessions"][self.flow_id] = session_data

            chosen_identity = self._mitid_identity

            def identity_selector(identity_names):
                """Block until the web view returns a choice."""
                # If the configured 1-based index is in range, use it directly.
                if 1 <= chosen_identity <= len(identity_names):
                    return str(chosen_identity)

                session_data["available_identities"] = identity_names
                session_data["status_message"] = "Please select an identity"
                future: concurrent.futures.Future = concurrent.futures.Future()
                session_data["identity_future"] = future
                try:
                    return future.result(timeout=300)
                except Exception as err:
                    _LOGGER.error("Identity selection timed out: %s", err)
                    raise

            self._auth_client.identity_selector = identity_selector

            # Run authentication in the background; advance the flow when it finishes.
            self.hass.async_create_task(self._authenticate_async(session_data))

            return self.async_external_step(
                step_id="authenticate",
                url=f"/api/aula_easyiq/auth/{self.flow_id}",
            )

        if session_data.get("completed"):
            self._tokens = session_data.get("tokens")
            if not self._tokens:
                _LOGGER.error("Authentication completed without tokens")
                return self.async_external_step_done(next_step_id="reauth_error")
            self.hass.async_create_task(self._delayed_cleanup(self.flow_id))
            return self.async_external_step_done(next_step_id="complete")

        if session_data.get("error"):
            return self.async_external_step_done(next_step_id="reauth_error")

        return self.async_external_step(
            step_id="authenticate",
            url=f"/api/aula_easyiq/auth/{self.flow_id}",
        )

    async def async_step_complete(self, user_input=None) -> FlowResult:
        """Persist tokens + create or update the config entry."""
        if not self._tokens:
            return self.async_abort(reason="auth_failed")

        data: dict[str, Any] = {
            CONF_MITID_USERNAME: self._mitid_username,
            CONF_AUTH_METHOD: self._auth_method,
            CONF_ACCESS_TOKEN: self._tokens.get("access_token"),
            CONF_REFRESH_TOKEN: self._tokens.get("refresh_token", ""),
            CONF_TOKEN_EXPIRES_AT: self._tokens.get("expires_at", 0),
            **self._feature_flags,
        }

        if self._reauth_entry:
            self.hass.config_entries.async_update_entry(self._reauth_entry, data=data)
            await self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
            return self.async_abort(reason="reauth_successful")

        await self.async_set_unique_id(self._mitid_username)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=f"EasyIQ ({self._mitid_username})", data=data
        )

    async def _authenticate_async(self, session_data: dict) -> None:
        """Run AulaLoginClient.authenticate() in an executor + bookkeep status."""
        try:
            monitor_task = self.hass.async_create_task(
                self._monitor_client_status(session_data)
            )
            try:
                result = await self.hass.async_add_executor_job(
                    self._auth_client.authenticate
                )
            finally:
                monitor_task.cancel()

            if result.get("success"):
                session_data["tokens"] = result.get("tokens")
                session_data["completed"] = True
                session_data["status_message"] = "Authentication successful!"
            else:
                session_data["error"] = result.get("error", "Unknown error")
        except Exception as err:
            _LOGGER.error("MitID authentication error: %s", err)
            session_data["error"] = str(err)

        # Advance the flow regardless of outcome.
        self.hass.async_create_task(
            self.hass.config_entries.flow.async_configure(flow_id=self.flow_id)
        )

    async def _monitor_client_status(self, session_data: dict) -> None:
        """Mirror AulaLoginClient.status_message into the session for the web view."""
        client = session_data["client"]
        while True:
            try:
                mitid_client = client.get_mitid_client()
                if mitid_client and hasattr(mitid_client, "status_message"):
                    if not session_data.get("available_identities"):
                        session_data["status_message"] = mitid_client.status_message
            except Exception:
                pass
            await asyncio.sleep(1)

    async def _delayed_cleanup(self, flow_id: str) -> None:
        """Clean the auth session a minute after success."""
        await asyncio.sleep(60)
        sessions = self.hass.data.get(DOMAIN, {}).get("auth_sessions", {})
        sessions.pop(flow_id, None)

    async def async_step_reauth_error(self, user_input=None) -> FlowResult:
        """Show error and let the user retry."""
        if user_input is not None:
            return await self.async_step_authenticate(user_input)
        return self.async_show_form(
            step_id="reauth_error",
            errors={"base": "auth_failed"},
        )

    async def async_step_reauth(self, entry_data) -> FlowResult:
        """Triggered by ConfigEntryAuthFailed during setup."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        if self._reauth_entry:
            self._mitid_username = self._reauth_entry.data.get(CONF_MITID_USERNAME)
            self._auth_method = self._reauth_entry.data.get(
                CONF_AUTH_METHOD, AUTH_METHOD_APP
            )
            self._mitid_identity = self._reauth_entry.data.get(
                CONF_MITID_IDENTITY, 1
            )
            self._feature_flags = {
                CONF_SCHOOLSCHEDULE: self._reauth_entry.data.get(
                    CONF_SCHOOLSCHEDULE, True
                ),
                CONF_WEEKPLAN: self._reauth_entry.data.get(CONF_WEEKPLAN, True),
                CONF_HOMEWORK: self._reauth_entry.data.get(CONF_HOMEWORK, True),
                CONF_PRESENCE: self._reauth_entry.data.get(CONF_PRESENCE, True),
                CONF_MITID_USE_TOKEN: self._reauth_entry.data.get(
                    CONF_MITID_USE_TOKEN, False
                ),
                CONF_MITID_IDENTITY: self._mitid_identity,
            }
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None) -> FlowResult:
        """Confirm reauth and start authentication."""
        if user_input is not None:
            sessions = self.hass.data.get(DOMAIN, {}).get("auth_sessions", {})
            sessions.pop(self.flow_id, None)
            if self._auth_method == AUTH_METHOD_TOKEN:
                return await self.async_step_token_credentials()
            return await self.async_step_authenticate()

        return self.async_show_form(
            step_id="reauth_confirm",
            description_placeholders={"username": self._mitid_username or ""},
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """EasyIQ options handler (intervals + days forward)."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        super().__init__()

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
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
        return self.config_entry.options.get(key, default)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
