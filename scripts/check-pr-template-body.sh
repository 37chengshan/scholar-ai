#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: check-pr-template-body.sh [--body BODY | --body-file FILE]

Validates that a PR body follows .github/pull_request_template.md and
contains non-placeholder content in the required sections.

Input can also be provided through the PR_BODY environment variable or stdin.
USAGE
  exit 1
}

body=""
body_file=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --body)
      body="$2"
      shift 2
      ;;
    --body-file)
      body_file="$2"
      shift 2
      ;;
    -h|--help)
      usage
      ;;
    *)
      echo "[pr-template-check] unknown argument: $1" >&2
      usage
      ;;
  esac
done

if [[ -n "$body_file" ]]; then
  if [[ ! -f "$body_file" ]]; then
    echo "[pr-template-check] body file not found: $body_file" >&2
    exit 2
  fi
  body_content="$(cat "$body_file")"
elif [[ -n "$body" ]]; then
  body_content="$body"
elif [[ -n "${PR_BODY:-}" ]]; then
  body_content="$PR_BODY"
elif [[ ! -t 0 ]]; then
  body_content="$(cat)"
else
  echo "[pr-template-check] missing PR body input" >&2
  usage
fi

if [[ -z "${body_content//[$' \n\r\t']/}" ]]; then
  echo "[pr-template-check] PR body is empty" >&2
  exit 3
fi

tmp_file="$(mktemp)"
trap 'rm -f "$tmp_file"' EXIT
# Normalize CRLF to LF for consistent matching
printf '%s\n' "$body_content" | tr -d '\r' > "$tmp_file"

required_sections=(
  "## 变更目的"
  "## 变更内容"
  "## 影响范围"
  "## 风险评估"
  "## 交付单元追踪"
  "## 自测清单"
  "## 文档是否需要同步"
)

section_body() {
  local section="$1"
  awk -v target="$section" '
    $0 == target { capture=1; next }
    /^## / && capture { exit }
    capture { print }
  ' "$tmp_file"
}

strip_comments_and_blank() {
  # Delete lines containing HTML comments (single-line <!-- ... -->)
  # Note: Using /<!--.*-->/d instead of /<!--/,/-->/d because BSD sed
  # treats the range as continuing even when both markers are on the same line
  sed '/<!--.*-->/d' | sed '/^\s*$/d'
}

is_placeholder_only() {
  local content="$1"
  local normalized
  normalized="$(printf '%s\n' "$content" \
    | strip_comments_and_blank \
    | sed 's/^\s*[-*]\s*//' \
    | sed 's/^\s*[-*] \[[ xX]\]\s*//' \
    | sed 's/^\s*//' \
    | sed 's/\s*$//' )"

  if [[ -z "${normalized//[$' \n\r\t']/}" ]]; then
    return 0
  fi

  # Remove lines that are just placeholder hints, then check if anything remains
  local non_placeholder
  non_placeholder="$(printf '%s\n' "$normalized" | grep -Ev '^(Closes #|Related #|低 / 中 / 高|页面：|接口：|服务/脚本：|数据/配置：|主要风险：|回滚方式：|Phase ID:|Deliverable Unit:|Migration-Task:|未覆盖项:)$')"

  if [[ -z "${non_placeholder//[$' \n\r\t']/}" ]]; then
    return 0
  fi

  return 1
}

for section in "${required_sections[@]}"; do
  if ! grep -Fxq "$section" "$tmp_file"; then
    echo "[pr-template-check] missing required section: $section" >&2
    exit 4
  fi

  content="$(section_body "$section")"
  if is_placeholder_only "$content"; then
    echo "[pr-template-check] section has no filled content: $section" >&2
    exit 5
  fi
done

change_section="$(section_body '## 变更内容')"
if ! printf '%s\n' "$change_section" | grep -Eq '^- \[x\] '; then
  echo "[pr-template-check] '## 变更内容' must mark at least one changed area with [x]" >&2
  exit 6
fi

test_section="$(section_body '## 自测清单')"
if ! printf '%s\n' "$test_section" | grep -Eq '^- \[x\] '; then
  echo "[pr-template-check] '## 自测清单' must mark at least one executed check with [x]" >&2
  exit 7
fi

docs_section="$(section_body '## 文档是否需要同步')"
selected_docs_options="$(printf '%s\n' "$docs_section" | grep -Ec '^- \[x\] (不需要|需要，已同步更新)')"
if [[ "$selected_docs_options" -ne 1 ]]; then
  echo "[pr-template-check] '## 文档是否需要同步' must explicitly choose one option with [x]" >&2
  exit 8
fi

echo "[pr-template-check] passed"