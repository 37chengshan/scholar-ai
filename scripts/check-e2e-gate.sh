#!/usr/bin/env bash
set -euo pipefail

mode="manifest"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      mode="$2"
      shift 2
      ;;
    *)
      echo "[e2e-gate] unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

required_specs=(
  "apps/web/e2e/chat-critical.spec.ts"
  "apps/web/e2e/kb-critical.spec.ts"
  "apps/web/e2e/retrieval-critical.spec.ts"
)

for spec in "${required_specs[@]}"; do
  if [[ ! -f "$spec" ]]; then
    echo "[e2e-gate] missing critical e2e spec: $spec" >&2
    exit 1
  fi
done

if [[ ! -f "apps/web/package.json" ]]; then
  echo "[e2e-gate] missing apps/web/package.json" >&2
  exit 1
fi

if ! grep -Fq '"test:e2e"' apps/web/package.json; then
  echo "[e2e-gate] missing script test:e2e in apps/web/package.json" >&2
  exit 1
fi

if ! grep -Fq '"test:e2e:ci"' apps/web/package.json; then
  echo "[e2e-gate] missing script test:e2e:ci in apps/web/package.json" >&2
  exit 1
fi

if [[ "$mode" == "manifest" ]]; then
  echo "[e2e-gate] manifest validation passed"
  exit 0
fi

if [[ "$mode" != "run" ]]; then
  echo "[e2e-gate] invalid mode: $mode" >&2
  exit 2
fi

pushd apps/web >/dev/null
npm ci
npm run test:e2e:ci
popd >/dev/null

echo "[e2e-gate] run mode passed"
