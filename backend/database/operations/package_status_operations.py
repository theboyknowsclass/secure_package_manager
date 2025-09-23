"""Database operations for PackageStatus entities."""

from datetime import datetime
from typing import Any, List, Optional, Type

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from ..models import PackageStatus
from .base_operations import BaseOperations


class PackageStatusOperations(BaseOperations):
    """Database operations for PackageStatus entities."""

    def get_by_package_id(self, package_id: int) -> Optional[PackageStatus]:
        """Get package status by package ID.

        Args:
            package_id: The ID of the package

        Returns:
            The package status if found, None otherwise
        """
        stmt = select(PackageStatus).where(
            PackageStatus.package_id == package_id
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def update_status(
        self, package_id: int, new_status: str, **kwargs: Any
    ) -> bool:
        """Update package status.

        Args:
            package_id: The ID of the package
            new_status: The new status to set
            **kwargs: Additional fields to update

        Returns:
            True if update was successful, False otherwise
        """
        status = self.get_by_package_id(package_id)
        if not status:
            return False

        old_status = status.status
        status.status = new_status
        status.updated_at = datetime.utcnow()

        # Update any additional fields
        for key, value in kwargs.items():
            if hasattr(status, key):
                setattr(status, key, value)

        return True

    def batch_update_status(
        self, package_ids: List[int], new_status: str, **kwargs: Any
    ) -> int:
        """Update status for multiple packages.

        Args:
            package_ids: List of package IDs to update
            new_status: The new status to set
            **kwargs: Additional fields to update

        Returns:
            Number of packages updated
        """
        updated_count = (
            self.session.query(PackageStatus)
            .filter(PackageStatus.package_id.in_(package_ids))
            .update(
                {
                    PackageStatus.status: new_status,
                    PackageStatus.updated_at: datetime.utcnow(),
                    **kwargs,
                },
                synchronize_session=False,
            )
        )

        return updated_count

    def get_by_status(self, status: str) -> List[PackageStatus]:
        """Get all package statuses with specific status.

        Args:
            status: The status to filter by

        Returns:
            List of package statuses with the specified status
        """
        stmt = select(PackageStatus).where(PackageStatus.status == status)
        return list(self.session.execute(stmt).scalars().all())

    def get_stuck_statuses(
        self, timeout_minutes: int, statuses: List[str]
    ) -> List[PackageStatus]:
        """Get stuck package statuses.

        Args:
            timeout_minutes: Number of minutes after which a status is considered stuck
            statuses: List of statuses to check for stuck packages

        Returns:
            List of stuck package statuses
        """
        from datetime import timedelta

        stuck_threshold = datetime.utcnow() - timedelta(
            minutes=timeout_minutes
        )

        stmt = select(PackageStatus).where(
            and_(
                PackageStatus.status.in_(statuses),
                PackageStatus.updated_at < stuck_threshold,
            )
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_all(self) -> List[PackageStatus]:
        """Get all package statuses.

        Returns:
            List of all package statuses
        """
        return super().get_all(PackageStatus)

    def update_package_publish_status(
        self, package_id: int, publish_status: str
    ) -> bool:
        """Update package publish status.

        Args:
            package_id: The ID of the package
            publish_status: The new publish status

        Returns:
            True if update was successful, False otherwise
        """
        status = self.get_by_package_id(package_id)
        if not status:
            return False

        status.publish_status = publish_status
        status.updated_at = datetime.utcnow()
        return True

    def mark_package_published(self, package_id: int) -> bool:
        """Mark package as published successfully.

        Args:
            package_id: The ID of the package

        Returns:
            True if update was successful, False otherwise
        """
        status = self.get_by_package_id(package_id)
        if not status:
            return False

        status.publish_status = "published"
        status.published_at = datetime.utcnow()
        status.updated_at = datetime.utcnow()
        return True

    def mark_package_publish_failed(
        self, package_id: int, error_message: str
    ) -> bool:
        """Mark package as publish failed.

        Args:
            package_id: The ID of the package
            error_message: Error message

        Returns:
            True if update was successful, False otherwise
        """
        status = self.get_by_package_id(package_id)
        if not status:
            return False

        status.publish_status = "failed"
        status.updated_at = datetime.utcnow()
        return True

    def refresh_package_timestamp(self, package_id: int) -> bool:
        """Refresh package timestamp to avoid constant reprocessing.

        Args:
            package_id: The ID of the package

        Returns:
            True if update was successful, False otherwise
        """
        status = self.get_by_package_id(package_id)
        if not status:
            return False

        status.updated_at = datetime.utcnow()
        return True

    def update_security_scan_status(
        self, package_id: int, scan_status: str
    ) -> bool:
        """Update package security scan status.

        Args:
            package_id: The ID of the package
            scan_status: The new security scan status

        Returns:
            True if update was successful, False otherwise
        """
        status = self.get_by_package_id(package_id)
        if not status:
            return False

        status.security_scan_status = scan_status
        status.updated_at = datetime.utcnow()
        return True

    def update_security_score(
        self, package_id: int, security_score: float
    ) -> bool:
        """Update package security score.

        Args:
            package_id: The ID of the package
            security_score: The new security score

        Returns:
            True if update was successful, False otherwise
        """
        status = self.get_by_package_id(package_id)
        if not status:
            return False

        status.security_score = security_score
        status.updated_at = datetime.utcnow()
        return True

    def update_license_info(
        self, package_id: int, license_score: int, license_status: str
    ) -> bool:
        """Update package license information.

        Args:
            package_id: The ID of the package
            license_score: The license score (0-100)
            license_status: The license status (e.g., 'always_allowed', 'allowed', 'avoid', 'blocked')

        Returns:
            True if update was successful, False otherwise
        """
        status = self.get_by_package_id(package_id)
        if not status:
            return False

        status.license_score = license_score
        status.license_status = (
            license_status  # Use exact value to match database constraints
        )
        status.updated_at = datetime.utcnow()
        return True

    def update_download_info(
        self,
        package_id: int,
        cache_path: Optional[str] = None,
        file_size: Optional[int] = None,
        checksum: Optional[str] = None,
    ) -> bool:
        """Update package download-related fields in a single operation.

        Args:
            package_id: The ID of the package
            cache_path: The actual cache directory path where package is stored (optional)
            file_size: The size of the downloaded/extracted package (optional)
            checksum: The checksum of the downloaded package (optional)

        Returns:
            True if update was successful, False otherwise
        """
        status = self.get_by_package_id(package_id)
        if not status:
            return False

        if cache_path is not None:
            status.cache_path = cache_path
        if file_size is not None:
            status.file_size = file_size
        if checksum is not None:
            status.checksum = checksum

        status.updated_at = datetime.utcnow()
        return True

    def update_security_scan_info(
        self,
        package_id: int,
        security_score: Optional[int] = None,
        security_scan_status: Optional[str] = None,
    ) -> bool:
        """Update package security scan-related fields in a single operation.

        Args:
            package_id: The ID of the package
            security_score: The security score 0-100 (optional)
            security_scan_status: The security scan status (optional)

        Returns:
            True if update was successful, False otherwise
        """
        status = self.get_by_package_id(package_id)
        if not status:
            return False

        if security_score is not None:
            status.security_score = security_score
        if security_scan_status is not None:
            status.security_scan_status = security_scan_status

        status.updated_at = datetime.utcnow()
        return True

    def update_approval_info(
        self,
        package_id: int,
        approver_id: Optional[int] = None,
        rejector_id: Optional[int] = None,
        published_at: Optional[datetime] = None,
        publish_status: Optional[str] = None,
    ) -> bool:
        """Update package approval-related fields in a single operation.

        Args:
            package_id: The ID of the package
            approver_id: The ID of the approver (optional)
            rejector_id: The ID of the rejector (optional)
            published_at: The publication timestamp (optional)
            publish_status: The publish status (optional)

        Returns:
            True if update was successful, False otherwise
        """
        status = self.get_by_package_id(package_id)
        if not status:
            return False

        if approver_id is not None:
            status.approver_id = approver_id
        if rejector_id is not None:
            status.rejector_id = rejector_id
        if published_at is not None:
            status.published_at = published_at
        if publish_status is not None:
            status.publish_status = publish_status

        status.updated_at = datetime.utcnow()
        return True

    def go_to_next_stage(self, package_id: int, **kwargs: Any) -> bool:
        """Advance package to the next stage in the workflow.

        This method provides workflow abstraction by automatically determining
        the next status based on the current status.

        Args:
            package_id: The ID of the package
            **kwargs: Additional fields to update along with status

        Returns:
            True if update was successful, False otherwise
        """
        status = self.get_by_package_id(package_id)
        if not status:
            return False

        # Define the workflow stages in order
        workflow_stages = [
            "Checking Licence",
            "Licence Checked",
            "Downloading",
            "Downloaded",
            "Security Scanning",
            "Security Scanned",
            "Pending Approval",
            "Approved",
            "Published",
        ]

        # Failed states are terminal and don't advance
        failed_states = {
            "Parse Failed",
            "Licence Check Failed",
            "Download Failed",
            "Security Scan Failed",
            "Rejected",
        }

        current_status = status.status

        # Check if current status is a failed state - these don't advance
        if current_status in failed_states:
            return False

        current_index = (
            workflow_stages.index(current_status)
            if current_status in workflow_stages
            else -1
        )

        if current_index == -1:
            # Current status not in workflow - cannot advance
            return False

        if current_index >= len(workflow_stages) - 1:
            # Already at final stage - cannot advance further
            return False

        next_status = workflow_stages[current_index + 1]
        return self.update_status(package_id, next_status, **kwargs)
