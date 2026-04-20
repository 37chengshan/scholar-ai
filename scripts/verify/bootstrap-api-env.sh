#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
VENV_DIR="$API_DIR/.venv"

if [[ ! -d "$API_DIR" ]]; then
  echo "[bootstrap-api-env] apps/api not found"
  exit 1
fi

if [[ ! -d "$VENV_DIR" ]]; then
  echo "[bootstrap-api-env] creating venv at $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

PYTHON_BIN="$VENV_DIR/bin/python"
PIP_BIN="$VENV_DIR/bin/pip"

if [[ ! -x "$PYTHON_BIN" || ! -x "$PIP_BIN" ]]; then
  echo "[bootstrap-api-env] venv python/pip missing"
  exit 1
fi

echo "[bootstrap-api-env] installing backend dependencies"
cd "$API_DIR"
"$PYTHON_BIN" -m pip install --upgrade pip
"$PIP_BIN" install -r requirements.txt

echo "[bootstrap-api-env] validating pytest availability"
"$PYTHON_BIN" -c "import pytest"

echo "[bootstrap-api-env] ready"