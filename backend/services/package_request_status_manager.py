"""Package Request Status Manager.

Handles the complex logic for determining and updating package request
statuses based on the states of individual packages within the request.
"""

import logging
from typing import Any, Dict, List, Optional

from database.session_helper import SessionHelper
from database.operations.request_operations import RequestOperations
from database.operations.package_operations import PackageOperations
from database.models import Package, PackageStatus, Request, RequestPackage

logger = logging.getLogger(__name__)


class PackageRequestStatusManager:
    """Manages package request status updates based on package states."""

    def __init__(self, db_session: Any = None) -> None:
        self.db = db_session

    def update_request_status(self, request_id: int) -> Optional[str]:
        """
        Determine and update the request status based on package states
        Note: Request status is now derived from package statuses, not stored

        Args:
            request_id: The ID of the package request to update

        Returns:
            The new status if updated, None if no change needed
        """
        with SessionHelper.get_session() as db:
            request_ops = RequestOperations(db.session)
            request = request_ops.get_by_id(request_id)
        if not request:
            logger.warning(f"Request {request_id} not found")
            return None

        new_status = self._determine_request_status(request_id, request)

        # Since request status is derived, we don't store it
        # Just return the calculated status for logging/monitoring
        logger.info(f"Request {request_id} status: {new_status}")
        return new_status

    def _determine_request_status(
        self, request_id: int, request: Request
    ) -> str:
        """Determine the appropriate status for a package request based on
        package states.

        Args:
            request_id: The ID of the package request
            request: The request object

        Returns:
            The appropriate status string
        """
        counts = self._get_package_counts_by_status(request_id)
        total_packages = counts["total"]

        if total_packages == 0:
            return "no_packages"

        # Rule 1: If there are still early-stage packages, keep processing
        if counts["Checking Licence"] > 0:
            return "processing"

        # Rule 3: If all packages are pending approval, request is ready for
        # approval
        if counts["Pending Approval"] == total_packages:
            return "pending_approval"

        # Rule 4: If all packages are approved, request is complete
        if counts["Approved"] == total_packages:
            return "approved"

        # Rule 5: If some packages are still processing, determine the stage
        processing_count = (
            counts["Checking Licence"]
            + counts["Downloading"]
            + counts["Security Scanning"]
            + counts["Licence Checked"]
            + counts["Downloaded"]
            + counts["Security Scanned"]
        )
        if processing_count > 0:
            return "processing"

        # Rule 6: Default fallback
        return "processing"

    def _get_package_counts_by_status(self, request_id: int) -> Dict[str, int]:
        """Get counts of packages by status for a request.

        Args:
            request_id: The ID of the package request

        Returns:
            Dictionary with status counts
        """
        # Get all packages for this request through the many-to-many
        # relationship
        with SessionHelper.get_session() as db:
            request_ops = RequestOperations(db.session)
            request_obj = request_ops.get_by_id(request_id)
            if not request_obj:
                return {"total": 0, "Submitted": 0, "Parsed": 0, "Checking Licence": 0, 
                       "Downloading": 0, "Security Scanning": 0, "Pending Approval": 0, 
                       "Approved": 0, "Rejected": 0}
            
            # Get packages for this request using the relationship
            request_packages = request_obj.request_packages if hasattr(request_obj, 'request_packages') else []
            logger.info(f"request_packages type: {type(request_packages)}")
            logger.info(f"request_packages length: {len(request_packages) if request_packages else 'None'}")
            if request_packages:
                logger.info(f"First request_package type: {type(request_packages[0])}")
                logger.info(f"First request_package: {request_packages[0]}")
            
            # Build packages list safely
            packages = []
            for rp in request_packages:
                try:
                    logger.info(f"Processing rp type: {type(rp)}, rp: {rp}")
                    if hasattr(rp, 'package') and rp.package:
                        packages.append(rp.package)
                    elif hasattr(rp, 'id') and hasattr(rp, 'name'):  # This might be a Package object directly
                        packages.append(rp)
                    else:
                        logger.warning(f"Unknown request_package type: {type(rp)}")
                except Exception as e:
                    logger.error(f"Error processing request_package: {e}")
                    logger.error(f"rp type: {type(rp)}, rp: {rp}")
                    continue
            
            logger.info(f"Final packages list length: {len(packages)}")
            if packages:
                logger.info(f"First package type: {type(packages[0])}")

            counts = {
                "total": len(packages),
                "Submitted": 0,
                "Parsed": 0,
                "Checking Licence": 0,
                "Licence Checked": 0,
                "Downloading": 0,
                "Downloaded": 0,
                "Security Scanning": 0,
                "Security Scanned": 0,
                "Pending Approval": 0,
                "Approved": 0,
                "Rejected": 0,
            }

            for package in packages:
                if package.package_status:
                    status = package.package_status.status
                    if status in counts:
                        counts[status] += 1
                    else:
                        # Handle unknown statuses
                        counts["Submitted"] += 1
                else:
                    # Package without status is considered submitted
                    counts["Submitted"] += 1

        return counts

    def get_request_status_summary(self, request_id: int) -> Dict[str, Any]:
        """Get a summary of the request status and package counts.

        Args:
            request_id: The ID of the package request

        Returns:
            Dictionary with status summary information
        """
        logger.info(f"get_request_status_summary called for request_id: {request_id}")
        with SessionHelper.get_session() as db:
            request_ops = RequestOperations(db.session)
            request = request_ops.get_by_id(request_id)
        if not request:
            return {"error": f"Request {request_id} not found"}

        logger.info(f"Request found: {request.id}, calling _get_package_counts_by_status")
        counts = self._get_package_counts_by_status(request_id)
        logger.info(f"Package counts retrieved: {counts}")
        current_status = self._determine_request_status(request_id, request)

        return {
            "request_id": request_id,
            "current_status": current_status,
            "total_packages": counts["total"],
            "package_counts": counts,
            "completion_percentage": self._calculate_completion_percentage(
                counts, counts["total"]
            ),
        }

    def _calculate_completion_percentage(
        self, counts: Dict[str, int], total_packages: int
    ) -> float:
        """Calculate the completion percentage of a request.

        Args:
            counts: Package counts by status
            total_packages: Total number of packages in the request

        Returns:
            Completion percentage (0.0 to 100.0)
        """
        if total_packages == 0:
            return 0.0

        completed_packages = (
            counts["Security Scanned"]
            + counts["Pending Approval"]
            + counts["Approved"]
            + counts["Rejected"]
        )

        return (completed_packages / total_packages) * 100.0

    def get_packages_by_status(
        self, request_id: int, status: str
    ) -> List[Package]:
        """Get all packages for a request with a specific status.

        Args:
            request_id: The ID of the package request
            status: The status to filter by

        Returns:
            List of packages with the specified status
        """
        with SessionHelper.get_session() as db:
            request_ops = RequestOperations(db.session)
            request_obj = request_ops.get_by_id(request_id)
            if not request_obj:
                return []
            
            # Get packages for this request with specific status - using relationship
            request_packages = request_obj.request_packages if hasattr(request_obj, 'request_packages') else []
            packages = [
                rp.package for rp in request_packages 
                if rp.package and rp.package.package_status and rp.package.package_status.status == status
            ]

            return packages

    def get_packages_needing_approval(self, request_id: int) -> List[Package]:
        """Get all packages for a request that are pending approval.

        Args:
            request_id: The ID of the package request

        Returns:
            List of packages pending approval
        """
        return self.get_packages_by_status(request_id, "Pending Approval")

    def get_packages_by_security_scan_status(
        self, request_id: int, scan_status: str
    ) -> List[Package]:
        """Get all packages for a request with a specific security scan status.

        Args:
            request_id: The ID of the package request
            scan_status: The security scan status to filter by

        Returns:
            List of packages with the specified security scan status
        """
        with SessionHelper.get_session() as db:
            request_ops = RequestOperations(db.session)
            request_obj = request_ops.get_by_id(request_id)
            if not request_obj:
                return []
            
            # Get packages for this request with specific security scan status - using relationship
            request_packages = request_obj.request_packages if hasattr(request_obj, 'request_packages') else []
            packages = [
                rp.package for rp in request_packages 
                if rp.package and rp.package.package_status and rp.package.package_status.security_scan_status == scan_status
            ]

            return packages
