#!/bin/zsh
set -e
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
python -m pip install -q -r requirements.txt
exec waitress-serve --listen=0.0.0.0:8080 app:app
