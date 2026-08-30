#!/bin/zsh
set -e
APP_DIR="/Applications/finance_tracker"
cd "$APP_DIR"
source .venv/bin/activate
exec waitress-serve --listen=0.0.0.0:8080 app:app
