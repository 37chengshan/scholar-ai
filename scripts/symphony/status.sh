#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/symphony/_common.sh
source "$script_dir/_common.sh"

echo "workflow: $workflow_file"
echo "symphony home: $SYMPHONY_HOME"
echo "logs root: $SYMPHONY_LOGS_ROOT"
echo "workspace root: $SYMPHONY_WORKSPACE_ROOT"
echo "default base branch: $(default_branch || echo unknown)"

if is_running; then
  pid="$(cat "$pid_file")"
  echo "status: running"
  echo "pid: $pid"
  ps -p "$pid" -o pid=,etime=,command= || true
else
  echo "status: stopped"
fi

if [[ -f "$stdout_log" ]]; then
  echo
  echo "recent output:"
  tail -n 20 "$stdout_log" || true
fi
