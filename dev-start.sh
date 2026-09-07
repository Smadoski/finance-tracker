#!/bin/zsh
set -e
cd "$(dirname "$0")"
[ -x .venv/bin/python ] || /opt/homebrew/bin/python3 -m venv .venv
source .venv/bin/activate
exec waitress-serve --listen=127.0.0.1:${PORT:-8080} app:app

