# Research: Add MitID Auth

## Task

Old Aula/Unilogin username/password auth is no longer supported. The EasyIQ Home Assistant integration needs MitID-based authentication done in a clean, MIT-compatible way.

## Current Auth Entry Point

`custom_components/aula_easyiq/config_flow.py` defines a version 1 config flow. The setup schema currently requires `CONF_USERNAME` and `CONF_PASSWORD`, and `validate_input` only checks that those fields are present. The created config entry title is derived from the username.

`custom_components/aula_easyiq/strings.json` and `custom_components/aula_easyiq/translations/en.json` both label the setup fields as "Unilogin username" and "Unilogin password" and describe the setup as entering Unilogin credentials.

## Current Startup Path

`custom_components/aula_easyiq/__init__.py` constructs `EasyIQClient` from `entry.data["username"]` and `entry.data["password"]`. There is no token extraction, reauth handling, migration function, or registered Home Assistant HTTP view for an external authentication flow.

The coordinator is then created and `async_config_entry_first_refresh()` is called. Initial data refresh therefore depends on the current client being able to authenticate synchronously with the old credentials.

## Current Client Auth and Data Flow

`custom_components/aula_easyiq/client.py` initializes `EasyIQClient(username, password)` and keeps both a synchronous `requests.Session` and an unused-ish async `aiohttp.ClientSession`.

`login()` currently:

- opens `https://login.aula.dk/auth/login.php` with `type=unilogin`;
- posts `selectedIdp=uni_idp` to the broker;
- scrapes and posts form fields with `username`, `password`, and `selected-aktoer=KONTAKT`;
- treats redirect to `https://www.aula.dk:443/portal/` as success;
- discovers the Aula API version;
- calls `profiles.getProfilesByLogin`;
- calls `profiles.getProfileContext&portalrole=guardian`;
- populates `_profiles`, `_institution_profiles`, `_children_data`, `_childuserids`, `_childids`, `_childnames`, and `children`;
- sets `_authenticated = True`.

Downstream methods depend on those populated fields:

- `get_token()` calls `aulaToken.getAulaToken&widgetId=...` through the session and returns `Bearer <widget token>`.
- `_sync_get_calendar_events()` calls EasyIQ `https://skoleportal.easyiqcloud.dk/Calendar/CalendarGetWeekplanEvents` using the widget bearer token in `authorization`.
- `get_presence()` calls Aula `presence.getDailyOverview`.
- `_sync_get_messages()` calls Aula messaging endpoints.
- `update_data_selective()` starts each cycle with `await self.authenticate()`, then updates children, calendar-derived weekplan/homework data, presence, and messages.

The EasyIQ calendar/homework API shape is separate from Aula login. The expected auth-sensitive boundary is Aula profile/widget-token/messaging/presence calls, not the EasyIQ `CalendarGetWeekplanEvents` endpoint itself.

## Existing Validation and Tests

There is no `tests/` directory.

`scripts/validate_ha_integration.py` is broad static validation. It checks basic manifest fields, required integration files, selected strings in source files, and JSON validity for translations. It does not validate auth behavior.

`scripts/test_client.py` is a manual live-client script. It still reads `EASYIQ_USERNAME` and `EASYIQ_PASSWORD`, constructs `EasyIQClient(username, password)`, and calls `client.login()`.

`scripts/dev_setup.py` generates `.env.template`, dev scripts, a test script, and development requirements that assume username/password auth.

## Docs State

`README.md` still tells end users to enter Aula credentials with username and password. It also includes manual YAML examples with `username` and `password`.

`DEVELOPMENT_SETUP.md` lists "Your Aula credentials (username/password)" as a prerequisite and repeats username/password setup and troubleshooting guidance.

## Manifest and Dependencies

`custom_components/aula_easyiq/manifest.json` currently declares only `aiohttp>=3.8.0` in `requirements`. Existing code imports undeclared dependencies such as `requests`, `beautifulsoup4`/`bs4`, `lxml` parsing, and `pytz`.

The upstream inspiration repo declares `after_dependencies: ["http"]` because its auth flow registers Home Assistant HTTP views, and declares dependencies for parsing, requests, QR rendering, and cryptographic primitives. Those dependency names are useful context, but implementation must remain clean-room and MIT-compatible.

## Upstream Inspiration

The project README credits `scaarup/aula` as inspiration. A local inspection of upstream commit `e8c3ac3ddf80b3deea61b9d881b2269169f21a03` found:

- a MitID config flow with external auth status;
- local Home Assistant views for QR/status/identity selection;
- stored Aula `access_token`, `refresh_token`, and expiry state;
- Aula API calls that append `access_token`;
- token refresh support;
- a large vendored MitID/NemLog-in/SAML/OIDC client.

The upstream repo is GPL-3.0. This EasyIQ repo is MIT. The user explicitly approved a clean MIT-compatible implementation and rejected copying/vendoring GPL upstream source.

## Home Assistant Constraints

Home Assistant config flows own config entry data and support migrations through config entry version changes. Reauth is the expected path for invalid, expired, or revoked credentials. For this integration, old username/password entries should not be silently used, and password fallback should not remain.

## Open Unknowns

Live MitID/NemLog-in compatibility cannot be fully proven with mocked unit tests. A real guardian MitID account is required for final smoke testing.

Child login support is not part of the desired scope. The target is guardian MitID.
