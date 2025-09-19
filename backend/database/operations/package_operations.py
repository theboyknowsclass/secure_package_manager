"""Database operations for Package entities."""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from ..models import Package, PackageStatus
from .base_operations import BaseOperations

class PackageOperations(BaseOperations):
    """Database operations for Package entities."""
    
    def get_by_name_version(self, name: str, version: str) -> Optional[Package]:
        """Get package by name and version.
        
        Args:
            name: The package name
            version: The package version
            
        Returns:
            The package if found, None otherwise
        """
        stmt = select(Package).where(
            and_(Package.name == name, Package.version == version)
        )
        return self.session.execute(stmt).scalar_one_or_none()
    
    def get_by_status(self, status: str) -> List[Package]:
        """Get packages by status.
        
        Args:
            status: The status to filter by
            
        Returns:
            List of packages with the specified status
        """
        stmt = select(Package).join(PackageStatus).where(
            PackageStatus.status == status
        )
        return list(self.session.execute(stmt).scalars().all())
    
    def get_by_statuses(self, statuses: List[str]) -> List[Package]:
        """Get packages by multiple statuses.
        
        Args:
            statuses: List of statuses to filter by
            
        Returns:
            List of packages with any of the specified statuses
        """
        stmt = select(Package).join(PackageStatus).where(
            PackageStatus.status.in_(statuses)
        )
        return list(self.session.execute(stmt).scalars().all())
    
    def get_stuck_packages(self, timeout_minutes: int) -> List[Package]:
        """Get packages that have been stuck in processing too long.
        
        Args:
            timeout_minutes: Number of minutes after which a package is considered stuck
            
        Returns:
            List of packages that are stuck in processing
        """
        from datetime import datetime, timedelta
        stuck_threshold = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        
        stmt = select(Package).join(PackageStatus).where(
            and_(
                PackageStatus.status.in_(["Downloading", "Checking Licence", "Security Scanning"]),
                PackageStatus.updated_at < stuck_threshold
            )
        )
        return list(self.session.execute(stmt).scalars().all())
    
    def create_with_status(self, package_data: dict, status: str = "Submitted") -> Package:
        """Create a package with initial status.
        
        Args:
            package_data: Dictionary containing package data
            status: Initial status for the package
            
        Returns:
            The created package
        """
        package = Package(**package_data)
        self.session.add(package)
        self.session.flush()  # Get package ID
        
        # Create package status
        package_status = PackageStatus(
            package_id=package.id,
            status=status,
            security_scan_status="pending"
        )
        self.session.add(package_status)
        
        return package
    
    def batch_create_with_status(self, packages_data: List[dict], status: str = "Submitted") -> List[Package]:
        """Create multiple packages with initial status.
        
        Args:
            packages_data: List of dictionaries containing package data
            status: Initial status for all packages
            
        Returns:
            List of created packages
        """
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
        return super().get_all(Package)
    
    def get_by_id(self, package_id: int) -> Optional[Package]:
        """Get package by ID.
        
        Args:
            package_id: The ID of the package
            
        Returns:
            The package if found, None otherwise
        """
        return super().get_by_id(Package, package_id)
