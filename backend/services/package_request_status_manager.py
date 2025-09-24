"""Package Request Status Manager.

Handles the complex logic for determining and updating package request
statuses based on the states of individual packages within the request.
"""

import logging
import os
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from database.models import Package, PackageStatus, Request, RequestPackage
from database.operations.package_operations import PackageOperations
from database.operations.request_operations import RequestOperations
from database.service import DatabaseService

logger = logging.getLogger(__name__)


class PackageRequestStatusManager:
    """Manages package request status updates based on package states."""

    def __init__(self, db_session: Any = None) -> None:
        """Initialize the status manager."""
        self.db = db_session
        self.database_url = os.getenv("DATABASE_URL", "")
        self.db_service = DatabaseService(self.database_url)

    def update_request_status(self, request_id: int) -> Optional[str]:
        """
        Determine and update the request status based on package states
        Note: Request status is now derived from package statuses, not stored

        Args:
            request_id: The ID of the package request to update

        Returns:
            The new status if updated, None if no change needed
        """
        with self.db_service.get_session() as session:
            request_ops = RequestOperations(session)
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
        from sqlalchemy import case, func

        # Use the existing session if available, otherwise create a new one
        if self.db:
            session = self.db
        else:
            with self.db_service.get_session() as session:
                return self._get_package_counts_by_status_with_session(
                    request_id, session
                )

        return self._get_package_counts_by_status_with_session(
            request_id, session
        )

    def _get_package_counts_by_status_with_session(
        self, request_id: int, session: Session
    ) -> Dict[str, int]:
        """Get package counts using a single optimized query."""
        from database.models import Package, PackageStatus, RequestPackage
        from sqlalchemy import case, func

        # Single query to get all package status counts for the request
        stmt = (
            session.query(
                func.count().label("total"),
                func.sum(
                    case((PackageStatus.status == "Submitted", 1), else_=0)
                ).label("submitted"),
                func.sum(
                    case((PackageStatus.status == "Parsed", 1), else_=0)
                ).label("parsed"),
                func.sum(
                    case(
                        (PackageStatus.status == "Checking Licence", 1),
                        else_=0,
                    )
                ).label("checking_licence"),
                func.sum(
                    case(
                        (PackageStatus.status == "Licence Checked", 1), else_=0
                    )
                ).label("licence_checked"),
                func.sum(
                    case((PackageStatus.status == "Downloading", 1), else_=0)
                ).label("downloading"),
                func.sum(
                    case((PackageStatus.status == "Downloaded", 1), else_=0)
                ).label("downloaded"),
                func.sum(
                    case(
                        (PackageStatus.status == "Security Scanning", 1),
                        else_=0,
                    )
                ).label("security_scanning"),
                func.sum(
                    case(
                        (PackageStatus.status == "Security Scanned", 1),
                        else_=0,
                    )
                ).label("security_scanned"),
                func.sum(
                    case(
                        (PackageStatus.status == "Pending Approval", 1),
                        else_=0,
                    )
                ).label("pending_approval"),
                func.sum(
                    case((PackageStatus.status == "Approved", 1), else_=0)
                ).label("approved"),
                func.sum(
                    case((PackageStatus.status == "Rejected", 1), else_=0)
                ).label("rejected"),
            )
            .select_from(RequestPackage)
            .join(Package, RequestPackage.package_id == Package.id)
            .outerjoin(PackageStatus, Package.id == PackageStatus.package_id)
            .where(RequestPackage.request_id == request_id)
        )

        result = session.execute(stmt).first()

        if not result or result.total is None:
            return {
                "total": 0,
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

        return {
            "total": result.total or 0,
            "Submitted": result.submitted or 0,
            "Parsed": result.parsed or 0,
            "Checking Licence": result.checking_licence or 0,
            "Licence Checked": result.licence_checked or 0,
            "Downloading": result.downloading or 0,
            "Downloaded": result.downloaded or 0,
            "Security Scanning": result.security_scanning or 0,
            "Security Scanned": result.security_scanned or 0,
            "Pending Approval": result.pending_approval or 0,
            "Approved": result.approved or 0,
            "Rejected": result.rejected or 0,
        }

    def get_request_status_summary(self, request_id: int) -> Dict[str, Any]:
        """Get a summary of the request status and package counts.

        Args:
            request_id: The ID of the package request

        Returns:
            Dictionary with status summary information
        """
        # Use the existing session if available, otherwise create a new one
        if self.db:
            session = self.db
            request_ops = RequestOperations(session)
            request = request_ops.get_by_id(request_id)
            if not request:
                return {"error": f"Request {request_id} not found"}

            counts = self._get_package_counts_by_status_with_session(
                request_id, session
            )
            current_status = self._determine_request_status(
                request_id, request
            )

            return {
                "request_id": request_id,
                "current_status": current_status,
                "total_packages": counts["total"],
                "package_counts": counts,
                "completion_percentage": self._calculate_completion_percentage(
                    counts, counts["total"]
                ),
            }
        else:
            with self.db_service.get_session() as session:
                request_ops = RequestOperations(session)
                request = request_ops.get_by_id(request_id)
                if not request:
                    return {"error": f"Request {request_id} not found"}

                counts = self._get_package_counts_by_status_with_session(
                    request_id, session
                )
                current_status = self._determine_request_status(
                    request_id, request
                )

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
        with self.db_service.get_session() as session:
            request_ops = RequestOperations(session)
            request_obj = request_ops.get_by_id(request_id)
            if not request_obj:
                return []

            # Get packages for this request with specific status - using relationship
            request_packages = (
                request_obj.request_packages
                if hasattr(request_obj, "request_packages")
                else []
            )
            packages = [
                rp.package
                for rp in request_packages
                if rp.package
                and rp.package.package_status
                and rp.package.package_status.status == status
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
        with self.db_service.get_session() as session:
            request_ops = RequestOperations(session)
            request_obj = request_ops.get_by_id(request_id)
            if not request_obj:
                return []

            # Get packages for this request with specific security scan status - using relationship
            request_packages = (
                request_obj.request_packages
                if hasattr(request_obj, "request_packages")
                else []
            )
            packages = [
                rp.package
                for rp in request_packages
                if rp.package
                and rp.package.package_status
                and rp.package.package_status.security_scan_status
                == scan_status
            ]

            return packages
