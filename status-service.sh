#!/bin/zsh
if launchctl print "gui/$(id -u)/com.adams.financetracker" >/dev/null 2>&1; then echo "Finance Tracker service: loaded"; else echo "Finance Tracker service: not loaded"; fi
curl -fsS -o /dev/null http://127.0.0.1:8080/ && echo "Application: responding" || echo "Application: not responding"
