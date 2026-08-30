#!/bin/zsh
set -e
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/Documents/FinanceTrackerBackups"
mkdir -p "$DEST"
STAMP=$(date +%Y-%m-%d_%H-%M-%S)

# Keep the familiar standalone database backup for quick restores.
cp "$APP_DIR/data/finance.db" "$DEST/finance_$STAMP.db"

# v2.0 also stores receipt images in data/receipts, so create a complete data snapshot.
tar -czf "$DEST/finance_data_$STAMP.tar.gz" -C "$APP_DIR" data

find "$DEST" -type f -name 'finance_*.db' -mtime +90 -delete
find "$DEST" -type f -name 'finance_data_*.tar.gz' -mtime +90 -delete
