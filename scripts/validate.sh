#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

find_python() {
  if [[ -n "${PYTHON:-}" ]]; then
    echo "$PYTHON"
    return 0
  fi

  for candidate in "$ROOT_DIR/.venv/bin/python" python3.12 python3.11 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      command -v "$candidate"
      return 0
    fi
  done

  echo "No Python interpreter found. Install Python 3.11+ or run scripts/bootstrap-dev.sh." >&2
  return 1
}

PYTHON_BIN="$(find_python)"

"$PYTHON_BIN" - <<'PY'
import sys

if sys.version_info < (3, 11):
    raise SystemExit(
        f"Python 3.11+ is required; found {sys.version.split()[0]}. "
        "Set PYTHON=/path/to/python3.11+ or run scripts/bootstrap-dev.sh."
    )
PY

export PYTHONPYCACHEPREFIX="${PYTHONPYCACHEPREFIX:-$ROOT_DIR/.pycache}"
mkdir -p "$PYTHONPYCACHEPREFIX"

echo "==> Python syntax check"
"$PYTHON_BIN" -m compileall -q custom_components scripts tests

echo "==> Home Assistant structure validation"
"$PYTHON_BIN" scripts/validate_ha_integration.py

echo "==> Offline unit tests"
"$PYTHON_BIN" -m unittest discover -s tests/unit

if "$PYTHON_BIN" -c "import homeassistant" >/dev/null 2>&1; then
  echo "==> Home Assistant import smoke"
  "$PYTHON_BIN" - <<'PY'
import importlib

for module_name in (
    "custom_components.aula_easyiq",
    "custom_components.aula_easyiq.binary_sensor",
    "custom_components.aula_easyiq.calendar",
    "custom_components.aula_easyiq.config_flow",
    "custom_components.aula_easyiq.sensor",
):
    importlib.import_module(module_name)
PY
else
  echo "==> Skipping Home Assistant import smoke; install requirements-dev.txt to enable it"
fi

echo "==> Validation complete"
