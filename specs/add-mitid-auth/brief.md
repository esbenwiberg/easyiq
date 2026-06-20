---
title: "Add MitID authentication for EasyIQ"
touches:
  - custom_components/aula_easyiq/const.py
  - custom_components/aula_easyiq/config_flow.py
  - custom_components/aula_easyiq/__init__.py
  - custom_components/aula_easyiq/client.py
  - custom_components/aula_easyiq/manifest.json
  - custom_components/aula_easyiq/strings.json
  - custom_components/aula_easyiq/translations/en.json
  - custom_components/aula_easyiq/views.py
  - custom_components/aula_easyiq/mitid_auth.py
  - tests/
  - scripts/validate_ha_integration.py
  - scripts/test_client.py
  - scripts/dev_setup.py
  - README.md
  - DEVELOPMENT_SETUP.md
does_not_touch:
  - custom_components/aula_easyiq/calendar.py
  - custom_components/aula_easyiq/binary_sensor.py
  - custom_components/aula_easyiq/services.yaml
require_sidecars: []
---

## Task

Add guardian MitID authentication to the EasyIQ Home Assistant integration. Old Aula/Unilogin username-password authentication is no longer supported and must not remain as a fallback.

Implement this as a clean MIT-compatible solution. Do not copy, vendor, or adapt GPL-licensed source from `scaarup/aula`; that repo is only a behavioral reference.

## Why

The current integration setup stores old username/password credentials and the client scrapes obsolete Aula login forms. Users need a working MitID-based setup that stores Aula token state, refreshes tokens during polling, and continues fetching EasyIQ schedule/homework plus Aula presence/messages.

## Research Summary

Read `specs/add-mitid-auth/research.md` and `specs/add-mitid-auth/plan.md` before coding.

Current facts:

- `custom_components/aula_easyiq/config_flow.py` requires `username` and `password` and stores them in the config entry.
- `custom_components/aula_easyiq/__init__.py` constructs `EasyIQClient(username=entry.data["username"], password=entry.data["password"])`.
- `custom_components/aula_easyiq/client.py` scrapes `login.aula.dk/auth/login.php?type=unilogin`, posts `selectedIdp=uni_idp`, and relies on cookies for Aula API calls.
- Client auth success currently populates `_profiles`, `_institution_profiles`, `_children_data`, `children`, `apiurl`, and `_authenticated`; preserve those downstream expectations.
- EasyIQ `CalendarGetWeekplanEvents` uses an EasyIQ widget bearer token in the `authorization` header. Keep that API shape; change how the Aula widget bearer token is obtained.
- `manifest.json`, translations, README, development docs, and dev scripts still assume username/password.
- There is no `tests/` directory; add one.

## Plan

1. Add MitID/token constants and remove password-based setup from the new config flow.
2. Add a clean-room `mitid_auth.py` or `auth/` module with mockable interfaces for MitID auth, token exchange, token refresh, status, and errors.
3. Add local Home Assistant auth status views under this integration's domain, for example `/api/aula_easyiq/auth/{flow_id}` and status/identity subpaths.
4. Update `config_flow.py` to run a MitID external auth step and create entries with MitID username plus Aula token fields. Do not store `password`.
5. Update `__init__.py` to construct the client from token state, register/update runtime token state safely, implement migration for old username/password entries, and trigger reauth on invalid/revoked credentials.
6. Update `client.py` so all Aula API calls append/use `access_token`, refresh tokens when needed, and raise/propagate auth failure instead of silently returning empty data on token failure.
7. Preserve EasyIQ calendar/homework data parsing and child ID mapping behavior.
8. Update manifest requirements and docs/scripts/translations away from username/password.
9. Add tests and update validation.

## Checkpoints

1. Define the new config-entry schema and old-entry migration/reauth behavior.
2. Implement clean-room auth interfaces and mocked test seams.
3. Implement config flow plus HTTP views.
4. Update setup/client token lifecycle.
5. Update all Aula API calls to include token auth.
6. Update docs, scripts, manifest, and translations.
7. Add tests and run the required fact commands.
8. Document manual guardian MitID smoke test status in the PR/body/wrap-up.

## Touches

Expected touches are the auth/config/client files, a new auth module and views file, tests, validation script, docs, manifest, translations, and old auth helper scripts listed in the frontmatter.

## Does Not Touch

Do not change `calendar.py`, `binary_sensor.py`, or `services.yaml`. Avoid changing `sensor.py` unless auth error propagation through the coordinator requires a small, justified adjustment.

## Constraints

- Keep the repo MIT-compatible. Do not copy GPL source from upstream.
- Guardian MitID only; no child-login support.
- No old username/password fallback.
- Do not store passwords in new or migrated config entries.
- Token refresh must not create Home Assistant reload loops.
- Mocked tests must not require real MitID credentials.
- Live MitID compatibility still needs manual guardian account testing.

## Test Expectations

Create/update these proof artifacts:

- `tests/test_mitid_config_flow.py`: new setup stores MitID/token fields and omits `password`.
- `tests/test_easyiq_token_auth.py`: mocked Aula API calls include `access_token` for profile discovery, profile context, widget token, messages, and presence.
- `tests/test_config_entry_migration.py`: old username/password entries are converted to reauth-required state or otherwise migrated without preserving the password.
- `scripts/validate_ha_integration.py`: verifies the new auth files/manifest requirements/translations and rejects user-facing Unilogin password setup strings.

Run each narrow test command from `contract.yaml`, then run the repo's normal validation script.

## Risks / Pitfalls

- Partial token conversion is dangerous: one missed Aula API call can make only some entities fail.
- Do not mutate `entry.data` on every token refresh in a way that causes reload churn.
- Config flow external views must be scoped by flow/session ID and not leak tokens.
- Live MitID protocol behavior cannot be proven by unit tests alone.

## Wrap-up

Before finishing:
1. Run the profile finish prompt if one is configured.
2. Re-run build and tests; both must still pass.
3. Commit and push.
