"""Security Service.

Handles security scanning for packages. This service separates database operations 
from I/O work for optimal performance.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from database.operations.package_operations import PackageOperations
from database.operations.package_status_operations import PackageStatusOperations
from database.operations.security_scan_operations import SecurityScanOperations
from database.session_helper import SessionHelper

logger = logging.getLogger(__name__)


class SecurityService:
    """Service for handling package security scanning.

    This service separates database operations from I/O work to minimize database session time.
    """

    def __init__(self) -> None:
        """Initialize the security service."""
        self.logger = logger

    def process_package_batch(
        self, max_packages: int = 5
    ) -> Dict[str, Any]:
        """Process a batch of packages for security scanning.

        This method separates database operations from I/O work:
        1. Get packages that need scanning (short DB session)
        2. Perform security scans (no DB session)
        3. Update database with results (short DB session)

        Args:
            max_packages: Maximum number of packages to process

        Returns:
            Dict with processing results
        """
        try:
            # Phase 1: Get package data (short DB session)
            packages_to_process = self._get_packages_for_scanning(max_packages)
            if not packages_to_process:
                return {
                    "success": True,
                    "processed_count": 0,
                    "successful_scans": 0,
                    "failed_scans": 0,
                    "total_packages": 0
                }

            # Phase 2: Perform security scans (no DB session)
            scan_results = self._perform_security_scan_batch(packages_to_process)

            # Phase 3: Update database (short DB session)
            return self._update_scan_results(scan_results)

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

    def _get_packages_for_scanning(self, max_packages: int) -> List[Any]:
        """Get packages that need security scanning (short DB session).

        Args:
            max_packages: Maximum number of packages to retrieve

        Returns:
            List of packages that need security scanning
        """
        with SessionHelper.get_session() as db:
            package_ops = PackageOperations(db.session)
            return package_ops.get_by_status("Downloaded")[:max_packages]

    def _perform_security_scan_batch(self, packages: List[Any]) -> List[Tuple[Any, Dict[str, Any]]]:
        """Perform security scans without database sessions.

        Args:
            packages: List of packages to scan

        Returns:
            List of tuples (package, result_dict)
        """
        results = []
        for package in packages:
            result = self._perform_security_scan_work(package)
            results.append((package, result))
        return results

    def _perform_security_scan_work(self, package: Any) -> Dict[str, Any]:
        """Pure I/O work - no database operations.

        Args:
            package: Package to scan

        Returns:
            Dict with scan result
        """
        try:
            # Perform the actual security scan using Trivy service
            scan_result = self._perform_security_scan(package)

            # Process scan results
            if scan_result.get("status") == "failed":
                return {"status": "failed", "error": "Security scan failed"}
            else:
                return {"status": "success", "scan_data": scan_result}

        except Exception as e:
            self.logger.error(f"Error scanning package {package.name}@{package.version}: {str(e)}")
            return {"status": "failed", "error": str(e)}

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
            return trivy_service.scan_package_data_only(package)
        except Exception as e:
            self.logger.error(f"Error performing security scan: {str(e)}")
            return {"status": "failed", "error": str(e)}

    def _update_scan_results(self, scan_results: List[Tuple[Any, Dict[str, Any]]]) -> Dict[str, Any]:
        """Update database with scan results (short DB session).

        Args:
            scan_results: List of tuples (package, result_dict)

        Returns:
            Dict with processing results
        """
        successful_count = 0
        failed_count = 0

        with SessionHelper.get_session() as db:
            package_ops = PackageOperations(db.session)
            status_ops = PackageStatusOperations(db.session)
            security_scan_ops = SecurityScanOperations(db.session)

            for package, result in scan_results:
                try:
                    # Verify package still needs processing (race condition protection)
                    current_package = package_ops.get_by_id(package.id)
                    if not current_package or not current_package.package_status or current_package.package_status.status != "Downloaded":
                        continue  # Skip if status changed

                    if result["status"] == "success":
                        # Update package status to Security Scanned
                        status_ops.update_status(package.id, "Security Scanned")
                        
                        # Update package with security score if available
                        if "scan_data" in result and "security_score" in result["scan_data"]:
                            status_ops.update_security_score(package.id, result["scan_data"]["security_score"])
                        
                        # Store scan results if available
                        if "scan_data" in result:
                            self._store_scan_results(security_scan_ops, package.id, result["scan_data"])
                        
                        successful_count += 1
                    else:  # failed
                        status_ops.update_status(package.id, "Security Scan Failed")
                        failed_count += 1

                except Exception as e:
                    self.logger.error(f"Error updating package {package.name}@{package.version}: {str(e)}")
                    failed_count += 1

            db.commit()

        # Log batch summary
        if successful_count > 0 or failed_count > 0:
            self.logger.info(
                f"Security scan batch complete: {successful_count} successful, {failed_count} failed"
            )

        return {
            "success": True,
            "processed_count": len(scan_results),
            "successful_scans": successful_count,
            "failed_scans": failed_count,
            "total_packages": len(scan_results)
        }

    def _store_scan_results(self, security_scan_ops: SecurityScanOperations, package_id: int, scan_data: Dict[str, Any]) -> None:
        """Store security scan results in database.

        Args:
            security_scan_ops: Security scan operations instance
            package_id: ID of the package that was scanned
            scan_data: Scan results data
        """
        try:
            # Create security scan record
            from database.models.security_scan import SecurityScan
            
            security_scan = SecurityScan(
                package_id=package_id,
                scan_type="trivy",
                scan_status="completed",
                vulnerabilities_found=scan_data.get("scan_result", {}).get("vulnerabilities", []),
                scan_summary=scan_data.get("scan_result", {}).get("summary", {}),
                scan_details=scan_data.get("scan_result", {}),
                critical_count=scan_data.get("critical_count", 0),
                high_count=scan_data.get("high_count", 0),
                medium_count=scan_data.get("medium_count", 0),
                low_count=scan_data.get("low_count", 0),
                info_count=scan_data.get("info_count", 0),
                scan_duration_ms=scan_data.get("scan_duration_ms", 0),
                trivy_version=scan_data.get("trivy_version", "unknown"),
                completed_at=datetime.utcnow()
            )
            
            security_scan_ops.create(security_scan)
            
        except Exception as e:
            self.logger.error(f"Error storing scan results for package {package_id}: {str(e)}")
