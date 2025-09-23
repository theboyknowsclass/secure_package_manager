#!/usr/bin/env python3
"""
Package Status Monitoring Script

This script monitors package counts by status in the database and can be run
on a regular basis (e.g., via cron job) to track system health and processing progress.

Usage:
    python package_status_monitor.py [--interval SECONDS] [--continuous] [--output FORMAT]

Examples:
    # Run once and exit
    python package_status_monitor.py

    # Run continuously every 30 seconds
    python package_status_monitor.py --continuous --interval 30

    # Output as JSON for logging systems
    python package_status_monitor.py --output json

    # Run with custom database URL
    DATABASE_URL=postgresql://user:pass@host/db python package_status_monitor.py
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database.models import PackageStatus
from database.session_helper import SessionHelper
from sqlalchemy import func, text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class PackageStatusMonitor:
    """Monitor package counts by status."""

    def __init__(self):
        """Initialize the monitor."""
        self.database_url = os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required")

    def get_package_counts_by_status(self) -> Dict[str, int]:
        """Get package counts grouped by status.

        Returns:
            Dictionary mapping status names to package counts
        """
        try:
            with SessionHelper.get_session() as db:
                # Use raw SQL for better performance on large datasets
                query = text(
                    """
                    SELECT status, COUNT(*) as count
                    FROM package_status
                    GROUP BY status
                    ORDER BY count DESC
                """
                )

                result = db.session.execute(query)
                counts = {row.status: row.count for row in result}

                # Also get total count
                total_query = text(
                    "SELECT COUNT(*) as total FROM package_status"
                )
                total_result = db.session.execute(total_query)
                total_count = total_result.scalar()

                counts["TOTAL"] = total_count

                return counts

        except Exception as e:
            logger.error(f"Error getting package counts: {str(e)}")
            return {}

    def get_detailed_status_breakdown(self) -> Dict[str, any]:
        """Get detailed breakdown of package statuses with additional metrics.

        Returns:
            Dictionary with detailed status information
        """
        try:
            with SessionHelper.get_session() as db:
                # Get counts by status
                status_query = text(
                    """
                    SELECT 
                        status,
                        COUNT(*) as count,
                        MIN(created_at) as oldest_created,
                        MAX(updated_at) as newest_updated
                    FROM package_status
                    GROUP BY status
                    ORDER BY count DESC
                """
                )

                result = db.session.execute(status_query)
                status_breakdown = {}

                for row in result:
                    status_breakdown[row.status] = {
                        "count": row.count,
                        "oldest_created": (
                            row.oldest_created.isoformat()
                            if row.oldest_created
                            else None
                        ),
                        "newest_updated": (
                            row.newest_updated.isoformat()
                            if row.newest_updated
                            else None
                        ),
                    }

                # Get total counts
                total_query = text(
                    "SELECT COUNT(*) as total FROM package_status"
                )
                total_count = db.session.execute(total_query).scalar()

                # Get stuck packages (updated more than 1 hour ago)
                stuck_query = text(
                    """
                    SELECT status, COUNT(*) as count
                    FROM package_status
                    WHERE updated_at < NOW() - INTERVAL '1 hour'
                    GROUP BY status
                """
                )

                stuck_result = db.session.execute(stuck_query)
                stuck_packages = {
                    row.status: row.count for row in stuck_result
                }

                return {
                    "timestamp": datetime.utcnow().isoformat(),
                    "total_packages": total_count,
                    "status_breakdown": status_breakdown,
                    "stuck_packages": stuck_packages,
                    "summary": {
                        "total_statuses": len(status_breakdown),
                        "has_stuck_packages": sum(stuck_packages.values()) > 0,
                        "stuck_count": sum(stuck_packages.values()),
                    },
                }

        except Exception as e:
            logger.error(f"Error getting detailed status breakdown: {str(e)}")
            return {}

    def print_status_report(
        self, counts: Dict[str, int], format_type: str = "table"
    ) -> None:
        """Print status report in the specified format.

        Args:
            counts: Dictionary of status counts
            format_type: Output format ('table', 'json', 'csv')
        """
        timestamp = datetime.utcnow().isoformat()

        if format_type == "json":
            report = {"timestamp": timestamp, "package_counts": counts}
            logger.info(json.dumps(report, indent=2))

        elif format_type == "csv":
            logger.info(f"timestamp,status,count")
            for status, count in counts.items():
                logger.info(f"{timestamp},{status},{count}")

        else:  # table format
            logger.info(f"\n📊 Package Status Report - {timestamp}")
            logger.info("=" * 50)

            # Sort by count (descending) but put TOTAL at the end
            sorted_items = sorted(
                [(k, v) for k, v in counts.items() if k != "TOTAL"],
                key=lambda x: x[1],
                reverse=True,
            )

            if "TOTAL" in counts:
                sorted_items.append(("TOTAL", counts["TOTAL"]))

            for status, count in sorted_items:
                # Add emoji indicators for different statuses
                emoji = self._get_status_emoji(status)
                logger.info(f"{emoji} {status:<20} {count:>8}")

            logger.info("=" * 50)

    def _get_status_emoji(self, status: str) -> str:
        """Get emoji for status display."""
        emoji_map = {
            "Checking Licence": "🔍",
            "Downloaded": "⬇️",
            "Security Scanning": "🔒",
            "Security Scanned": "✅",
            "Pending Approval": "⏳",
            "Approved": "👍",
            "Rejected": "❌",
            "Published": "🚀",
            "TOTAL": "📦",
        }
        return emoji_map.get(status, "📋")

    def run_once(self, format_type: str = "table") -> None:
        """Run the monitor once and print results."""
        logger.info("Running package status monitor...")

        counts = self.get_package_counts_by_status()
        if counts:
            self.print_status_report(counts, format_type)
        else:
            logger.error("Failed to get package counts")
            sys.exit(1)

    def run_continuous(
        self, interval: int = 60, format_type: str = "table"
    ) -> None:
        """Run the monitor continuously at specified intervals.

        Args:
            interval: Seconds between runs
            format_type: Output format
        """
        logger.info(f"Starting continuous monitoring (interval: {interval}s)")

        try:
            while True:
                # Clear screen for better readability (optional)
                if format_type == "table":
                    os.system("clear" if os.name == "posix" else "cls")

                self.run_once(format_type)

                if format_type == "table":
                    logger.info(
                        f"\n⏰ Next update in {interval} seconds... (Ctrl+C to stop)"
                    )

                time.sleep(interval)

        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
        except Exception as e:
            logger.error(f"Error in continuous monitoring: {str(e)}")
            sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Monitor package counts by status",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Run once with table output
  %(prog)s --continuous --interval 30 # Run every 30 seconds
  %(prog)s --output json              # Output as JSON
  %(prog)s --detailed                 # Show detailed breakdown
        """,
    )

    parser.add_argument(
        "--continuous",
        "-c",
        action="store_true",
        help="Run continuously instead of once",
    )

    parser.add_argument(
        "--interval",
        "-i",
        type=int,
        default=60,
        help="Interval in seconds for continuous mode (default: 60)",
    )

    parser.add_argument(
        "--output",
        "-o",
        choices=["table", "json", "csv"],
        default="table",
        help="Output format (default: table)",
    )

    parser.add_argument(
        "--detailed",
        "-d",
        action="store_true",
        help="Show detailed breakdown with timestamps and stuck packages",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        monitor = PackageStatusMonitor()

        if args.detailed:
            # Show detailed breakdown
            breakdown = monitor.get_detailed_status_breakdown()
            if breakdown:
                if args.output == "json":
                    logger.info(json.dumps(breakdown, indent=2))
                else:
                    logger.info(
                        f"\n📊 Detailed Package Status Report - {breakdown['timestamp']}"
                    )
                    logger.info("=" * 60)
                    logger.info(f"Total Packages: {breakdown['total_packages']}")
                    logger.info(
                        f"Status Types: {breakdown['summary']['total_statuses']}"
                    )
                    logger.info(
                        f"Stuck Packages: {breakdown['summary']['stuck_count']}"
                    )
                    logger.info("\nStatus Breakdown:")
                    for status, info in breakdown["status_breakdown"].items():
                        emoji = monitor._get_status_emoji(status)
                        logger.info(f"{emoji} {status:<20} {info['count']:>8}")
                        if info["oldest_created"]:
                            logger.info(f"   Oldest: {info['oldest_created']}")
                        if info["newest_updated"]:
                            logger.info(f"   Newest: {info['newest_updated']}")
                        logger.info("")
        else:
            # Regular status counts
            if args.continuous:
                monitor.run_continuous(args.interval, args.output)
            else:
                monitor.run_once(args.output)

    except Exception as e:
        logger.error(f"Error running monitor: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
