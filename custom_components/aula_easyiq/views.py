"""Home Assistant HTTP views for EasyIQ MitID auth status."""
from __future__ import annotations

from html import escape
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
    requires_auth = False

    async def get(self, request: web.Request, flow_id: str) -> web.Response:
        """Return public auth status for the flow."""
        manager = get_auth_manager(request.app["hass"])
        session = manager.get_session(flow_id)
        if session is None:
            if "text/html" in request.headers.get("Accept", ""):
                return web.Response(
                    text=_render_auth_page(
                        "EasyIQ MitID Authentication",
                        "This authentication session was not found or has expired.",
                    ),
                    content_type="text/html",
                    status=404,
                )
            return web.json_response({"error": "unknown_auth_session"}, status=404)

        if "text/html" in request.headers.get("Accept", ""):
            return web.Response(
                text=_render_auth_page(
                    "EasyIQ MitID Authentication",
                    session.message or "Complete guardian MitID authentication.",
                    status=session.status,
                ),
                content_type="text/html",
            )
        return web.json_response(session.as_status())


class MitIDAuthCompleteView(HomeAssistantView):
    """Endpoint for completing a MitID auth session with tokens."""

    url = "/api/aula_easyiq/auth/{flow_id}/complete"
    name = "api:aula_easyiq:auth_complete"
    requires_auth = False

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


def _render_auth_page(title: str, message: str, *, status: str = "pending") -> str:
    """Render a small browser-friendly page for the external auth step."""
    safe_title = escape(title)
    safe_message = escape(message)
    safe_status = escape(status)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_title}</title>
  <style>
    body {{
      background: #111827;
      color: #f9fafb;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
    }}
    main {{
      box-sizing: border-box;
      max-width: 38rem;
      padding: 2rem;
      text-align: center;
    }}
    h1 {{ font-size: 1.5rem; margin: 0 0 1rem; }}
    p {{ color: #d1d5db; line-height: 1.5; margin: 0.75rem 0; }}
    .status {{
      display: inline-block;
      margin-top: 1rem;
      padding: 0.35rem 0.65rem;
      border: 1px solid #374151;
      border-radius: 999px;
      color: #93c5fd;
      font-size: 0.875rem;
      text-transform: uppercase;
    }}
  </style>
</head>
<body>
  <main>
    <h1>{safe_title}</h1>
    <p>{safe_message}</p>
    <p>Return to Home Assistant after the authorization step completes.</p>
    <span class="status">{safe_status}</span>
  </main>
</body>
</html>"""
