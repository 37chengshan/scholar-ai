#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
DEFAULT_VENV_DIR="$HOME/.virtualenvs/scholar-ai-api"
VENV_DIR="${SCHOLAR_AI_API_VENV_DIR:-$DEFAULT_VENV_DIR}"
PYTHON_BIN="$VENV_DIR/bin/python"

if [[ ! -d "$API_DIR" ]]; then
  echo "[bootstrap-shared-api-env] apps/api not found"
  exit 1
fi

mkdir -p "$(dirname "$VENV_DIR")"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "[bootstrap-shared-api-env] creating shared venv at $VENV_DIR"
  if command -v uv >/dev/null 2>&1; then
    uv venv --python 3.11 "$VENV_DIR"
  else
    python3 -m venv "$VENV_DIR"
  fi
fi

echo "[bootstrap-shared-api-env] installing backend dependencies from apps/api/requirements.txt"
if command -v uv >/dev/null 2>&1; then
  uv pip install --python "$PYTHON_BIN" -r "$API_DIR/requirements.txt"
else
  "$PYTHON_BIN" -m pip install --upgrade pip
  "$PYTHON_BIN" -m pip install -r "$API_DIR/requirements.txt"
fi

echo "[bootstrap-shared-api-env] validating pytest availability"
"$PYTHON_BIN" -c "import pytest"

cat <<EOF
[bootstrap-shared-api-env] ready
Interpreter: $PYTHON_BIN
VS Code workspace default: ${HOME}/.virtualenvs/scholar-ai-api/bin/python

If you prefer another shared path, rerun with:
SCHOLAR_AI_API_VENV_DIR=/custom/path bash scripts/bootstrap-shared-api-env.sh
EOF
