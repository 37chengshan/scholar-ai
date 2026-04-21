#!/usr/bin/env bash
set -euo pipefail

usage(){
  cat <<'USAGE'
Usage: pr_create_with_template_check.sh --title "TITLE" (--body "BODY" | --body-file FILE) [--repo OWNER/REPO] [--base BASE]

This script validates the PR body against .github/pull_request_template.md before calling 'gh pr create'.

Examples:
  pr_create_with_template_check.sh --title "chore: ..." --body-file ./pr_body.md --repo owner/repo --base main
  pr_create_with_template_check.sh --title "chore: ..." --body "## 变更目的\n- ..." --repo owner/repo
USAGE
  exit 1
}

title=""
body=""
body_file=""
repo=""
base=""
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -t|--title)
      title="$2"; shift 2;;
    -b|--body)
      body="$2"; shift 2;;
    -f|--body-file)
      body_file="$2"; shift 2;;
    -r|--repo)
      repo="$2"; shift 2;;
    --base)
      base="$2"; shift 2;;
    -h|--help)
      usage;;
    *)
      echo "Unknown argument: $1"; usage;;
  esac
done

if [[ -z "$title" ]]; then
  echo "Error: --title is required" >&2
  usage
fi

if [[ -n "$body_file" ]]; then
  if [[ ! -f "$body_file" ]]; then
    echo "Error: body file not found: $body_file" >&2; exit 2
  fi
  body_content=$(cat "$body_file")
else
  body_content="${body-}"
fi

if [[ -z "${body_content:-}" ]]; then
  echo "Error: PR body is empty; provide via --body or --body-file" >&2
  usage
fi

validate_script="$script_dir/check-pr-template-body.sh"
if [[ ! -x "$validate_script" ]]; then
  chmod +x "$validate_script"
fi

printf '%s\n' "$body_content" | "$validate_script"

tmpfile=$(mktemp)
trap 'rm -f "$tmpfile"' EXIT
printf '%s\n' "$body_content" > "$tmpfile"

cmd=(gh pr create --title "$title" --body-file "$tmpfile")
if [[ -n "$repo" ]]; then cmd+=(--repo "$repo"); fi
if [[ -n "$base" ]]; then cmd+=(--base "$base"); fi

echo "Creating PR with title: $title"
(
  cd "$repo_root"
  "${cmd[@]}"
)
status=$?
exit $status
