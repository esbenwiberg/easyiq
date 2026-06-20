# EasyIQ Test Pyramid

EasyIQ needs fast checks for autonomous agents and slower checks for Home
Assistant and live EasyIQ behavior. Keep the lower layers credential-free.

## 1. Offline Unit Tests

Command:

```bash
./scripts/validate.sh
```

Scope:

- Pure update policy, date, parser, and formatting helpers.
- Manifest and translation contracts.
- No Home Assistant import.
- No network.
- No `.env`.

Add tests here first whenever behavior can be extracted from HA classes.

## 2. Home Assistant Integration Tests

Command, once tests exist:

```bash
.venv/bin/python -m pytest
```

Scope:

- Config flow behavior.
- Entity setup and unique IDs.
- Coordinator lifecycle with fake clients.
- Calendar and binary sensor behavior against HA objects.

Use `pytest-homeassistant-custom-component` and fake the EasyIQ client. These
tests should still avoid live Aula/EasyIQ traffic.

## 3. Repository Validation

Command:

```bash
./scripts/validate.sh
```

Scope:

- Python 3.11+ enforcement.
- Syntax compilation with bytecode cached inside the repo.
- Home Assistant structure validation.
- Offline unit tests.
- HA import smoke when dependencies are installed.

## 4. Hassfest and HACS Validation

Scope:

- Home Assistant custom integration packaging rules.
- HACS repository rules.

These run in GitHub Actions and complement local validation.

## 5. Local Home Assistant Smoke

Commands:

```bash
python scripts/dev_start.py
python scripts/docker_setup.py
```

Scope:

- The integration appears in Home Assistant.
- Config flow renders.
- Entities load after setup.
- Logs are clean enough to diagnose failures.

This layer can use `.env` credentials but should be run intentionally.

## 6. Live Aula/EasyIQ Smoke

Command:

```bash
python scripts/test_client.py
```

Scope:

- Authentication still works.
- Children, weekplan, homework, presence, and messages can be fetched.

This is opt-in only because it touches real services and real user data.
