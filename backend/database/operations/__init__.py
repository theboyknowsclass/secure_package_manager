"""Database operations package.

This package provides entity-specific database operations classes that
handle all database interactions for each entity type. Operations are
organized by entity to provide clear separation of concerns and better
maintainability.
"""

from typing import Dict, Type

from sqlalchemy.orm import Session

from .audit_log_operations import AuditLogOperations
from .base_operations import BaseOperations

# CompositeOperations has been removed - use SessionHelper + individual entity operations instead
from .package_operations import PackageOperations
from .package_status_operations import PackageStatusOperations
from .request_operations import RequestOperations
from .request_package_operations import RequestPackageOperations
from .security_scan_operations import SecurityScanOperations
from .supported_license_operations import SupportedLicenseOperations
from .user_operations import UserOperations


class OperationsFactory:
    """Factory for creating entity-specific operations."""

    _operations_classes: Dict[str, Type[BaseOperations]] = {
        "package": PackageOperations,
        "request": RequestOperations,
        "user": UserOperations,
        "package_status": PackageStatusOperations,
        "request_package": RequestPackageOperations,
        "audit_log": AuditLogOperations,
        "security_scan": SecurityScanOperations,
        "supported_license": SupportedLicenseOperations,
    }

    @classmethod
    def create_operations(
        cls, entity_type: str, session: Session
    ) -> BaseOperations:
        """Create operations instance for specific entity type."""
        if entity_type not in cls._operations_classes:
            raise ValueError(f"Unknown entity type: {entity_type}")

        return cls._operations_classes[entity_type](session)


# Convenience imports
__all__ = [
    "BaseOperations",
    "PackageOperations",
    "RequestOperations",
    "UserOperations",
    "PackageStatusOperations",
    "RequestPackageOperations",
    "AuditLogOperations",
    "SecurityScanOperations",
    "SupportedLicenseOperations",
    "OperationsFactory",
]
