"""Approval Service.

Handles approval workflow for packages. This service separates database operations
from I/O work for optimal performance.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Tuple

from database.operations.package_operations import PackageOperations
from database.operations.package_status_operations import (
    PackageStatusOperations,
)
from database.session_helper import SessionHelper

logger = logging.getLogger(__name__)


class ApprovalService:
    """Service for handling package approval workflow.

    This service separates database operations from I/O work to minimize database session time.
    """

    def __init__(self) -> None:
        """Initialize the approval service."""
        self.logger = logger

    def process_security_scanned_packages(
        self, max_packages: int = 50
    ) -> Dict[str, Any]:
        """Process packages that are Security Scanned and ready for approval.

        This method separates database operations from I/O work:
        1. Get packages that need approval transitions (short DB session)
        2. Process approval logic (no DB session)
        3. Update database with results (short DB session)

        Args:
            max_packages: Maximum number of packages to process

        Returns:
            Dict with processing results
        """
        try:
            # Phase 1: Get package data (short DB session)
            packages_to_process = self._get_packages_for_approval(max_packages)
            if not packages_to_process:
                return {
                    "success": True,
                    "processed_count": 0,
                    "total_packages": 0,
                }

            # Phase 2: Process approval logic (no DB session)
            approval_results = self._perform_approval_batch(
                packages_to_process
            )

            # Phase 3: Update database (short DB session)
            return self._update_approval_results(approval_results)

        except Exception as e:
            self.logger.error(
                f"Error processing security scanned packages: {str(e)}"
            )
            return {
                "success": False,
                "error": str(e),
                "processed_count": 0,
                "total_packages": 0,
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
                security_scanned_count = package_ops.count_packages_by_status(
                    "Security Scanned"
                )
                pending_approval_count = package_ops.count_packages_by_status(
                    "Pending Approval"
                )
                approved_count = package_ops.count_packages_by_status(
                    "Approved"
                )

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
            if (
                package.package_status
                and package.package_status.status == "Security Scanned"
            ):
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

    def _get_packages_for_approval(self, max_packages: int) -> List[Any]:
        """Get packages that need approval transitions (short DB session)."""
        with SessionHelper.get_session() as db:
            package_ops = PackageOperations(db.session)
            return package_ops.get_by_status("Security Scanned")[:max_packages]

    def _perform_approval_batch(
        self, packages: List[Any]
    ) -> List[Tuple[Any, Dict[str, Any]]]:
        """Process approval logic without database sessions."""
        results = []
        for package in packages:
            # Simple approval logic - just mark as ready for approval
            results.append(
                (
                    package,
                    {
                        "status": "success",
                        "action": "transition_to_pending_approval",
                    },
                )
            )
        return results

    def _update_approval_results(
        self, approval_results: List[Tuple[Any, Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Update database with approval results (short DB session)."""
        processed_count = 0

        with SessionHelper.get_session() as db:
            package_ops = PackageOperations(db.session)
            status_ops = PackageStatusOperations(db.session)

            for package, result in approval_results:
                try:
                    # Verify package still needs processing (race condition protection)
                    current_package = package_ops.get_by_id(package.id)
                    if (
                        not current_package
                        or not current_package.package_status
                        or current_package.package_status.status
                        != "Security Scanned"
                    ):
                        continue

                    if result["status"] == "success":
                        status_ops.update_status(
                            package.id, "Pending Approval"
                        )
                        processed_count += 1

                except Exception as e:
                    self.logger.error(
                        f"Error updating package {package.name}@{package.version}: {str(e)}"
                    )

            db.commit()

        return {
            "success": True,
            "processed_count": processed_count,
            "total_packages": len(approval_results),
        }
