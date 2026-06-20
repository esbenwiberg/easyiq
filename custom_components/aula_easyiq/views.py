"""Home Assistant HTTP views for EasyIQ MitID auth status."""
from __future__ import annotations

from typing import Any

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .const import (
    CONF_ACCESS_TOKEN,
    CONF_REFRESH_TOKEN,
    CONF_TOKEN_EXPIRES_AT,
    DOMAIN,
)
from .mitid_auth import AulaTokenState, MitIDAuthRejected, get_auth_manager


VIEW_REGISTERED = "mitid_auth_views_registered"


async def async_register_auth_views(hass: HomeAssistant) -> None:
    """Register MitID auth status views once."""
    hass.data.setdefault(DOMAIN, {})
    if hass.data[DOMAIN].get(VIEW_REGISTERED):
        return

    hass.http.register_view(MitIDAuthStatusView())
    hass.http.register_view(MitIDAuthCompleteView())
    hass.data[DOMAIN][VIEW_REGISTERED] = True


class MitIDAuthStatusView(HomeAssistantView):
    """Expose status for an EasyIQ MitID auth session."""

    url = "/api/aula_easyiq/auth/{flow_id}"
    name = "api:aula_easyiq:auth_status"
    requires_auth = True

    async def get(self, request: web.Request, flow_id: str) -> web.Response:
        """Return public auth status for the flow."""
        manager = get_auth_manager(request.app["hass"])
        session = manager.get_session(flow_id)
        if session is None:
            return web.json_response({"error": "unknown_auth_session"}, status=404)

        return web.json_response(session.as_status())


class MitIDAuthCompleteView(HomeAssistantView):
    """Authenticated endpoint for completing a MitID auth session with tokens."""

    url = "/api/aula_easyiq/auth/{flow_id}/complete"
    name = "api:aula_easyiq:auth_complete"
    requires_auth = True

    async def post(self, request: web.Request, flow_id: str) -> web.Response:
        """Complete auth with token state produced by the MitID boundary."""
        try:
            payload: dict[str, Any] = await request.json()
            token_state = AulaTokenState(
                access_token=str(payload[CONF_ACCESS_TOKEN]),
                refresh_token=str(payload[CONF_REFRESH_TOKEN]),
                expires_at=float(payload[CONF_TOKEN_EXPIRES_AT]),
            )
            session = get_auth_manager(request.app["hass"]).complete_session(
                flow_id,
                token_state,
                username=payload.get("mitid_username"),
            )
        except (KeyError, TypeError, ValueError):
            return web.json_response({"error": "invalid_token_payload"}, status=400)
        except MitIDAuthRejected:
            return web.json_response({"error": "unknown_auth_session"}, status=404)

        flow_mgr = request.app["hass"].config_entries.flow
        if session.ha_flow_id and hasattr(flow_mgr, "async_configure"):
            await flow_mgr.async_configure(session.ha_flow_id)

        return web.json_response(session.as_status())
