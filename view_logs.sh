#!/bin/bash
# Script to view system logs in real-time
# Usage: ./view_logs.sh

LOG_FILE="logs/fishery_system.log"

if [ ! -f "$LOG_FILE" ]; then
    echo "Log file not found: $LOG_FILE"
    echo "Make sure the system has been run at least once to create the log file."
    exit 1
fi

echo "Viewing logs from: $LOG_FILE"
echo "Press Ctrl+C to stop"
echo "================================"
tail -f "$LOG_FILE"

