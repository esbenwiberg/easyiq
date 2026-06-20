# Plan: Add MitID Auth

## Overview

Replace the obsolete Aula/Unilogin username-password scraper with a MitID-backed Aula token flow while keeping this repository MIT-compatible. Do not copy or vendor GPL-licensed upstream code. Use the upstream repo only as behavioral reference for the broad shape: external auth status, token storage, Aula API access-token usage, and refresh/reauth lifecycle.

## Desired End State

New setup uses guardian MitID. The integration stores Aula access/refresh token state and MitID username, not an Aula/Unilogin password. Data updates use token-backed Aula API calls to discover profiles, fetch presence/messages, and obtain EasyIQ widget bearer tokens. EasyIQ schedule/homework calls continue using the widget bearer token.

Existing username/password config entries are handled predictably: on migration/setup they are moved into a state that requires MitID reauthentication instead of attempting unsupported password auth or preserving passwords.

Docs, translations, dev scripts, manifest requirements, and validation reflect the new MitID auth shape.

## What We Are Not Doing

- No GPL source copy or vendored `scaarup/aula` MitID client.
- No username/password fallback.
- No child-login support.
- No redesign of calendar, binary sensor, or sensor entities except minimal auth-error propagation if needed.
- No claim that mocks prove live MitID protocol compatibility.

## Implementation Approach

1. Introduce new auth constants in `const.py`.

   Add keys for MitID username, auth method if needed, token state, token expiry, and any config-flow status fields. Keep old `CONF_USERNAME`/`CONF_PASSWORD` only as migration sentinels if useful; do not use them for new setup.

2. Add a clean-room auth boundary.

   Create either `custom_components/aula_easyiq/mitid_auth.py` or `custom_components/aula_easyiq/auth/`. This boundary should expose small interfaces that the config flow and client can mock in tests:

   - start or continue MitID auth;
   - expose QR/status/identity-selection data if the implementation supports app auth;
   - exchange a successful MitID/OIDC result for Aula tokens;
   - refresh access tokens from a refresh token;
   - report structured auth failures.

   Keep GPL upstream files out of the repo.

3. Replace config flow setup with MitID.

   Update `config_flow.py` so new installs collect MitID username and feature toggles. Run authentication through an external step and local Home Assistant HTTP views, similar in user experience to the upstream repo but implemented independently. Store token fields in `entry.data` and never store a password.

4. Register auth status views.

   Add `views.py` or equivalent. Register views during config flow authentication. The views should be scoped to flow/session IDs, return status/QR/identity data, and allow identity selection when needed. Keep view names/URLs under this integration's domain, e.g. `/api/aula_easyiq/auth/...`.

5. Update setup, migration, and reauth.

   In `__init__.py`, extract token state from `entry.data`, construct `EasyIQClient` with MitID username/token state, and perform token validation/refresh instead of password login. Implement `async_migrate_entry` for old version 1 entries containing `username`/`password`; remove password data and force reauth, or otherwise mark the entry so setup raises `ConfigEntryAuthFailed` with a clear reauth path. Add explicit `async_step_reauth` handling.

6. Update `EasyIQClient` for token-backed Aula API.

   Replace `login()`/`authenticate()` internals with token validation and refresh. Add a helper to append `access_token` to every Aula API request:

   - `profiles.getProfilesByLogin`;
   - `profiles.getProfileContext`;
   - `aulaToken.getWidgets`;
   - `aulaToken.getAulaToken`;
   - `presence.getDailyOverview`;
   - `messaging.getThreads`;
   - `messaging.getMessagesForThread`.

   Preserve population of `_profiles`, `_institution_profiles`, `_children_data`, `children`, `apiurl`, and `_authenticated`. Preserve EasyIQ `CalendarGetWeekplanEvents` request semantics except for replacing `x-login` with the appropriate MitID username/session identifier if needed.

7. Update docs and scripts.

   Update README, development setup, `scripts/test_client.py`, `scripts/dev_setup.py`, and any debug scripts that instruct username/password auth. Where live testing is still needed, document MitID/manual smoke flow instead of `.env` password credentials.

8. Add durable tests.

   Add a `tests/` directory with narrow tests around config flow data shape, token URL plumbing, refresh failure/reauth, and old-entry migration. Use mocked auth/session objects; do not require real MitID in tests.

9. Extend validation.

   Update `scripts/validate_ha_integration.py` so it checks for the new auth files/manifest requirements/translations and rejects old setup strings such as "Unilogin password" in user-facing setup text.

## Checkpoints

1. Define auth constants, token data model, and migration behavior.
2. Add clean-room auth boundary and mockable interfaces.
3. Update config flow and views for MitID external auth.
4. Update setup/reauth/migration lifecycle.
5. Update client Aula API calls to use `access_token` and refresh tokens.
6. Update docs, scripts, manifest, and translations.
7. Add and run narrow tests plus validation.
8. Perform or document manual real guardian MitID smoke test results.

## Test Strategy

- `tests/test_mitid_config_flow.py`: proves new setup stores MitID/token fields and no password.
- `tests/test_easyiq_token_auth.py`: proves Aula API URLs include `access_token` for profile, profile context, widget token, messages, and presence calls.
- `tests/test_config_entry_migration.py`: proves old username/password entries are migrated or converted to reauth-required state without preserving the password.
- `scripts/validate_ha_integration.py`: updated static check proves manifest/files/translations reflect MitID auth and old Unilogin password UI text is gone.

Live MitID testing remains manual because the protocol requires real guardian approval.

## Risks / Pitfalls

- MitID/NemLog-in flow details may change and cannot be fully covered without a live account.
- Accidentally copying GPL upstream implementation would violate the approved clean-MIT strategy.
- Missing `access_token` on one Aula API call can produce partial data failures that broad import tests would not catch.
- Token refresh loops can trigger Home Assistant reload churn if refreshed tokens are persisted incorrectly; runtime token updates should avoid reload loops.
