#!/bin/bash
# Continuous trading loop for Alpaca AI Trading Agent
# Runs the paper trading cycle every 60 seconds and logs output

LOG_DIR="logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/trading_$TIMESTAMP.log"

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

echo "Starting continuous trading loop..."
echo "Log file: $LOG_FILE"
echo "Press Ctrl+C to stop"
echo "============================================================"

# Loop indefinitely
while true; do
    # Get current timestamp for the log entry
    CYCLE_TIME=$(date +"%Y-%m-%d %H:%M:%S")
    echo "[$CYCLE_TIME] Starting trading cycle" | tee -a "$LOG_FILE"

    # Run the paper trading cycle and append output to log file
    python -m backend.scripts.run_paper_cycle 2>&1 | tee -a "$LOG_FILE"

    # Add a separator between cycles
    echo "============================================================" | tee -a "$LOG_FILE"

    # Wait for 60 seconds (as per LOOP_INTERVAL_SECONDS in .env)
    sleep 60
done