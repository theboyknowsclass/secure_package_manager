"""Approval Service.

Handles approval workflow for packages. This service is used
by both the API (for immediate processing) and workers (for background processing).

This service works with entity-based operations structure and focuses purely on business logic.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ApprovalService:
    """Service for handling package approval workflow.

    This service handles the business logic of package approval transitions and
    status management. It works with database operations passed in from the caller
    (worker or API) to maintain separation of concerns.
    """

    def __init__(self) -> None:
        """Initialize the approval service."""
        self.logger = logger

    def process_security_scanned_packages(
        self, packages: List[Any], ops: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process packages that are Security Scanned and ready for approval.

        Args:
            packages: List of packages to process
            ops: Dictionary of database operations instances

        Returns:
            Dict with processing results
        """
        try:
            processed_count = 0
            for package in packages:
                if self._transition_to_pending_approval(package, ops):
                    processed_count += 1

            return {
                "success": True,
                "processed_count": processed_count,
                "total_packages": len(packages)
            }
        except Exception as e:
            self.logger.error(f"Error processing security scanned packages: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "processed_count": 0,
                "total_packages": len(packages)
            }

    def get_stuck_packages(
        self, stuck_threshold: datetime, ops: Dict[str, Any]
    ) -> List[Any]:
        """Get packages that have been stuck in Security Scanned state too long.

        Args:
            stuck_threshold: DateTime threshold for considering packages stuck
            ops: Dictionary of database operations instances

        Returns:
            List of stuck packages
        """
        try:
            # Use operations to get stuck packages
            stuck_packages = ops.package.get_stuck_packages_in_security_scanned(
                stuck_threshold
            )
            return stuck_packages
        except Exception as e:
            self.logger.error(f"Error getting stuck packages: {str(e)}")
            return []

    def refresh_stuck_packages(
        self, stuck_packages: List[Any], ops: Dict[str, Any]
    ) -> None:
        """Refresh timestamp for stuck packages to avoid constant reprocessing.

        Args:
            stuck_packages: List of stuck packages to refresh
            ops: Dictionary of database operations instances
        """
        for package in stuck_packages:
            try:
                if package.package_status:
                    ops.package_status.refresh_package_timestamp(package.id)
                    self.logger.debug(
                        f"Refreshed timestamp for stuck package {package.name}@{package.version}"
                    )
            except Exception as e:
                self.logger.error(
                    f"Error refreshing stuck package {package.name}@{package.version}: {str(e)}"
                )

    def get_approval_statistics(self, ops: Dict[str, Any]) -> Dict[str, Any]:
        """Get current approval statistics.

        Args:
            ops: Dictionary of database operations instances

        Returns:
            Dict with approval statistics
        """
        try:
            # Get package counts by status
            security_scanned_count = ops.package.count_packages_by_status("Security Scanned")
            pending_approval_count = ops.package.count_packages_by_status("Pending Approval")
            approved_count = ops.package.count_packages_by_status("Approved")

            return {
                "security_scanned_packages": security_scanned_count,
                "pending_approval_packages": pending_approval_count,
                "approved_packages": approved_count,
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"Error getting approval statistics: {str(e)}")
            return {"error": str(e)}

    def _transition_to_pending_approval(
        self, package: Any, ops: Dict[str, Any]
    ) -> bool:
        """Transition a package from Security Scanned to Pending Approval.

        Args:
            package: Package to transition
            ops: Dictionary of database operations instances

        Returns:
            True if transition was successful, False otherwise
        """
        try:
            if package.package_status and package.package_status.status == "Security Scanned":
                ops.package_status.update_status(
                    package.id, "Pending Approval"
                )
                self.logger.debug(
                    f"Transitioned package {package.name}@{package.version} to Pending Approval"
                )
                return True
            return False
        except Exception as e:
            self.logger.error(
                f"Error transitioning package {package.name}@{package.version}: {str(e)}"
            )
            return False
