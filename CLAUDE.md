# CLAUDE.md - EasyIQ Home Assistant Integration

This is a Home Assistant custom integration for Aula + EasyIQ. The integration
domain and folder are `aula_easyiq`.

Read this before changing code.

## Self-validation

The standard local contract is:

```bash
./scripts/validate.sh
```

It runs:

| Gate | What it checks |
| ---- | -------------- |
| Python version | Python 3.11+ so the source syntax matches the project contract |
| Syntax | `compileall` over `custom_components`, `scripts`, and `tests` |
| HA structure | Manifest, required integration files, config flow, sensors, translations |
| Offline unit tests | Pure stdlib tests under `tests/unit`, no Home Assistant or network required |
| HA import smoke | Runs only when Home Assistant is installed locally |

Any non-zero exit means the work is not done.

## First-clone setup

For the full local toolchain:

```bash
./scripts/bootstrap-dev.sh
./scripts/validate.sh
```

The offline validation lane does not need Aula credentials. Only create `.env`
when you intentionally run live API or Home Assistant development flows:

```bash
cp .env.template .env
python scripts/dev_start.py
```

## Dev and live checks

Use these only when the change needs that level of confidence:

| Command | Use |
| ------- | --- |
| `python scripts/dev_start.py` | Run Home Assistant locally at `http://localhost:8123` with this integration linked in |
| `python scripts/docker_setup.py` | Start a Docker-backed Home Assistant dev instance |
| `python scripts/test_client.py` | Opt-in live Aula/EasyIQ API check; requires real credentials in `.env` |
| `python scripts/debug_helper.py` | Interactive diagnosis for local HA setup and API issues |

Live account scripts must never run in default validation. Keep them explicit
because they touch real services and real family/school data.

## Test pyramid

1. **Pure unit tests** live in `tests/unit`. They must not import Home Assistant
   or call the network. Extract pure helpers from integration modules when a
   behavior deserves fast coverage.
2. **Home Assistant integration tests** should use `pytest-homeassistant-custom-component`
   once the behavior needs HA entities, config entries, or coordinator lifecycle.
3. **Repository validation** is `./scripts/validate.sh`.
4. **CI validation** uses hassfest and HACS validation from `.github/workflows`.
5. **Local HA smoke** uses `scripts/dev_start.py` or `scripts/docker_setup.py`.
6. **Live Aula/EasyIQ smoke** uses `scripts/test_client.py` and is opt-in only.

## Trip-wires

- The integration folder is `custom_components/aula_easyiq`. Do not document or
  copy `custom_components/easyiq`.
- Default tests and validation must be credential-free and network-free.
- Keep real credentials out of fixtures, logs, docs, and screenshots.
- If code imports a new third-party runtime package, add it to
  `custom_components/aula_easyiq/manifest.json` and `requirements-dev.txt`.
- Prefer extracting pure parsing, date, and update-policy logic before testing;
  Home Assistant imports are expensive and slow for tight agent loops.
- The client boundary in `client.py` talks to Aula/EasyIQ. Keep request logic
  isolated so parsing and transformation can be tested offline.

## Coverage map

| Surface | Coverage | Notes |
| ------- | -------- | ----- |
| Manifest/runtime dependency contract | Unit tests | `tests/unit/test_manifest_contract.py` |
| Coordinator update interval policy | Unit tests | `tests/unit/test_update_policy.py` |
| HA integration structure | Scripted validation | `scripts/validate_ha_integration.py` |
| Entity behavior | Gap | Add HA integration tests before deep entity refactors |
| Calendar parsing | Gap | Extract pure parser helpers before expanding coverage |
| EasyIQ/Aula client parsing | Gap | Extract response mappers before changing API handling |
| Live authentication | Manual smoke | `scripts/test_client.py`, credentials required |

## Context locations

- `custom_components/aula_easyiq/` - Home Assistant integration source
- `scripts/` - local setup, validation, debug, and live smoke tools
- `docs/` - usage guides and implementation notes
- `.github/workflows/` - hassfest and HACS validation
- `tests/unit/` - fast offline tests
