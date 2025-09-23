#!/bin/bash
# Package Status Monitoring Script Wrapper
# 
# This script provides easy access to the package status monitor with common configurations.
# 
# Usage:
#   ./monitor-packages.sh [command] [options]
#
# Commands:
#   once        - Run once and exit (default)
#   watch       - Run continuously with 30-second intervals
#   json        - Run once and output as JSON
#   detailed    - Show detailed breakdown with timestamps
#   help        - Show this help message
#
# Examples:
#   ./monitor-packages.sh                    # Run once
#   ./monitor-packages.sh watch              # Watch continuously
#   ./monitor-packages.sh json               # Output as JSON
#   ./monitor-packages.sh detailed           # Detailed breakdown

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

# Change to backend directory to ensure proper Python path
cd "$BACKEND_DIR"

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "❌ Error: DATABASE_URL environment variable is not set"
    echo "Please set DATABASE_URL before running this script."
    echo "Example: export DATABASE_URL=postgresql://user:pass@host/db"
    exit 1
fi

# Function to show help
show_help() {
    echo "Package Status Monitoring Script"
    echo "================================"
    echo ""
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  once        Run once and exit (default)"
    echo "  watch       Run continuously with 30-second intervals"
    echo "  json        Run once and output as JSON"
    echo "  detailed    Show detailed breakdown with timestamps"
    echo "  help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Run once"
    echo "  $0 watch              # Watch continuously"
    echo "  $0 json               # Output as JSON"
    echo "  $0 detailed           # Detailed breakdown"
    echo ""
    echo "Environment Variables:"
    echo "  DATABASE_URL          Database connection URL (required)"
    echo ""
}

# Parse command
COMMAND="${1:-once}"

case "$COMMAND" in
    "once")
        echo "🔍 Running package status monitor once..."
        python scripts/package_status_monitor.py
        ;;
    "watch")
        echo "👀 Starting continuous package monitoring (30s intervals)..."
        echo "Press Ctrl+C to stop"
        python scripts/package_status_monitor.py --continuous --interval 30
        ;;
    "json")
        echo "📊 Running package status monitor (JSON output)..."
        python scripts/package_status_monitor.py --output json
        ;;
    "detailed")
        echo "📋 Running detailed package status breakdown..."
        python scripts/package_status_monitor.py --detailed
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        echo "❌ Unknown command: $COMMAND"
        echo ""
        show_help
        exit 1
        ;;
esac
