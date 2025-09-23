#!/bin/bash
# Cron-friendly Package Status Monitor
# 
# This script is designed to be run from cron jobs for regular monitoring.
# It logs results to a file and can send alerts for stuck packages.
#
# Usage in crontab:
#   # Run every 5 minutes
#   */5 * * * * /path/to/cron-package-monitor.sh
#
#   # Run every hour with detailed output
#   0 * * * * /path/to/cron-package-monitor.sh --detailed
#
# Environment variables:
#   DATABASE_URL          - Database connection URL (required)
#   LOG_FILE              - Log file path (default: /tmp/package-monitor.log)
#   ALERT_THRESHOLD       - Alert if stuck packages exceed this count (default: 10)
#   ALERT_EMAIL           - Email address for alerts (optional)

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

# Configuration
LOG_FILE="${LOG_FILE:-/tmp/package-monitor.log}"
ALERT_THRESHOLD="${ALERT_THRESHOLD:-10}"
ALERT_EMAIL="${ALERT_EMAIL:-}"

# Change to backend directory
cd "$BACKEND_DIR"

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "$(date): ERROR: DATABASE_URL environment variable is not set" >> "$LOG_FILE"
    exit 1
fi

# Function to log with timestamp
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S'): $1" >> "$LOG_FILE"
}

# Function to send alert email
send_alert() {
    local message="$1"
    if [ -n "$ALERT_EMAIL" ] && command -v mail >/dev/null 2>&1; then
        echo "$message" | mail -s "Package Monitor Alert" "$ALERT_EMAIL"
    fi
    log_message "ALERT: $message"
}

# Function to check for stuck packages
check_stuck_packages() {
    local stuck_count
    stuck_count=$(python scripts/package_status_monitor.py --output json | \
                  python -c "
import json, sys
data = json.load(sys.stdin)
stuck = data.get('package_counts', {}).get('stuck_count', 0)
print(stuck)
" 2>/dev/null || echo "0")
    
    if [ "$stuck_count" -gt "$ALERT_THRESHOLD" ]; then
        send_alert "High number of stuck packages detected: $stuck_count (threshold: $ALERT_THRESHOLD)"
    fi
}

# Main execution
log_message "Starting package status monitoring..."

# Run the monitor and capture output
if python scripts/package_status_monitor.py --output json > /tmp/package-monitor-output.json 2>/dev/null; then
    # Parse the JSON output for logging
    python -c "
import json, sys
try:
    with open('/tmp/package-monitor-output.json', 'r') as f:
        data = json.load(f)
    
    timestamp = data.get('timestamp', 'unknown')
    counts = data.get('package_counts', {})
    
    print(f'Package Status Report - {timestamp}')
    print('=' * 50)
    
    # Sort by count (descending) but put TOTAL at the end
    sorted_items = sorted(
        [(k, v) for k, v in counts.items() if k != 'TOTAL'],
        key=lambda x: x[1],
        reverse=True
    )
    
    if 'TOTAL' in counts:
        sorted_items.append(('TOTAL', counts['TOTAL']))
    
    for status, count in sorted_items:
        print(f'{status:<20} {count:>8}')
    
    print('=' * 50)
    
except Exception as e:
    print(f'Error parsing monitor output: {e}')
" >> "$LOG_FILE"
    
    # Check for stuck packages if detailed mode is not enabled
    if [ "$1" != "--detailed" ]; then
        check_stuck_packages
    fi
    
    log_message "Package monitoring completed successfully"
else
    log_message "ERROR: Package monitoring failed"
    send_alert "Package monitoring script failed to execute"
    exit 1
fi

# Clean up temporary files
rm -f /tmp/package-monitor-output.json

log_message "Package monitoring finished"
