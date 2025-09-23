# Package Status Monitoring Script Wrapper (PowerShell)
# 
# This script provides easy access to the package status monitor with common configurations.
# 
# Usage:
#   .\monitor-packages.ps1 [command] [options]
#
# Commands:
#   once        - Run once and exit (default)
#   watch       - Run continuously with 30-second intervals
#   json        - Run once and output as JSON
#   detailed    - Show detailed breakdown with timestamps
#   help        - Show this help message
#
# Examples:
#   .\monitor-packages.ps1                    # Run once
#   .\monitor-packages.ps1 watch              # Watch continuously
#   .\monitor-packages.ps1 json               # Output as JSON
#   .\monitor-packages.ps1 detailed           # Detailed breakdown

param(
    [string]$Command = "once"
)

# Get the directory where this script is located
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Split-Path -Parent $ScriptDir

# Change to backend directory to ensure proper Python path
Set-Location $BackendDir

# Check if DATABASE_URL is set
if (-not $env:DATABASE_URL) {
    Write-Host "❌ Error: DATABASE_URL environment variable is not set" -ForegroundColor Red
    Write-Host "Please set DATABASE_URL before running this script." -ForegroundColor Yellow
    Write-Host "Example: `$env:DATABASE_URL = 'postgresql://user:pass@host/db'" -ForegroundColor Yellow
    exit 1
}

# Function to show help
function Show-Help {
    Write-Host "Package Status Monitoring Script" -ForegroundColor Green
    Write-Host "================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Usage: .\monitor-packages.ps1 [command] [options]"
    Write-Host ""
    Write-Host "Commands:"
    Write-Host "  once        Run once and exit (default)"
    Write-Host "  watch       Run continuously with 30-second intervals"
    Write-Host "  json        Run once and output as JSON"
    Write-Host "  detailed    Show detailed breakdown with timestamps"
    Write-Host "  help        Show this help message"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\monitor-packages.ps1                    # Run once"
    Write-Host "  .\monitor-packages.ps1 watch              # Watch continuously"
    Write-Host "  .\monitor-packages.ps1 json               # Output as JSON"
    Write-Host "  .\monitor-packages.ps1 detailed           # Detailed breakdown"
    Write-Host ""
    Write-Host "Environment Variables:"
    Write-Host "  DATABASE_URL          Database connection URL (required)"
    Write-Host ""
}

# Parse command
switch ($Command.ToLower()) {
    "once" {
        Write-Host "🔍 Running package status monitor once..." -ForegroundColor Cyan
        python scripts/package_status_monitor.py
    }
    "watch" {
        Write-Host "👀 Starting continuous package monitoring (30s intervals)..." -ForegroundColor Cyan
        Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
        python scripts/package_status_monitor.py --continuous --interval 30
    }
    "json" {
        Write-Host "📊 Running package status monitor (JSON output)..." -ForegroundColor Cyan
        python scripts/package_status_monitor.py --output json
    }
    "detailed" {
        Write-Host "📋 Running detailed package status breakdown..." -ForegroundColor Cyan
        python scripts/package_status_monitor.py --detailed
    }
    { $_ -in @("help", "-h", "--help") } {
        Show-Help
    }
    default {
        Write-Host "❌ Unknown command: $Command" -ForegroundColor Red
        Write-Host ""
        Show-Help
        exit 1
    }
}
