"""Approval Service.

Handles approval workflow for packages. This service manages its own database sessions
and operations, following the service-first architecture pattern.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

from database.operations.package_operations import PackageOperations
from database.operations.package_status_operations import PackageStatusOperations
from database.session_helper import SessionHelper

logger = logging.getLogger(__name__)


class ApprovalService:
    """Service for handling package approval workflow.

    This service manages its own database sessions and operations,
    following the service-first architecture pattern.
    """

    def __init__(self) -> None:
        """Initialize the approval service."""
        self.logger = logger

    def process_security_scanned_packages(
        self, max_packages: int = 50
    ) -> Dict[str, Any]:
        """Process packages that are Security Scanned and ready for approval.

        Args:
            max_packages: Maximum number of packages to process

        Returns:
            Dict with processing results
        """
        try:
            with SessionHelper.get_session() as db:
                # Initialize operations
                package_ops = PackageOperations(db.session)
                status_ops = PackageStatusOperations(db.session)
                
                # Find packages that need approval transitions
                security_scanned_packages = package_ops.get_by_status("Security Scanned")
                
                # Limit the number of packages processed
                limited_packages = security_scanned_packages[:max_packages]

                if not limited_packages:
                    return {
                        "success": True,
                        "processed_count": 0,
                        "total_packages": 0
                    }

                processed_count = 0
                for package in limited_packages:
                    if self._transition_to_pending_approval(package, status_ops):
                        processed_count += 1

                db.commit()

                return {
                    "success": True,
                    "processed_count": processed_count,
                    "total_packages": len(limited_packages)
                }
        except Exception as e:
            self.logger.error(f"Error processing security scanned packages: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "processed_count": 0,
                "total_packages": 0
            }

    def get_approval_statistics(self) -> Dict[str, Any]:
        """Get current approval statistics.

        Returns:
            Dict with approval statistics
        """
        try:
            with SessionHelper.get_session() as db:
                package_ops = PackageOperations(db.session)
                
                # Get package counts by status
                security_scanned_count = package_ops.count_packages_by_status("Security Scanned")
                pending_approval_count = package_ops.count_packages_by_status("Pending Approval")
                approved_count = package_ops.count_packages_by_status("Approved")

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
        self, package: Any, status_ops: PackageStatusOperations
    ) -> bool:
        """Transition a package from Security Scanned to Pending Approval.

        Args:
            package: Package to transition
            status_ops: Package status operations instance

        Returns:
            True if transition was successful, False otherwise
        """
        try:
            if package.package_status and package.package_status.status == "Security Scanned":
                status_ops.go_to_next_stage(package.id)
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
