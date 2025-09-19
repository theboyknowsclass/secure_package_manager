"""Composite operations class that provides both dictionary and direct access.

This class maintains backward compatibility with the existing dictionary-based
approach while providing cleaner direct access to operations.
"""

import os
from contextlib import contextmanager
from typing import TYPE_CHECKING, Dict, Any, Generator

from sqlalchemy.orm import Session

from .audit_log_operations import AuditLogOperations
from .package_operations import PackageOperations
from .package_status_operations import PackageStatusOperations
from .request_operations import RequestOperations
from .request_package_operations import RequestPackageOperations
from .security_scan_operations import SecurityScanOperations
from .supported_license_operations import SupportedLicenseOperations
from .user_operations import UserOperations

# Import DatabaseService here to avoid circular imports
from ..service import DatabaseService

if TYPE_CHECKING:
    from .base_operations import BaseOperations


class CompositeOperations:
    """Composite operations class that provides direct access to all entity operations.
    
    This class provides a clean, type-safe interface for database operations.
    
    Usage:
        with get_composite_operations() as ops:
            user = ops.user.get_by_username("admin")
            packages = ops.package.get_by_status("Downloaded")
            ops.package_status.update_status(package_id, "Downloaded")
    """
    
    def __init__(self, session: Session):
        """Initialize all operations with the given session.
        
        Args:
            session: SQLAlchemy session for database operations
        """
        self.session = session
        
        # Initialize all entity operations
        self.user = UserOperations(session)
        self.package = PackageOperations(session)
        self.request = RequestOperations(session)
        self.package_status = PackageStatusOperations(session)
        self.request_package = RequestPackageOperations(session)
        self.audit_log = AuditLogOperations(session)
        self.security_scan = SecurityScanOperations(session)
        self.supported_license = SupportedLicenseOperations(session)
    
    
    def commit(self) -> None:
        """Commit the current transaction."""
        self.session.commit()
    
    def rollback(self) -> None:
        """Rollback the current transaction."""
        self.session.rollback()
    
    def flush(self) -> None:
        """Flush pending changes to the database without committing."""
        self.session.flush()
    
    def close(self) -> None:
        """Close the session."""
        self.session.close()
    
    def query(self, *args, **kwargs):
        """Query method that delegates to the session.
        
        This provides backward compatibility for code that uses ops.query() directly.
        """
        return self.session.query(*args, **kwargs)
    
    @classmethod
    @contextmanager
    def get_operations(cls) -> Generator['CompositeOperations', None, None]:
        """Class method to get composite operations for database access.
        
        This replaces the need for flask_utils.get_composite_operations().
        
        Usage:
            with CompositeOperations.get_operations() as ops:
                user = ops.user.get_by_username("admin")
                packages = ops.package.get_by_status("Downloaded")
                ops.package_status.update_status(package_id, "Downloaded")
        """
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is required")

        db_service = DatabaseService(database_url)
        with db_service.get_session() as session:
            composite_ops = cls(session)
            yield composite_ops
