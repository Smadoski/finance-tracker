#!/bin/zsh
TS="$(command -v tailscale 2>/dev/null || true)"; [ -n "$TS" ] || TS="/Applications/Tailscale.app/Contents/MacOS/Tailscale"
"$TS" serve --https=8443 off || "$TS" serve reset
