#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/symphony/_common.sh
source "$script_dir/_common.sh"

if ! is_running; then
  rm -f "$pid_file"
  echo "[symphony] not running"
  exit 0
fi

pid="$(cat "$pid_file")"
kill "$pid" 2>/dev/null || true

for _ in 1 2 3 4 5; do
  if ! kill -0 "$pid" 2>/dev/null; then
    rm -f "$pid_file"
    echo "[symphony] stopped"
    exit 0
  fi
  sleep 1
done

kill -9 "$pid" 2>/dev/null || true
rm -f "$pid_file"
echo "[symphony] force stopped"
