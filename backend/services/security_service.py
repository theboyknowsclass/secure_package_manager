"""Security Service.

Handles security scanning for packages. This service is used
by both the API (for immediate processing) and workers (for background processing).

This service works with entity-based operations structure and focuses purely on business logic.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SecurityService:
    """Service for handling package security scanning.

    This service handles the business logic of security scanning and
    status management. It works with database operations passed in from the caller
    (worker or API) to maintain separation of concerns.
    """

    def __init__(self) -> None:
        """Initialize the security service."""
        self.logger = logger

    def process_package_batch(
        self, packages: List[Any], ops
    ) -> Dict[str, Any]:
        """Process a batch of packages for security scanning.

        Args:
            packages: List of packages to process
            ops: Composite operations instance

        Returns:
            Dict with processing results
        """
        try:
            successful_scans = 0
            failed_scans = 0

            for package in packages:
                result = self.scan_single_package(package, ops)
                if result["success"]:
                    successful_scans += 1
                else:
                    failed_scans += 1

            return {
                "success": True,
                "successful_scans": successful_scans,
                "failed_scans": failed_scans,
                "total_packages": len(packages)
            }
        except Exception as e:
            self.logger.error(f"Error processing security scan batch: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "successful_scans": 0,
                "failed_scans": 0,
                "total_packages": len(packages)
            }

    def scan_single_package(
        self, package: Any, ops
    ) -> Dict[str, Any]:
        """Scan a single package for security vulnerabilities.

        Args:
            package: Package to scan
            ops: Composite operations instance

        Returns:
            Dict with scan results
        """
        try:
            # Update package status to "Security Scanning"
            self._update_package_status_to_scanning(package, ops)

            # Perform the actual security scan
            scan_result = self._perform_security_scan(package)

            # Process scan results
            if scan_result.get("status") == "failed":
                self._mark_scan_failed(package, ops)
                return {"success": False, "error": "Security scan failed"}
            else:
                self._mark_scan_completed(package, scan_result, ops)
                return {"success": True, "scan_result": scan_result}

        except Exception as e:
            self.logger.error(
                f"Error scanning package {package.name}@{package.version}: {str(e)}"
            )
            self._mark_scan_failed(package, ops)
            return {"success": False, "error": str(e)}

    def get_stuck_packages(
        self, stuck_threshold: datetime, ops: Dict[str, Any]
    ) -> List[Any]:
        """Get packages that have been stuck in Security Scanning state too long.

        Args:
            stuck_threshold: DateTime threshold for considering packages stuck
            ops: Dictionary of database operations instances

        Returns:
            List of stuck packages
        """
        try:
            # Use operations to get stuck packages
            stuck_packages = ops.package.get_stuck_packages_in_security_scanning(
                stuck_threshold
            )
            return stuck_packages
        except Exception as e:
            self.logger.error(f"Error getting stuck packages: {str(e)}")
            return []

    def reset_stuck_packages(
        self, stuck_packages: List[Any], ops: Dict[str, Any]
    ) -> None:
        """Reset stuck packages to Downloaded status.

        Args:
            stuck_packages: List of stuck packages to reset
            ops: Dictionary of database operations instances
        """
        for package in stuck_packages:
            try:
                ops.package_status.update_status(
                    package.id, "Downloaded"
                )
                self.logger.info(
                    f"Reset stuck package {package.name}@{package.version} to Downloaded"
                )
            except Exception as e:
                self.logger.error(
                    f"Error resetting stuck package {package.name}@{package.version}: {str(e)}"
                )

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

    def _update_package_status_to_scanning(
        self, package: Any, ops: Dict[str, Any]
    ) -> None:
        """Update package status to Security Scanning.

        Args:
            package: Package to update
            ops: Dictionary of database operations instances
        """
        if package.package_status:
            ops.package_status.update_status(
                package.id, "Security Scanning"
            )
            ops.package_status.update_security_scan_status(
                package.id, "running"
            )

    def _mark_scan_completed(
        self, package: Any, scan_result: Dict[str, Any], ops: Dict[str, Any]
    ) -> None:
        """Mark package scan as completed.

        Args:
            package: Package to update
            scan_result: Results from the security scan
            ops: Dictionary of database operations instances
        """
        if package.package_status:
            ops.package_status.update_status(
                package.id, "Security Scanned"
            )
            ops.package_status.update_security_scan_status(
                package.id, "completed"
            )
            
            # Update security score if available
            if "security_score" in scan_result:
                ops.package_status.update_security_score(
                    package.id, scan_result["security_score"]
                )

    def _mark_scan_failed(self, package: Any, ops) -> None:
        """Mark package scan as failed.

        Args:
            package: Package to update
            ops: Dictionary of database operations instances
        """
        if package.package_status:
            ops.package_status.update_status(
                package.id, "Security Scanned"
            )
            ops.package_status.update_security_scan_status(
                package.id, "failed"
            )
