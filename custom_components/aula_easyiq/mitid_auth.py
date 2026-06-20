"""Clean-room MitID/Aula token authentication boundary."""
from __future__ import annotations

import inspect
from dataclasses import dataclass, replace
import time
from typing import Any, Callable, Protocol
from uuid import uuid4

try:
    import requests
except ImportError:  # pragma: no cover - Home Assistant installs requirements.
    requests = None

try:
    from .const import (
        AUTH_METHOD_MITID,
        CONF_ACCESS_TOKEN,
        CONF_AUTH_METHOD,
        CONF_HOMEWORK,
        CONF_MITID_USERNAME,
        CONF_PRESENCE,
        CONF_REFRESH_TOKEN,
        CONF_SCHOOLSCHEDULE,
        CONF_TOKEN_EXPIRES_AT,
        CONF_WEEKPLAN,
    )
except ImportError:
    # For standalone script execution from custom_components/aula_easyiq.
    from const import (  # type: ignore[no-redef]
        AUTH_METHOD_MITID,
        CONF_ACCESS_TOKEN,
        CONF_AUTH_METHOD,
        CONF_HOMEWORK,
        CONF_MITID_USERNAME,
        CONF_PRESENCE,
        CONF_REFRESH_TOKEN,
        CONF_SCHOOLSCHEDULE,
        CONF_TOKEN_EXPIRES_AT,
        CONF_WEEKPLAN,
    )


class MitIDAuthError(Exception):
    """Raised when MitID or Aula token authentication fails."""


class MitIDAuthPending(MitIDAuthError):
    """Raised when an external MitID authentication session is not complete."""


class MitIDAuthRejected(MitIDAuthError):
    """Raised when token refresh or exchange is rejected."""


@dataclass(frozen=True)
class AulaTokenState:
    """Aula token state stored in config entries and runtime data."""

    access_token: str
    refresh_token: str
    expires_at: float

    @classmethod
    def from_auth_tokens(cls, tokens: dict[str, Any]) -> "AulaTokenState":
        """Create token state from an Aula authentication result."""
        access_token = tokens.get(CONF_ACCESS_TOKEN) or tokens.get("accessToken")
        refresh_token = tokens.get(CONF_REFRESH_TOKEN) or tokens.get("refreshToken")
        expires_at = (
            tokens.get(CONF_TOKEN_EXPIRES_AT)
            or tokens.get("expires_at")
            or tokens.get("expiresAt")
        )

        if expires_at is None:
            expires_in = tokens.get("expires_in", tokens.get("expiresIn", 3600))
            expires_at = time.time() + int(expires_in)

        if not access_token or not refresh_token:
            raise MitIDAuthRejected("Aula auth result did not include token state")

        return cls(
            access_token=str(access_token),
            refresh_token=str(refresh_token),
            expires_at=float(expires_at),
        )

    @classmethod
    def from_entry_data(cls, data: dict[str, Any]) -> "AulaTokenState":
        """Create token state from a Home Assistant config entry data mapping."""
        access_token = data.get(CONF_ACCESS_TOKEN)
        refresh_token = data.get(CONF_REFRESH_TOKEN)
        expires_at = data.get(CONF_TOKEN_EXPIRES_AT)

        if not access_token or not refresh_token or expires_at is None:
            raise MitIDAuthRejected("Missing Aula token state")

        return cls(
            access_token=str(access_token),
            refresh_token=str(refresh_token),
            expires_at=float(expires_at),
        )

    def as_entry_data(self) -> dict[str, Any]:
        """Return the token fields suitable for config entry data."""
        return {
            CONF_ACCESS_TOKEN: self.access_token,
            CONF_REFRESH_TOKEN: self.refresh_token,
            CONF_TOKEN_EXPIRES_AT: self.expires_at,
        }

    def is_expired(self, *, leeway_seconds: int = 60) -> bool:
        """Return true when the access token should be refreshed."""
        return self.expires_at <= time.time() + leeway_seconds


class TokenRefresher(Protocol):
    """Protocol for refreshing Aula access tokens."""

    def refresh(self, token_state: AulaTokenState) -> AulaTokenState:
        """Refresh token state."""


class AulaTokenRefresher:
    """Refresh Aula tokens through a small mockable HTTP boundary."""

    def __init__(
        self,
        refresh_url: str = "https://www.aula.dk/api/v22/?method=auth.refreshToken",
        session_factory: Callable[[], Any] | None = None,
    ) -> None:
        """Initialize the refresher."""
        self.refresh_url = refresh_url
        self._session_factory = session_factory

    def refresh(self, token_state: AulaTokenState) -> AulaTokenState:
        """Refresh an Aula access token using the refresh token."""
        if requests is None and self._session_factory is None:
            raise MitIDAuthRejected("requests is not available")

        session = self._session_factory() if self._session_factory else requests.Session()
        response = session.post(
            self.refresh_url,
            json={CONF_REFRESH_TOKEN: token_state.refresh_token},
            timeout=30,
            verify=True,
        )

        if response.status_code in (401, 403):
            raise MitIDAuthRejected("Aula refresh token was rejected")
        if response.status_code != 200:
            raise MitIDAuthError(f"Aula token refresh failed: HTTP {response.status_code}")

        payload = response.json()
        data = payload.get("data", payload)
        access_token = data.get(CONF_ACCESS_TOKEN) or data.get("accessToken")
        refresh_token = (
            data.get(CONF_REFRESH_TOKEN)
            or data.get("refreshToken")
            or token_state.refresh_token
        )
        expires_at = (
            data.get(CONF_TOKEN_EXPIRES_AT)
            or data.get("expiresAt")
            or time.time() + int(data.get("expires_in", data.get("expiresIn", 3600)))
        )

        if not access_token:
            raise MitIDAuthRejected("Aula refresh response did not include an access token")

        return AulaTokenState(
            access_token=str(access_token),
            refresh_token=str(refresh_token),
            expires_at=float(expires_at),
        )


@dataclass(frozen=True)
class MitIDAuthSession:
    """External MitID auth session tracked during a config flow."""

    flow_id: str
    username: str
    status: str
    external_url: str
    token_state: AulaTokenState | None = None
    message: str = ""
    ha_flow_id: str | None = None

    @property
    def complete(self) -> bool:
        """Return true when the session has produced Aula tokens."""
        return self.status == "complete" and self.token_state is not None

    def as_status(self) -> dict[str, Any]:
        """Return public status data for a local Home Assistant auth view."""
        return {
            "flow_id": self.flow_id,
            "username": self.username,
            "status": self.status,
            "message": self.message,
        }


class MitIDAuthManager:
    """In-memory manager for external MitID auth sessions."""

    def __init__(self, base_path: str = "/api/aula_easyiq/auth") -> None:
        """Initialize the session manager."""
        self.base_path = base_path.rstrip("/")
        self._sessions: dict[str, MitIDAuthSession] = {}
        self._clients: dict[str, Any] = {}

    def start_session(
        self,
        username: str,
        *,
        ha_flow_id: str | None = None,
    ) -> MitIDAuthSession:
        """Start a new external MitID auth session."""
        flow_id = uuid4().hex
        session = MitIDAuthSession(
            flow_id=flow_id,
            username=username,
            status="pending",
            external_url=f"{self.base_path}/{flow_id}",
            message="Complete guardian MitID authentication in the opened browser window.",
            ha_flow_id=ha_flow_id,
        )
        self._sessions[flow_id] = session
        return session

    def get_session(self, flow_id: str) -> MitIDAuthSession | None:
        """Return a tracked MitID auth session."""
        return self._sessions.get(flow_id)

    def attach_client(self, flow_id: str, client: Any) -> None:
        """Attach the live Aula/MitID client used by a session."""
        self._clients[flow_id] = client

    def update_session(
        self,
        flow_id: str,
        *,
        status: str | None = None,
        message: str | None = None,
    ) -> MitIDAuthSession:
        """Update public session status fields."""
        session = self._sessions.get(flow_id)
        if session is None:
            raise MitIDAuthRejected("Unknown MitID auth session")

        updated = replace(
            session,
            status=status or session.status,
            message=message if message is not None else session.message,
        )
        self._sessions[flow_id] = updated
        return updated

    def public_status(self, flow_id: str) -> dict[str, Any] | None:
        """Return public status plus transient QR/status data for a session."""
        session = self._sessions.get(flow_id)
        if session is None:
            return None

        status = session.as_status()
        if session.status in {"complete", "failed"}:
            return status

        client = self._clients.get(flow_id)
        if client is None:
            return status

        mitid_client = None
        if hasattr(client, "get_mitid_client"):
            mitid_client = client.get_mitid_client()

        live_message = getattr(mitid_client, "status_message", None) or getattr(
            client, "status_message", None
        )
        if live_message:
            status["message"] = str(live_message)

        if hasattr(client, "get_qr_codes_svg"):
            qr_svgs = client.get_qr_codes_svg()
            if qr_svgs:
                status["qr_svg"] = qr_svgs[int(time.time()) % len(qr_svgs)]

        return status

    def complete_session(
        self,
        flow_id: str,
        token_state: AulaTokenState,
        *,
        username: str | None = None,
    ) -> MitIDAuthSession:
        """Mark a MitID auth session complete with Aula token state."""
        session = self._sessions.get(flow_id)
        if session is None:
            raise MitIDAuthRejected("Unknown MitID auth session")

        updated = replace(
            session,
            username=username or session.username,
            status="complete",
            token_state=token_state,
            message="MitID authentication completed.",
        )
        self._sessions[flow_id] = updated
        return updated

    def fail_session(self, flow_id: str, message: str) -> MitIDAuthSession:
        """Mark a MitID auth session failed."""
        session = self._sessions.get(flow_id)
        if session is None:
            raise MitIDAuthRejected("Unknown MitID auth session")

        updated = replace(session, status="failed", message=message)
        self._sessions[flow_id] = updated
        return updated


def _default_aula_login_client(*, mitid_username: str) -> Any:
    """Build the live Aula login client lazily so unit tests can use fakes."""
    try:
        from .aula_login_client.client import AulaLoginClient
    except ImportError:
        from aula_login_client.client import AulaLoginClient  # type: ignore[no-redef]

    return AulaLoginClient(
        mitid_username=mitid_username,
        auth_method="APP",
        verbose=False,
        debug=False,
    )


async def _maybe_await(value: Any) -> Any:
    """Await value when it is awaitable; otherwise return it unchanged."""
    if inspect.isawaitable(value):
        return await value
    return value


async def run_live_mitid_auth(
    hass: Any,
    manager: MitIDAuthManager,
    flow_id: str,
    *,
    client_factory: Callable[..., Any] | None = None,
) -> None:
    """Run the live Aula/MitID authentication flow for a pending session."""
    session = manager.get_session(flow_id)
    if session is None:
        return

    try:
        factory = client_factory or _default_aula_login_client
        client = factory(mitid_username=session.username)
        manager.attach_client(flow_id, client)
        manager.update_session(
            flow_id,
            status="running",
            message="Starting Aula MitID authentication...",
        )

        auth_result = await _maybe_await(
            hass.async_add_executor_job(client.authenticate)
        )
        if not auth_result.get("success"):
            raise MitIDAuthRejected(auth_result.get("error", "MitID authentication failed"))

        token_state = AulaTokenState.from_auth_tokens(auth_result.get("tokens", {}))
        manager.complete_session(flow_id, token_state, username=session.username)
    except Exception as err:  # pylint: disable=broad-except
        manager.fail_session(flow_id, str(err))

    latest = manager.get_session(flow_id)
    if latest and latest.ha_flow_id:
        flow_mgr = hass.config_entries.flow
        if hasattr(flow_mgr, "async_configure"):
            await _maybe_await(flow_mgr.async_configure(latest.ha_flow_id))


def start_live_mitid_auth(
    hass: Any,
    flow_id: str,
    *,
    auth_manager: MitIDAuthManager | None = None,
    client_factory: Callable[..., Any] | None = None,
) -> Any:
    """Start the live MitID auth task in Home Assistant's event loop."""
    manager = auth_manager or get_auth_manager(hass)
    coroutine = run_live_mitid_auth(
        hass,
        manager,
        flow_id,
        client_factory=client_factory,
    )
    return hass.async_create_task(coroutine)


def get_auth_manager(hass: Any) -> MitIDAuthManager:
    """Return the integration auth manager stored on Home Assistant data."""
    try:
        from .const import DOMAIN
    except ImportError:
        from const import DOMAIN  # type: ignore[no-redef]

    hass.data.setdefault(DOMAIN, {})
    manager = hass.data[DOMAIN].get("mitid_auth_manager")
    if manager is None:
        manager = MitIDAuthManager()
    hass.data[DOMAIN]["mitid_auth_manager"] = manager
    return manager


def build_config_entry_data(
    user_input: dict[str, Any],
    session: MitIDAuthSession,
) -> dict[str, Any]:
    """Build Home Assistant config entry data from a completed MitID session."""
    if not session.complete or session.token_state is None:
        raise MitIDAuthPending("MitID authentication is not complete")

    return {
        CONF_MITID_USERNAME: session.username,
        CONF_AUTH_METHOD: AUTH_METHOD_MITID,
        **session.token_state.as_entry_data(),
        CONF_SCHOOLSCHEDULE: user_input.get(CONF_SCHOOLSCHEDULE, True),
        CONF_WEEKPLAN: user_input.get(CONF_WEEKPLAN, True),
        CONF_HOMEWORK: user_input.get(CONF_HOMEWORK, True),
        CONF_PRESENCE: user_input.get(CONF_PRESENCE, True),
    }
