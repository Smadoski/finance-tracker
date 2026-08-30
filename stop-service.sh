#!/bin/zsh
launchctl bootout "gui/$(id -u)/com.adams.financetracker" 2>/dev/null || true; echo "Finance Tracker service stopped."
