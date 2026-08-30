#!/bin/zsh
set -e
cd "$(dirname "$0")"
./build-macos-pkg.sh
PKG="FinanceTracker-v$(cat VERSION)-macOS.pkg"
echo
echo "Installer created: $PKG"
open -R "$PKG" 2>/dev/null || true
echo "You can now double-click the .pkg to install or upgrade Finance Tracker."
read -k 1 "?Press any key to close..."
echo
