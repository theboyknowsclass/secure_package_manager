# Package Status Monitoring Scripts

This directory contains scripts for monitoring package processing status in the secure package manager system.

## Scripts Overview

### 1. `package_status_monitor.py` - Main Monitoring Script

The core Python script that queries the database for package status counts.

**Features:**
- Count packages by status
- Detailed breakdown with timestamps
- Multiple output formats (table, JSON, CSV)
- Continuous monitoring mode
- Stuck package detection

**Usage:**
```bash
# Run once
python package_status_monitor.py

# Run continuously every 30 seconds
python package_status_monitor.py --continuous --interval 30

# Output as JSON
python package_status_monitor.py --output json

# Detailed breakdown
python package_status_monitor.py --detailed
```

### 2. `monitor-packages.sh` - Linux/macOS Wrapper

Convenient shell script wrapper for common monitoring tasks.

**Usage:**
```bash
# Make executable (first time only)
chmod +x monitor-packages.sh

# Run once
./monitor-packages.sh

# Watch continuously
./monitor-packages.sh watch

# JSON output
./monitor-packages.sh json

# Detailed breakdown
./monitor-packages.sh detailed
```

### 3. `monitor-packages.ps1` - PowerShell Wrapper

PowerShell wrapper for Windows systems.

**Usage:**
```powershell
# Run once
.\monitor-packages.ps1

# Watch continuously
.\monitor-packages.ps1 watch

# JSON output
.\monitor-packages.ps1 json

# Detailed breakdown
.\monitor-packages.ps1 detailed
```

### 4. `cron-package-monitor.sh` - Cron Job Script

Designed for regular execution via cron jobs with logging and alerting.

**Usage:**
```bash
# Make executable (first time only)
chmod +x cron-package-monitor.sh

# Add to crontab for every 5 minutes
*/5 * * * * /path/to/cron-package-monitor.sh

# Add to crontab for every hour with detailed output
0 * * * * /path/to/cron-package-monitor.sh --detailed
```

## Environment Variables

### Required
- `DATABASE_URL` - Database connection URL (e.g., `postgresql://user:pass@host/db`)

### Optional (for cron script)
- `LOG_FILE` - Log file path (default: `/tmp/package-monitor.log`)
- `ALERT_THRESHOLD` - Alert if stuck packages exceed this count (default: 10)
- `ALERT_EMAIL` - Email address for alerts (requires `mail` command)

## Package Statuses

The monitor tracks packages in the following statuses:

- **Checking Licence** 🔍 - Packages being validated for license compliance
- **Downloaded** ⬇️ - Packages successfully downloaded from npm registry
- **Security Scanning** 🔒 - Packages currently being scanned for vulnerabilities
- **Security Scanned** ✅ - Packages that have completed security scanning
- **Pending Approval** ⏳ - Packages waiting for manual approval
- **Approved** 👍 - Packages approved for publishing
- **Rejected** ❌ - Packages rejected during approval process
- **Published** 🚀 - Packages successfully published to internal registry

## Example Output

### Table Format
```
📊 Package Status Report - 2024-01-15T10:30:00
==================================================
🔍 Checking Licence        45
⬇️ Downloaded             23
🔒 Security Scanning       8
✅ Security Scanned        156
⏳ Pending Approval        12
👍 Approved                89
❌ Rejected                 3
📦 TOTAL                  336
==================================================
```

### JSON Format
```json
{
  "timestamp": "2024-01-15T10:30:00",
  "package_counts": {
    "Security Scanned": 156,
    "Approved": 89,
    "Checking Licence": 45,
    "Downloaded": 23,
    "Pending Approval": 12,
    "Security Scanning": 8,
    "Rejected": 3,
    "TOTAL": 336
  }
}
```

## Setting Up Regular Monitoring

### Using Cron (Linux/macOS)

1. Edit your crontab:
   ```bash
   crontab -e
   ```

2. Add monitoring entries:
   ```bash
   # Monitor every 5 minutes
   */5 * * * * /path/to/secure_package_manager/backend/scripts/cron-package-monitor.sh
   
   # Detailed report every hour
   0 * * * * /path/to/secure_package_manager/backend/scripts/cron-package-monitor.sh --detailed
   ```

3. Set environment variables in your shell profile:
   ```bash
   export DATABASE_URL="postgresql://user:pass@host/db"
   export LOG_FILE="/var/log/package-monitor.log"
   export ALERT_THRESHOLD=20
   export ALERT_EMAIL="admin@company.com"
   ```

### Using Windows Task Scheduler

1. Open Task Scheduler
2. Create a new task
3. Set trigger (e.g., every 5 minutes)
4. Set action to run PowerShell script:
   ```powershell
   $env:DATABASE_URL = "postgresql://user:pass@host/db"
   & "C:\path\to\secure_package_manager\backend\scripts\monitor-packages.ps1"
   ```

## Troubleshooting

### Common Issues

1. **DATABASE_URL not set**
   - Ensure the environment variable is properly set
   - Check the connection string format

2. **Permission denied (Linux/macOS)**
   - Make scripts executable: `chmod +x *.sh`

3. **Python import errors**
   - Ensure you're running from the backend directory
   - Check that all dependencies are installed

4. **Database connection errors**
   - Verify database is running and accessible
   - Check network connectivity
   - Validate credentials in DATABASE_URL

### Log Files

- Cron script logs to `/tmp/package-monitor.log` by default
- Use `tail -f /tmp/package-monitor.log` to monitor logs in real-time
- Adjust `LOG_FILE` environment variable to change log location

## Integration with Monitoring Systems

The JSON output format makes it easy to integrate with monitoring systems:

- **Prometheus**: Use JSON output to create custom metrics
- **Grafana**: Import JSON data for dashboards
- **ELK Stack**: Parse JSON logs for analysis
- **Custom Alerts**: Parse JSON output for custom alerting logic
