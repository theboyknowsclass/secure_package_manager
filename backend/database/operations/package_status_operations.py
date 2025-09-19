"""Database operations for PackageStatus entities."""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from datetime import datetime

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
        stmt = select(PackageStatus).where(PackageStatus.package_id == package_id)
        return self.session.execute(stmt).scalar_one_or_none()
    
    def update_status(self, package_id: int, new_status: str, **kwargs) -> bool:
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
        
        status.status = new_status
        status.updated_at = datetime.utcnow()
        
        # Update any additional fields
        for key, value in kwargs.items():
            if hasattr(status, key):
                setattr(status, key, value)
        
        return True
    
    def batch_update_status(self, package_ids: List[int], new_status: str, **kwargs) -> int:
        """Update status for multiple packages.
        
        Args:
            package_ids: List of package IDs to update
            new_status: The new status to set
            **kwargs: Additional fields to update
            
        Returns:
            Number of packages updated
        """
        updated_count = self.session.query(PackageStatus).filter(
            PackageStatus.package_id.in_(package_ids)
        ).update({
            PackageStatus.status: new_status,
            PackageStatus.updated_at: datetime.utcnow(),
            **kwargs
        }, synchronize_session=False)
        
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
    
    def get_stuck_statuses(self, timeout_minutes: int, statuses: List[str]) -> List[PackageStatus]:
        """Get stuck package statuses.
        
        Args:
            timeout_minutes: Number of minutes after which a status is considered stuck
            statuses: List of statuses to check for stuck packages
            
        Returns:
            List of stuck package statuses
        """
        from datetime import timedelta
        stuck_threshold = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        
        stmt = select(PackageStatus).where(
            and_(
                PackageStatus.status.in_(statuses),
                PackageStatus.updated_at < stuck_threshold
            )
        )
        return list(self.session.execute(stmt).scalars().all())
    
    def get_all(self) -> List[PackageStatus]:
        """Get all package statuses.
        
        Returns:
            List of all package statuses
        """
        return super().get_all(PackageStatus)
