"""Database operations for SecurityScan entities."""

from typing import List, Optional, Type

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import SecurityScan


class SecurityScanOperations:
    """Database operations for SecurityScan entities."""

    def __init__(self, session: Session):
        """Initialize with a database session.

        Args:
            session: SQLAlchemy session for database operations
        """
        self.session = session

    def create(self, security_scan: SecurityScan) -> SecurityScan:
        """Create a new security scan.

        Args:
            security_scan: The security scan to create

        Returns:
            The created security scan (with ID populated)
        """
        self.session.add(security_scan)
        self.session.flush()
        return security_scan

    def get_by_package_id(self, package_id: int) -> List[SecurityScan]:
        """Get security scans by package ID.

        Args:
            package_id: The ID of the package

        Returns:
            List of security scans for the specified package
        """
        stmt = select(SecurityScan).where(
            SecurityScan.package_id == package_id
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_latest_by_package_id(
        self, package_id: int
    ) -> Optional[SecurityScan]:
        """Get the latest security scan for a package.

        Args:
            package_id: The ID of the package

        Returns:
            The latest security scan if found, None otherwise
        """
        stmt = (
            select(SecurityScan)
            .where(SecurityScan.package_id == package_id)
            .order_by(SecurityScan.created_at.desc())
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_packages_needing_scan(self) -> List[int]:
        """Get package IDs that need security scanning.

        This would typically join with PackageStatus to find packages
        in "Downloaded" status that haven't been scanned yet.

        Returns:
            List of package IDs that need security scanning
        """
        # Implementation depends on specific business logic
        # For now, return empty list - this would be implemented based on
        # requirements
        return []

    def get_all(self) -> List[SecurityScan]:
        """Get all security scans.

        Returns:
            List of all security scans
        """
        return list(self.session.query(SecurityScan).all())

    def get_by_id(self, security_scan_id: int) -> Optional[SecurityScan]:
        """Get security scan by ID.

        Args:
            security_scan_id: The ID of the security scan to retrieve

        Returns:
            The security scan if found, None otherwise
        """
        return self.session.get(SecurityScan, security_scan_id)
