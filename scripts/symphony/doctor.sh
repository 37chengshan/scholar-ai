#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/symphony/_common.sh
source "$script_dir/_common.sh"

ok() {
  echo "[ok] $*"
}

warn() {
  echo "[warn] $*"
}

check_cmd() {
  local name="$1"
  if command -v "$name" >/dev/null 2>&1; then
    ok "command available: $name"
  else
    warn "missing command: $name"
  fi
}

check_file() {
  local path="$1"
  if [[ -e "$path" ]]; then
    ok "path exists: $path"
  else
    warn "missing path: $path"
  fi
}

check_cmd git
check_cmd gh
check_cmd ssh
check_cmd codex
check_cmd mise

check_file "$workflow_file"
check_file "$symphony_bin"
check_file "$repo_root/.codex/skills/linear/SKILL.md"
check_file "$HOME/.codex/auth.json"

if [[ -n "${LINEAR_API_KEY:-}" ]]; then
  ok "LINEAR_API_KEY is set"
else
  warn "LINEAR_API_KEY is not set"
fi

assert_runtime_layout
ok "runtime roots are outside the repo"

if branch="$(default_branch)"; then
  ok "local default base branch resolved: $branch"
else
  warn "could not resolve origin/HEAD locally"
fi

if gh auth status >/dev/null 2>&1; then
  ok "gh auth status succeeded"
else
  warn "gh auth status failed"
fi

ssh_output="$(ssh -o BatchMode=yes -o ConnectTimeout=5 -T git@github.com 2>&1 || true)"
if printf '%s\n' "$ssh_output" | grep -Eq "successfully authenticated|You've successfully authenticated"; then
  ok "GitHub SSH authentication succeeded"
else
  warn "GitHub SSH authentication did not succeed"
  printf '%s\n' "$ssh_output"
fi

if git -C "$repo_root" ls-remote --symref origin HEAD >/dev/null 2>&1; then
  ok "origin default branch reachable over network"
else
  warn "origin default branch could not be verified over network"
fi

if codex app-server --help >/dev/null 2>&1; then
  ok "codex app-server is available"
else
  warn "codex app-server help failed"
fi

if codex app-server generate-json-schema --help >/dev/null 2>&1; then
  ok "codex app-server schema generator is available"
else
  warn "codex app-server schema generator help failed"
fi

echo
echo "workflow file: $workflow_file"
echo "symphony home: $SYMPHONY_HOME"
echo "logs root: $SYMPHONY_LOGS_ROOT"
echo "workspace root: $SYMPHONY_WORKSPACE_ROOT"
