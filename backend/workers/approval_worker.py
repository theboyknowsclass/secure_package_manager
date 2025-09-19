"""Approval Worker.

Transitions packages from Security Scanned to Pending Approval status.
This is a lightweight worker that can be extended for auto-approval
logic in the future.
"""

import logging
import os
from datetime import datetime, timedelta

from database.models import Package, PackageStatus
from database.service import DatabaseService
from workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class ApprovalWorker(BaseWorker):
    """Background worker for transitioning packages to pending approval."""

    WORKER_TYPE = "approval_worker"

    def __init__(self, sleep_interval: int = 30):
        super().__init__("ApprovalWorker", sleep_interval)
        self.max_packages_per_cycle = (
            50  # Can handle many packages since it's just status updates
        )
        self.stuck_package_timeout = timedelta(
            minutes=10
        )  # Short timeout since this should be fast
        self.db_service = DatabaseService(
            database_url=os.getenv(
                "DATABASE_URL",
                "postgresql://user:password@localhost/secure_package_manager",
            ),
            echo=False,
        )

    def initialize(self) -> None:
        """Initialize the approval worker."""
        logger.info("Initializing ApprovalWorker...")

    def process_cycle(self) -> None:
        """Process one cycle of approval work."""
        try:
            self._handle_stuck_packages()
            self._process_security_scanned_packages()
        except Exception as e:
            logger.error(f"Approval cycle error: {str(e)}", exc_info=True)

    def _handle_stuck_packages(self) -> None:
        """Handle packages that have been stuck in Security Scanned state too
        long."""
        try:
            stuck_threshold = datetime.utcnow() - self.stuck_package_timeout

            with self.db_service.get_session() as session:
                # Find packages that have been Security Scanned for too long
                # This shouldn't happen often, but helps with edge cases
                stuck_packages = (
                    session.query(Package)
                    .join(PackageStatus)
                    .filter(
                        PackageStatus.status == "Security Scanned",
                        PackageStatus.updated_at < stuck_threshold,
                    )
                    .all()
                )

                if stuck_packages:
                    logger.warning(
                        f"Found {
                            len(stuck_packages)} packages stuck in Security Scanned state")
                    # Just refresh their timestamp to avoid constant
                    # reprocessing
                    for package in stuck_packages:
                        if package.package_status:
                            package.package_status.updated_at = (
                                datetime.utcnow()
                            )
                    session.commit()

        except Exception as e:
            logger.error(
                f"Error handling stuck packages: {str(e)}", exc_info=True
            )

    def _process_security_scanned_packages(self) -> None:
        """Process packages that are Security Scanned and ready for
        approval."""
        try:
            with self.db_service.get_session() as session:
                # Get packages that are Security Scanned and ready to move to
                # Pending Approval
                security_scanned_packages = (
                    session.query(Package)
                    .join(PackageStatus)
                    .filter(PackageStatus.status == "Security Scanned")
                    .limit(self.max_packages_per_cycle)
                    .all()
                )

                if not security_scanned_packages:
                    logger.info(
                        "ApprovalWorker heartbeat: No packages found for approval transition"
                    )
                    return

                logger.info(
                    f"Transitioning {
                        len(security_scanned_packages)} packages from Security Scanned to Pending Approval"
                )

                # Batch update all packages to Pending Approval
                for package in security_scanned_packages:
                    if package.package_status:
                        package.package_status.status = "Pending Approval"
                        package.package_status.updated_at = datetime.utcnow()

                session.commit()
                logger.info(
                    f"Successfully transitioned {
                        len(security_scanned_packages)} packages to Pending Approval")

        except Exception as e:
            logger.error(
                f"Error processing security scanned packages: {str(e)}",
                exc_info=True,
            )

    def get_approval_stats(self) -> dict:
        """Get current approval statistics."""
        try:
            with self.db_service.get_session() as session:
                # Count packages by status
                security_scanned_count = (
                    session.query(Package)
                    .join(PackageStatus)
                    .filter(PackageStatus.status == "Security Scanned")
                    .count()
                )

                pending_approval_count = (
                    session.query(Package)
                    .join(PackageStatus)
                    .filter(PackageStatus.status == "Pending Approval")
                    .count()
                )

                approved_count = (
                    session.query(Package)
                    .join(PackageStatus)
                    .filter(PackageStatus.status == "Approved")
                    .count()
                )

                return {
                    "worker_status": self.get_worker_status(),
                    "security_scanned_packages": security_scanned_count,
                    "pending_approval_packages": pending_approval_count,
                    "approved_packages": approved_count,
                    "timestamp": datetime.utcnow().isoformat(),
                }

        except Exception as e:
            logger.error(f"Error getting approval stats: {str(e)}")
            return {"error": str(e)}
