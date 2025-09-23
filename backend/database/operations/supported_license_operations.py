"""Database operations for SupportedLicense entities."""

from typing import List, Optional, Type

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import SupportedLicense
from .base_operations import BaseOperations


class SupportedLicenseOperations(BaseOperations):
    """Database operations for SupportedLicense entities."""

    def get_by_identifier(self, identifier: str) -> Optional[SupportedLicense]:
        """Get supported license by SPDX identifier.

        Args:
            identifier: The SPDX license identifier

        Returns:
            The supported license if found, None otherwise
        """
        stmt = select(SupportedLicense).where(
            SupportedLicense.identifier == identifier
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_status(self, status: str) -> List[SupportedLicense]:
        """Get supported licenses by status.

        Args:
            status: The status to filter by

        Returns:
            List of supported licenses with the specified status
        """
        stmt = select(SupportedLicense).where(
            SupportedLicense.status == status
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_allowed_licenses(self) -> List[SupportedLicense]:
        """Get all allowed licenses.

        Returns:
            List of all allowed licenses
        """
        return self.get_by_status("allowed")

    def get_blocked_licenses(self) -> List[SupportedLicense]:
        """Get all blocked licenses.

        Returns:
            List of all blocked licenses
        """
        return self.get_by_status("blocked")

    def get_all(self) -> List[SupportedLicense]:
        """Get all supported licenses.

        Returns:
            List of all supported licenses
        """
        return super().get_all(SupportedLicense)

    def count_packages_by_license(self, identifier: str) -> int:
        """Count packages using a specific license.

        Args:
            identifier: The license identifier to count

        Returns:
            Number of packages using the specified license
        """
        from ..models import Package

        stmt = select(Package).where(Package.license_identifier == identifier)
        return self.session.execute(stmt).scalars().count()
