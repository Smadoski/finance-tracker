#!/bin/zsh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
VERSION="$(cat "$ROOT/VERSION")"
# Build an offline dependency wheelhouse on the Mac build host.
# The resulting .pkg installs Python packages without contacting PyPI.
WHEELHOUSE="$ROOT/wheelhouse"
mkdir -p "$WHEELHOUSE"
PYTHON_BIN="$(command -v python3 2>/dev/null || true)"
for CANDIDATE in /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
  if [[ -z "$PYTHON_BIN" && -x "$CANDIDATE" ]]; then PYTHON_BIN="$CANDIDATE"; fi
done
if [[ -z "$PYTHON_BIN" ]]; then
  echo "Python 3 is required on the build Mac to prepare Finance Tracker dependencies." >&2
  exit 1
fi
"$PYTHON_BIN" -m pip download --dest "$WHEELHOUSE" -r "$ROOT/requirements.txt"


# Apple Installer requires package scripts to be executable.
chmod 755 "$ROOT/packaging/macos/scripts/preinstall" "$ROOT/packaging/macos/scripts/postinstall"
chmod 755 "$ROOT/build-macos-pkg.sh" "$ROOT/Build Finance Tracker Installer.command" 2>/dev/null || true
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
PAYLOAD="$WORK/payload"
mkdir -p "$PAYLOAD/Applications/finance_tracker"
rsync -a \
  --exclude .git --exclude .venv --exclude .pytest_cache --exclude '__pycache__' \
  --exclude '*.pyc' --exclude data --exclude wheelhouse --exclude packaging \
  --exclude 'FinanceTracker-*.pkg' --exclude 'FinanceTracker-*.zip' \
  "$ROOT/" "$PAYLOAD/Applications/finance_tracker/"
chmod +x "$PAYLOAD/Applications/finance_tracker"/*.sh 2>/dev/null || true
pkgbuild --root "$PAYLOAD" --scripts "$ROOT/packaging/macos/scripts" --identifier com.adams.financetracker --version "$VERSION" --install-location / "$WORK/FinanceTracker-component.pkg"
productbuild --package "$WORK/FinanceTracker-component.pkg" "$ROOT/FinanceTracker-v${VERSION}-macOS.pkg"
echo "Created: $ROOT/FinanceTracker-v${VERSION}-macOS.pkg"
