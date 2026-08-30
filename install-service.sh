#!/bin/zsh
set -e
APP_DIR="/Applications/finance_tracker"; LABEL="com.adams.financetracker"; PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"; LOG_DIR="$HOME/Library/Logs/FinanceTracker"
mkdir -p "$HOME/Library/LaunchAgents" "$LOG_DIR"
cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd"><plist version="1.0"><dict><key>Label</key><string>$LABEL</string><key>ProgramArguments</key><array><string>$APP_DIR/service-run.sh</string></array><key>RunAtLoad</key><true/><key>KeepAlive</key><true/><key>StandardOutPath</key><string>$LOG_DIR/stdout.log</string><key>StandardErrorPath</key><string>$LOG_DIR/stderr.log</string></dict></plist>
PLIST
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true; launchctl bootstrap "gui/$(id -u)" "$PLIST"; launchctl kickstart -k "gui/$(id -u)/$LABEL"
echo "Finance Tracker service installed and started."
