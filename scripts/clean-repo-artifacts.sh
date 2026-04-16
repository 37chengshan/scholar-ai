#!/usr/bin/env bash
set -euo pipefail

echo "[clean-repo-artifacts] removing local runtime/test artifacts"

rm -rf logs/archive
rm -rf test-results
rm -rf uploads

rm -rf apps/web/test-results
rm -f apps/web/frontend.log
rm -rf apps/web/.vite

rm -rf apps/api/htmlcov
rm -rf apps/api/htmlcov_*
rm -f apps/api/.coverage
rm -rf apps/api/venv
rm -rf apps/api/venv_new
rm -rf apps/api/.pytest_cache

find apps/api -type d -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true

echo "[clean-repo-artifacts] done"