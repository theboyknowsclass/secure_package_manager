"""Database operations for Package entities."""

from typing import List, Optional

from sqlalchemy import and_, select
from sqlalchemy.orm import Session, selectinload

from ..models import Package, PackageStatus


class PackageOperations:
    """Database operations for Package entities."""

    def __init__(self, session: Session):
        """Initialize with a database session.

        Args:
            session: SQLAlchemy session for database operations
        """
        self.session = session
        self.CHECKING_LICENCE_STR = "Checking Licence"

    def get_by_name_version(self, name: str, version: str) -> Optional[Package]:
        """Get package by name and version.

        Args:
            name: The package name
            version: The package version

        Returns:
            The package if found, None otherwise
        """
        stmt = select(Package).where(and_(Package.name == name, Package.version == version))
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_status(self, status: str) -> List[Package]:
        """Get packages by status.

        Args:
            status: The status to filter by

        Returns:
            List of packages with the specified status, ordered by name
        """
        stmt = (
            select(Package)
            .join(PackageStatus)
            .where(PackageStatus.status == status)
            .options(selectinload(Package.package_status))
            .order_by(Package.name.asc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_by_statuses(self, statuses: List[str]) -> List[Package]:
        """Get packages by multiple statuses.

        Args:
            statuses: List of statuses to filter by

        Returns:
            List of packages with any of the specified statuses
        """
        stmt = (
            select(Package)
            .join(PackageStatus)
            .where(PackageStatus.status.in_(statuses))
            .options(selectinload(Package.package_status))
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_stuck_packages(self, timeout_minutes: int) -> List[Package]:
        """Get packages that have been stuck in processing too long.

        Args:
            timeout_minutes: Number of minutes after which a package is considered stuck

        Returns:
            List of packages that are stuck in processing
        """
        from datetime import datetime, timedelta, timezone

        stuck_threshold = datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)

        stmt = (
            select(Package)
            .join(PackageStatus)
            .where(
                and_(
                    PackageStatus.status.in_(
                        [
                            "Downloading",
                            self.CHECKING_LICENCE_STR,
                            "Security Scanning",
                        ]
                    ),
                    PackageStatus.updated_at < stuck_threshold,
                )
            )
            .options(selectinload(Package.package_status))
        )
        return list(self.session.execute(stmt).scalars().all())

    def create_with_status(self, package_data: dict, status: str = None) -> Package:
        """Create a package with initial status.

        Args:
            package_data: Dictionary containing package data
            status: Initial status for the package

        Returns:
            The created package
        """
        if status is None:
            status = self.CHECKING_LICENCE_STR

        package = Package(**package_data)
        self.session.add(package)
        self.session.flush()  # Get package ID

        # Create package status
        package_status = PackageStatus()
        package_status.package_id = package.id
        package_status.status = status
        package_status.security_scan_status = "pending"
        self.session.add(package_status)

        return package

    def update_license_info(
        self,
        package_id: int,
        license_identifier: Optional[str] = None,
        license_text: Optional[str] = None,
    ) -> bool:
        """Update package license information (readonly package table fields).

        Args:
            package_id: The ID of the package
            license_identifier: The license identifier from package-lock.json (optional)
            license_text: The license text from package-lock.json (optional)

        Returns:
            True if update was successful, False otherwise
        """
        package = self.get_by_id(package_id)
        if not package:
            return False

        # Update package fields (these are input fields from package-lock.json)
        if license_identifier is not None:
            package.license_identifier = license_identifier
        if license_text is not None:
            package.license_text = license_text

        self.session.flush()
        return True

    def batch_create_with_status(self, packages_data: List[dict], status: str = None) -> List[Package]:
        """Create multiple packages with initial status.

        Args:
            packages_data: List of dictionaries containing package data
            status: Initial status for all packages

        Returns:
            List of created packages
        """
        if status is None:
            status = self.CHECKING_LICENCE_STR

        packages = []
        for package_data in packages_data:
            package = self.create_with_status(package_data, status)
            packages.append(package)
        return packages

    def get_all(self) -> List[Package]:
        """Get all packages.

        Returns:
            List of all packages
        """
        return list(self.session.query(Package).all())

    def get_by_id(self, package_id: int) -> Optional[Package]:
        """Get package by ID.

        Args:
            package_id: The ID of the package to retrieve

        Returns:
            The package if found, None otherwise
        """
        return self.session.get(Package, package_id)

    def get_packages_needing_publishing(self, limit: int = 3) -> List[Package]:
        """Get packages that need publishing.

        Args:
            limit: Maximum number of packages to return

        Returns:
            List of packages that need publishing
        """
        stmt = (
            select(Package)
            .join(PackageStatus)
            .where(
                and_(
                    PackageStatus.status == "Approved",
                    PackageStatus.publish_status == "pending",
                )
            )
            .options(selectinload(Package.package_status))
            .limit(limit)
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_stuck_packages_in_publishing(self, stuck_threshold: int) -> List[Package]:
        """Get packages stuck in publishing state.

        Args:
            stuck_threshold: DateTime threshold for considering packages stuck

        Returns:
            List of stuck packages
        """
        stmt = (
            select(Package)
            .join(PackageStatus)
            .where(
                and_(
                    PackageStatus.publish_status.in_(["publishing", "failed"]),
                    PackageStatus.updated_at < stuck_threshold,
                )
            )
            .options(selectinload(Package.package_status))
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_packages_by_publish_status(self, publish_status: str) -> List[Package]:
        """Get packages by publish status.

        Args:
            publish_status: The publish status to filter by

        Returns:
            List of packages with the specified publish status
        """
        stmt = (
            select(Package)
            .join(PackageStatus)
            .where(PackageStatus.publish_status == publish_status)
            .options(selectinload(Package.package_status))
        )
        return list(self.session.execute(stmt).scalars().all())

    def count_packages_by_publish_status(self, publish_status: str) -> int:
        """Count packages by publish status.

        Args:
            publish_status: The publish status to count

        Returns:
            Number of packages with the specified publish status
        """
        stmt = select(Package).join(PackageStatus).where(PackageStatus.publish_status == publish_status)
        return len(list(self.session.execute(stmt).scalars()))

    def count_packages_by_status(self, status: str) -> int:
        """Count packages by status.

        Args:
            status: The status to count

        Returns:
            Number of packages with the specified status
        """
        stmt = select(Package).join(PackageStatus).where(PackageStatus.status == status)
        return len(list(self.session.execute(stmt).scalars()))

    def get_stuck_packages_in_security_scanned(self, stuck_threshold: int) -> List[Package]:
        """Get packages stuck in Security Scanned state.

        Args:
            stuck_threshold: DateTime threshold for considering packages stuck

        Returns:
            List of stuck packages
        """
        stmt = (
            select(Package)
            .join(PackageStatus)
            .where(
                and_(
                    PackageStatus.status == "Security Scanned",
                    PackageStatus.updated_at < stuck_threshold,
                )
            )
            .options(selectinload(Package.package_status))
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_stuck_packages_in_security_scanning(self, stuck_threshold: int) -> List[Package]:
        """Get packages stuck in Security Scanning state.

        Args:
            stuck_threshold: DateTime threshold for considering packages stuck

        Returns:
            List of stuck packages
        """
        stmt = (
            select(Package)
            .join(PackageStatus)
            .where(
                and_(
                    PackageStatus.status == "Security Scanning",
                    PackageStatus.updated_at < stuck_threshold,
                )
            )
            .options(selectinload(Package.package_status))
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_stuck_packages_in_downloading(self, stuck_threshold: int) -> List[Package]:
        """Get packages stuck in Downloading state.

        Args:
            stuck_threshold: DateTime threshold for considering packages stuck

        Returns:
            List of stuck packages
        """
        stmt = (
            select(Package)
            .join(PackageStatus)
            .where(
                and_(
                    PackageStatus.status == "Downloading",
                    PackageStatus.updated_at < stuck_threshold,
                )
            )
            .options(selectinload(Package.package_status))
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_packages_needing_license_check(self, limit: int | None = None) -> List[Package]:
        """Get packages that need license checking.

        Args:
            limit: Maximum number of packages to return

        Returns:
            List of packages that need license checking
        """
        stmt = (
            select(Package)
            .join(PackageStatus)
            .where(PackageStatus.status == self.CHECKING_LICENCE_STR)
            .options(selectinload(Package.package_status))
        )
        if limit:
            stmt = stmt.limit(limit)
        return list(self.session.execute(stmt).scalars().all())

    def get_stuck_packages_in_license_checking(self, stuck_threshold: int) -> List[Package]:
        """Get packages stuck in license checking state.

        Args:
            stuck_threshold: DateTime threshold for considering packages stuck

        Returns:
            List of stuck packages in license checking
        """
        stmt = (
            select(Package)
            .join(PackageStatus)
            .where(
                and_(
                    PackageStatus.status == self.CHECKING_LICENCE_STR,
                    PackageStatus.updated_at < stuck_threshold,
                )
            )
            .options(selectinload(Package.package_status))
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_pending_approval(self) -> List[Package]:
        """Get packages pending approval.

        Returns:
            List of packages pending approval
        """
        stmt = (
            select(Package)
            .join(PackageStatus)
            .where(PackageStatus.status == "Pending Approval")
            .options(selectinload(Package.package_status))
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_recent_packages(self, limit: int = 10) -> List[Package]:
        """Get recent packages with status information.

        Args:
            limit: Maximum number of packages to return

        Returns:
            List of recent packages with status
        """
        stmt = (
            select(Package)
            .join(PackageStatus)
            .where(PackageStatus.updated_at.isnot(None))
            .options(selectinload(Package.package_status))
            .order_by(PackageStatus.updated_at.desc())
            .limit(limit)
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_with_security_scan_info(self, package_id: int) -> Optional[Package]:
        """Get package with security scan information.

        Args:
            package_id: The ID of the package

        Returns:
            Package with security scan info if found, None otherwise
        """
        from ..models import SecurityScan

        stmt = select(Package).outerjoin(SecurityScan).where(Package.id == package_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def count_by_license(self, license_identifier: str) -> int:
        """Count packages by license identifier.

        Args:
            license_identifier: The license identifier to count

        Returns:
            Number of packages with the specified license
        """
        stmt = select(Package).where(Package.license_identifier == license_identifier)
        return len(list(self.session.execute(stmt).scalars()))

    def get_packages_with_context_and_scans(self, request_id: int) -> List[tuple]:
        """Get packages with their request context and security scan info.

        Args:
            request_id: The ID of the request

        Returns:
            List of tuples containing (Package, RequestPackage, SecurityScan)
        """
        from sqlalchemy import func

        from ..models import RequestPackage, SecurityScan

        # First, get all request_packages for this request
        request_package_stmt = select(RequestPackage).where(RequestPackage.request_id == request_id)
        request_packages = self.session.execute(request_package_stmt).scalars().all()

        if not request_packages:
            return []

        # Get package IDs for batch query
        package_ids = [rp.package_id for rp in request_packages]

        # Get all packages in one query
        packages_stmt = select(Package).where(Package.id.in_(package_ids))
        packages = {pkg.id: pkg for pkg in self.session.execute(packages_stmt).scalars().all()}

        # Get latest security scans for all packages in one query
        latest_scans_stmt = select(SecurityScan).where(
            SecurityScan.package_id.in_(package_ids),
            SecurityScan.id.in_(
                select(func.max(SecurityScan.id))
                .where(SecurityScan.package_id.in_(package_ids))
                .group_by(SecurityScan.package_id)
            ),
        )
        latest_scans = {scan.package_id: scan for scan in self.session.execute(latest_scans_stmt).scalars().all()}

        # Build results maintaining order
        results = []
        for rp in request_packages:
            if rp.package_id is not None:
                package = packages.get(rp.package_id)
                if package:
                    scan = latest_scans.get(rp.package_id)
                    results.append((package, rp, scan))

        return results
