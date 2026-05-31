#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/../.." && pwd)"

: "${SYMPHONY_HOME:=$HOME/code/openai-symphony}"
: "${SYMPHONY_LOGS_ROOT:=/private/tmp/symphony/logs/scholar-ai}"
: "${SYMPHONY_WORKSPACE_ROOT:=/private/tmp/symphony/workspaces/scholar-ai}"

workflow_file="$repo_root/WORKFLOW.md"
symphony_elixir_dir="$SYMPHONY_HOME/elixir"
symphony_bin="$symphony_elixir_dir/bin/symphony"
runtime_dir="$repo_root/runtime/symphony"
pid_file="$runtime_dir/symphony.pid"
stdout_log="$runtime_dir/symphony.stdout.log"

fail() {
  echo "[symphony] $*" >&2
  exit 1
}

ensure_dirs() {
  mkdir -p "$runtime_dir" "$SYMPHONY_LOGS_ROOT" "$SYMPHONY_WORKSPACE_ROOT"
}

require_file() {
  local path="$1"
  [[ -e "$path" ]] || fail "missing required path: $path"
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "missing required command: $1"
}

require_env() {
  local name="$1"
  [[ -n "${!name:-}" ]] || fail "missing required env var: $name"
}

is_running() {
  [[ -f "$pid_file" ]] || return 1
  local pid
  pid="$(cat "$pid_file" 2>/dev/null || true)"
  [[ -n "$pid" ]] || return 1
  kill -0 "$pid" 2>/dev/null
}

default_branch() {
  git -C "$repo_root" symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#^origin/##'
}

assert_runtime_layout() {
  case "$SYMPHONY_LOGS_ROOT" in
    "$repo_root"/*) fail "SYMPHONY_LOGS_ROOT must live outside the repo: $SYMPHONY_LOGS_ROOT" ;;
  esac
  case "$SYMPHONY_WORKSPACE_ROOT" in
    "$repo_root"/*) fail "SYMPHONY_WORKSPACE_ROOT must live outside the repo: $SYMPHONY_WORKSPACE_ROOT" ;;
  esac
}

basic_preflight() {
  require_cmd git
  require_cmd codex
  require_cmd mise
  require_file "$workflow_file"
  require_file "$symphony_bin"
  require_env LINEAR_API_KEY
  assert_runtime_layout
  ensure_dirs
}
