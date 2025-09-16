"""
Package Request Status Manager

Handles the complex logic for determining and updating package request statuses
based on the states of individual packages within the request.
"""

import logging
from typing import Any, Dict, Optional

from models import Package, PackageRequest, db

logger = logging.getLogger(__name__)


class PackageRequestStatusManager:
    """Manages package request status updates based on package states"""

    def __init__(self, db_session: Any = None) -> None:
        self.db = db_session or db

    def update_request_status(self, request_id: int) -> Optional[str]:
        """
        Determine and update the request status based on package states

        Args:
            request_id: The ID of the package request to update

        Returns:
            The new status if updated, None if no change needed
        """
        package_request = PackageRequest.query.get(request_id)
        if not package_request:
            logger.warning(f"Package request {request_id} not found")
            return None

        new_status = self._determine_request_status(request_id, package_request)

        if new_status != package_request.status:
            package_request.status = new_status
            self.db.session.commit()
            logger.info(
                f"Updated request {request_id} status: {package_request.status} -> {new_status}"
            )
            return new_status

        return None

    def _determine_request_status(
        self, request_id: int, package_request: PackageRequest
    ) -> str:
        """
        Determine the appropriate status for a package request based on package states

        Args:
            request_id: The ID of the package request
            package_request: The package request object

        Returns:
            The appropriate status string
        """
        counts = self._get_package_counts_by_status(request_id)

        # Rule 1: If there are still requested packages, keep processing
        if counts["requested"] > 0:
            return "processing"

        # Rule 2: If any packages failed validation, reject the entire request
        if counts["rejected"] > 0:
            return "rejected"

        # Rule 3: If all packages are pending approval, request is ready for approval
        if counts["pending_approval"] == package_request.total_packages:
            return "pending_approval"

        # Rule 4: If all packages completed security scan, request is complete
        if counts["security_scan_complete"] == package_request.total_packages:
            return "security_scan_complete"

        # Rule 5: If some packages are still processing, determine the stage
        if counts["processing"] > 0:
            return "performing_security_scan"

        # Rule 6: Default fallback - assume license check stage
        return "performing_licence_check"

    def _get_package_counts_by_status(self, request_id: int) -> Dict[str, int]:
        """
        Get counts of packages by status for a request

        Args:
            request_id: The ID of the package request

        Returns:
            Dictionary with status counts
        """
        return {
            "requested": Package.query.filter_by(
                package_request_id=request_id, status="requested"
            ).count(),
            "rejected": Package.query.filter_by(
                package_request_id=request_id, status="rejected"
            ).count(),
            "pending_approval": Package.query.filter_by(
                package_request_id=request_id, status="pending_approval"
            ).count(),
            "security_scan_complete": Package.query.filter_by(
                package_request_id=request_id, status="security_scan_complete"
            ).count(),
            "processing": Package.query.filter(
                Package.package_request_id == request_id,
                Package.status.in_(
                    [
                        "performing_licence_check",
                        "licence_check_complete",
                        "performing_security_scan",
                    ]
                ),
            ).count(),
        }

    def get_request_status_summary(self, request_id: int) -> Dict[str, Any]:
        """
        Get a summary of the request status and package counts

        Args:
            request_id: The ID of the package request

        Returns:
            Dictionary with status summary information
        """
        package_request = PackageRequest.query.get(request_id)
        if not package_request:
            return {"error": f"Request {request_id} not found"}

        counts = self._get_package_counts_by_status(request_id)

        return {
            "request_id": request_id,
            "current_status": package_request.status,
            "total_packages": package_request.total_packages,
            "package_counts": counts,
            "completion_percentage": self._calculate_completion_percentage(
                counts, package_request.total_packages
            ),
        }

    def _calculate_completion_percentage(
        self, counts: Dict[str, int], total_packages: int
    ) -> float:
        """
        Calculate the completion percentage of a request

        Args:
            counts: Package counts by status
            total_packages: Total number of packages in the request

        Returns:
            Completion percentage (0.0 to 100.0)
        """
        if total_packages == 0:
            return 0.0

        completed_packages = (
            counts["pending_approval"]
            + counts["security_scan_complete"]
            + counts["rejected"]
        )

        return (completed_packages / total_packages) * 100.0
