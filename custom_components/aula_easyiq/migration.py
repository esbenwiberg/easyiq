"""Pure config-entry migration helpers for EasyIQ."""
from __future__ import annotations

from typing import Any

try:
    from .const import (
        AUTH_METHOD_MITID,
        CONF_AUTH_METHOD,
        CONF_MITID_USERNAME,
        CONF_PASSWORD,
        CONF_REAUTH_REQUIRED,
        CONF_USERNAME,
    )
except ImportError:
    from const import (  # type: ignore[no-redef]
        AUTH_METHOD_MITID,
        CONF_AUTH_METHOD,
        CONF_MITID_USERNAME,
        CONF_PASSWORD,
        CONF_REAUTH_REQUIRED,
        CONF_USERNAME,
    )


def migrate_legacy_password_entry_data(data: dict[str, Any]) -> dict[str, Any]:
    """Return migrated config data that requires MitID reauthentication."""
    migrated = dict(data)
    legacy_username = migrated.pop(CONF_USERNAME, "")
    migrated.pop(CONF_PASSWORD, None)
    migrated[CONF_AUTH_METHOD] = AUTH_METHOD_MITID
    migrated[CONF_REAUTH_REQUIRED] = True

    if legacy_username and CONF_MITID_USERNAME not in migrated:
        migrated[CONF_MITID_USERNAME] = legacy_username

    return migrated
