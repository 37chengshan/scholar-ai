#!/usr/bin/env bash
# scripts/setup_specter2_env.sh
# Creates .venv-specter2 — an isolated Python venv for SPECTER2 embedding generation.
# Does NOT touch the main API venv (apps/api/.venv or ~/.virtualenvs/scholar-ai-api).
#
# Usage:
#   bash scripts/setup_specter2_env.sh
#   bash scripts/setup_specter2_env.sh --force   # recreate from scratch

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${REPO_ROOT}/.venv-specter2"
REQ_FILE="${REPO_ROOT}/requirements-specter2.txt"

FORCE=false
for arg in "$@"; do
  [[ "$arg" == "--force" ]] && FORCE=true
done

echo "=== SPECTER2 Isolated Environment Setup ==="
echo "Repo: ${REPO_ROOT}"
echo "Venv: ${VENV_DIR}"
echo ""

# Pick Python interpreter (prefer 3.11, fall back to 3.10/3.12)
PYTHON=""
for candidate in python3.11 python3.10 python3.12 python3; do
  if command -v "$candidate" &>/dev/null; then
    ver=$("$candidate" -c "import sys; print(sys.version_info[:2])" 2>/dev/null)
    echo "Found: $candidate ($ver)"
    PYTHON="$candidate"
    break
  fi
done

if [[ -z "$PYTHON" ]]; then
  echo "ERROR: No Python 3.10+ found. Install Python first."
  exit 1
fi

# Remove if force
if [[ "$FORCE" == true && -d "$VENV_DIR" ]]; then
  echo "Removing existing venv (--force)..."
  rm -rf "$VENV_DIR"
fi

# Create venv
if [[ ! -d "$VENV_DIR" ]]; then
  echo "Creating venv with $PYTHON..."
  "$PYTHON" -m venv "$VENV_DIR"
fi

PIP="${VENV_DIR}/bin/pip"

echo ""
echo "Upgrading pip..."
"$PIP" install --upgrade pip --quiet

echo ""
echo "Installing SPECTER2 dependencies from ${REQ_FILE}..."
"$PIP" install -r "$REQ_FILE" --quiet

echo ""
echo "=== Verification ==="
"${VENV_DIR}/bin/python" - <<'PYEOF'
import sys
print(f"Python: {sys.version}")

import transformers
print(f"transformers: {transformers.__version__}")

import adapters
print(f"adapters: {adapters.__version__}")

import torch
print(f"torch: {torch.__version__}")

import pymilvus
print(f"pymilvus: {pymilvus.__version__}")

# Smoke test: can we load AutoAdapterModel?
from adapters import AutoAdapterModel
print("AutoAdapterModel: importable ✓")

# Verify BERT compat
from transformers.models.bert.modeling_bert import BertModel
print(f"BertModel: importable ✓")

print("\n✅ specter2 venv OK")
PYEOF

echo ""
echo "Venv path: ${VENV_DIR}/bin/python"
echo "Done."
