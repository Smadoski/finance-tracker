#!/bin/zsh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
VERSION="$(tr -d '[:space:]' < "$ROOT/VERSION")"
RELEASE_NAME="FinanceTracker-v${VERSION}-build"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

rsync -a \
  --exclude .git --exclude .venv --exclude .pytest_cache --exclude '__pycache__' \
  --exclude '*.pyc' --exclude data --exclude wheelhouse \
  --exclude 'FinanceTracker-*.pkg' --exclude 'FinanceTracker-*.zip' \
  "$ROOT/" "$STAGE/$RELEASE_NAME/"

chmod +x "$STAGE/$RELEASE_NAME"/*.sh "$STAGE/$RELEASE_NAME"/*.command 2>/dev/null || true
(
  cd "$STAGE"
  /usr/bin/zip -q -r -X "FinanceTracker-v${VERSION}.zip" "$RELEASE_NAME"
)
mv "$STAGE/FinanceTracker-v${VERSION}.zip" "$ROOT/FinanceTracker-v${VERSION}.zip"
echo "Created: $ROOT/FinanceTracker-v${VERSION}.zip"
