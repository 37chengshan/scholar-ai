#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR" || exit 1

RELEASES_DIR="$ROOT_DIR/releases"
mkdir -p "$RELEASES_DIR"

DATE="$(date -u +%Y%m%dT%H%M%SZ)"
NAME="scholar-ai-${DATE}"
ARCHIVE="$RELEASES_DIR/${NAME}.tar.gz"
EXCLUDE_FILE="$ROOT_DIR/.packageignore"

echo "Creating archive: ${ARCHIVE}"
# Use -C to ensure paths are stored relative to repo root
tar -czf "$ARCHIVE" --exclude-from="$EXCLUDE_FILE" -C "$ROOT_DIR" .

if [ -f "$ARCHIVE" ]; then
  echo "Archive created: ${ARCHIVE}"
  du -h "$ARCHIVE" || true
else
  echo "Archive creation failed" >&2
  exit 2
fi
