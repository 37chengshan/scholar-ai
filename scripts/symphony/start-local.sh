#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/symphony/_common.sh
source "$script_dir/_common.sh"

basic_preflight

if is_running; then
  echo "[symphony] already running (pid $(cat "$pid_file"))"
  exit 0
fi

rm -f "$stdout_log"

(
  cd "$symphony_elixir_dir"
  nohup mise exec -- ./bin/symphony \
    --i-understand-that-this-will-be-running-without-the-usual-guardrails \
    --logs-root "$SYMPHONY_LOGS_ROOT" \
    "$workflow_file" </dev/null >"$stdout_log" 2>&1 &
  echo $! >"$pid_file"
)

sleep 2

if ! is_running; then
  echo "[symphony] failed to start; recent output:" >&2
  sed -n '1,120p' "$stdout_log" >&2 || true
  rm -f "$pid_file"
  exit 1
fi

echo "[symphony] started"
echo "pid: $(cat "$pid_file")"
echo "workflow: $workflow_file"
echo "logs root: $SYMPHONY_LOGS_ROOT"
echo "workspace root: $SYMPHONY_WORKSPACE_ROOT"
