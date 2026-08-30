#!/bin/zsh
LABEL="com.adams.financetracker"; PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"; launchctl bootstrap "gui/$(id -u)" "$PLIST" 2>/dev/null || true; launchctl kickstart -k "gui/$(id -u)/$LABEL"; echo "Finance Tracker service started."
