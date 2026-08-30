#!/bin/zsh
set -e
LABEL="com.adams.financetracker"
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/$LABEL.plist"
echo "Finance Tracker service removed. Application data has NOT been deleted."
echo "To remove application files manually: sudo rm -rf /Applications/finance_tracker"
