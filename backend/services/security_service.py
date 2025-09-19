"""Security Service.

Handles security scanning for packages. This service manages its own database sessions
and operations, following the service-first architecture pattern.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from database.operations.package_operations import PackageOperations
from database.operations.package_status_operations import PackageStatusOperations
from database.session_helper import SessionHelper

logger = logging.getLogger(__name__)


class SecurityService:
    """Service for handling package security scanning.

    This service manages its own database sessions and operations,
    following the service-first architecture pattern.
    """

    def __init__(self) -> None:
        """Initialize the security service."""
        self.logger = logger
        # Operations instances (set up in _setup_operations)
        self._session = None
        self._package_ops = None
        self._status_ops = None

    def _setup_operations(self, session):
        """Set up operations instances for the current session."""
        self._session = session
        self._package_ops = PackageOperations(session)
        self._status_ops = PackageStatusOperations(session)

    def process_package_batch(
        self, max_packages: int = 5
    ) -> Dict[str, Any]:
        """Process a batch of packages for security scanning.

        Args:
            max_packages: Maximum number of packages to process (reduced for better performance)

        Returns:
            Dict with processing results
        """
        try:
            with SessionHelper.get_session() as db:
                # Set up operations
                self._setup_operations(db.session)
                
                # Find packages that need security scanning
                downloaded_packages = self._package_ops.get_by_status("Downloaded")
                
                # Limit the number of packages processed (smaller batches)
                limited_packages = downloaded_packages[:max_packages]

                if not limited_packages:
                    return {
                        "success": True,
                        "processed_count": 0,
                        "successful_scans": 0,
                        "failed_scans": 0,
                        "total_packages": 0
                    }

                successful_scans = 0
                failed_scans = 0

                for package in limited_packages:
                    result = self.scan_single_package(package)
                    if result["success"]:
                        successful_scans += 1
                    else:
                        failed_scans += 1

                db.commit()

                return {
                    "success": True,
                    "processed_count": len(limited_packages),
                    "successful_scans": successful_scans,
                    "failed_scans": failed_scans,
                    "total_packages": len(limited_packages)
                }
        except Exception as e:
            self.logger.error(f"Error processing security scan batch: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "processed_count": 0,
                "successful_scans": 0,
                "failed_scans": 0,
                "total_packages": 0
            }

    def scan_single_package(self, package: Any) -> Dict[str, Any]:
        """Scan a single package for security vulnerabilities.

        Args:
            package: Package to scan

        Returns:
            Dict with scan results
        """
        try:
            # Update package status to "Security Scanning"
            self._update_package_status_to_scanning(package)

            # Perform the actual security scan
            scan_result = self._perform_security_scan(package)

            # Process scan results
            if scan_result.get("status") == "failed":
                self._mark_scan_failed(package)
                return {"success": False, "error": "Security scan failed"}
            else:
                self._mark_scan_completed(package, scan_result)
                return {"success": True, "scan_result": scan_result}

        except Exception as e:
            self.logger.error(
                f"Error scanning package {package.name}@{package.version}: {str(e)}"
            )
            self._mark_scan_failed(package)
            return {"success": False, "error": str(e)}


    def _perform_security_scan(self, package: Any) -> Dict[str, Any]:
        """Perform the actual security scan using Trivy service.

        Args:
            package: Package to scan

        Returns:
            Dict with scan results
        """
        try:
            # Import here to avoid circular imports
            from services.trivy_service import TrivyService
            
            trivy_service = TrivyService()
            return trivy_service.scan_package(package)
        except Exception as e:
            self.logger.error(f"Error performing security scan: {str(e)}")
            return {"status": "failed", "error": str(e)}

    def _update_package_status_to_scanning(self, package: Any) -> None:
        """Update package status to Security Scanning.

        Args:
            package: Package to update
        """
        if package.package_status:
            self._status_ops.go_to_next_stage(package.id)

    def _mark_scan_completed(self, package: Any, scan_result: Dict[str, Any]) -> None:
        """Mark package scan as completed.

        Args:
            package: Package to update
            scan_result: Results from the security scan
        """
        if package.package_status:
            self._status_ops.go_to_next_stage(package.id)

    def _mark_scan_failed(self, package: Any) -> None:
        """Mark package scan as failed.

        Args:
            package: Package to update
        """
        if package.package_status:
            self._status_ops.update_status(package.id, "Security Scan Failed")
