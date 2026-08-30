#!/bin/zsh
set -e
TS="$(command -v tailscale 2>/dev/null || true)"
if [ -z "$TS" ] && [ -x "/Applications/Tailscale.app/Contents/MacOS/Tailscale" ]; then TS="/Applications/Tailscale.app/Contents/MacOS/Tailscale"; fi
[ -n "$TS" ] || { echo "Tailscale CLI not found. Install and sign in to Tailscale first."; exit 1; }
echo "Publishing Finance Tracker privately inside your tailnet..."
"$TS" serve --bg --https=8443 127.0.0.1:8080
"$TS" serve status
