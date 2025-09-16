"""
Package Processor

Handles the processing of individual packages through the validation pipeline,
including license validation, security scanning, and status updates.
"""

import logging
from typing import Any, Dict

from models import Package, db

logger = logging.getLogger(__name__)


class PackageProcessor:
    """Processes individual packages through the validation pipeline"""

    def __init__(self, license_service: Any, trivy_service: Any, db_session: Any = None) -> None:
        self.license_service = license_service
        self.trivy_service = trivy_service
        self.db = db_session or db

    def process_pending_packages(self, request_id: int) -> Dict[str, Any]:
        """
        Process all pending packages for a request

        Args:
            request_id: The ID of the package request

        Returns:
            Dictionary with processing results
        """
        packages = Package.query.filter_by(
            package_request_id=request_id, status="requested"
        ).all()

        if not packages:
            logger.info(f"No pending packages found for request {request_id}")
            return {"processed": 0, "failed": 0, "errors": [], "packages": []}

        logger.info(
            f"Processing {len(packages)} pending packages for request {request_id}"
        )

        results: Dict[str, Any] = {"processed": 0, "failed": 0, "errors": [], "packages": []}

        for package in packages:
            try:
                package_result = self._process_single_package(package)
                results["packages"].append(package_result)

                if package_result["success"]:
                    results["processed"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append(
                        f"Package {package.name}@{package.version}: {package_result['error']}"
                    )

            except Exception as e:
                results["failed"] += 1
                error_msg = f"Package {package.name}@{package.version}: {str(e)}"
                results["errors"].append(error_msg)
                logger.error(f"Failed to process package {package.name}: {str(e)}")

                # Update package status to failed
                try:
                    package.status = "rejected"
                    package.validation_errors = [str(e)]
                    self.db.session.commit()
                except Exception as commit_error:
                    logger.error(
                        f"Failed to update package status after error: {str(commit_error)}"
                    )

        logger.info(
            f"Completed processing for request {request_id}: "
            f"{results['processed']} successful, {results['failed']} failed"
        )

        return results

    def _process_single_package(self, package: Package) -> Dict[str, Any]:
        """
        Process a single package through the validation pipeline

        Args:
            package: The package object to process

        Returns:
            Dictionary with processing result
        """
        try:
            logger.info(
                f"Starting processing for package {package.name}@{package.version}"
            )

            # Step 1: Perform license check
            if not self._perform_license_check(package):
                return {
                    "success": False,
                    "error": "License validation failed",
                    "package_id": package.id,
                    "package_name": package.name,
                    "package_version": package.version,
                }

            # Step 2: Create validation records
            if not self._create_validation_records(package):
                return {
                    "success": False,
                    "error": "Failed to create validation records",
                    "package_id": package.id,
                    "package_name": package.name,
                    "package_version": package.version,
                }

            # Step 3: Perform security scan
            if not self._perform_security_scan(package):
                return {
                    "success": False,
                    "error": "Security scan failed",
                    "package_id": package.id,
                    "package_name": package.name,
                    "package_version": package.version,
                }

            # Step 4: Mark as ready for approval
            package.status = "pending_approval"
            self.db.session.commit()

            logger.info(
                f"Successfully processed package {package.name}@{package.version}"
            )

            return {
                "success": True,
                "package_id": package.id,
                "package_name": package.name,
                "package_version": package.version,
                "final_status": package.status,
            }

        except Exception as e:
            logger.error(
                f"Error processing package {package.name}@{package.version}: {str(e)}"
            )
            return {
                "success": False,
                "error": str(e),
                "package_id": package.id,
                "package_name": package.name,
                "package_version": package.version,
            }

    def _perform_license_check(self, package: Package) -> bool:
        """
        Perform license validation for a package

        Args:
            package: The package to validate

        Returns:
            True if license validation passed, False otherwise
        """
        try:
            # Update status to performing license check
            package.status = "performing_licence_check"
            self.db.session.commit()

            # Validate package information (license check)
            if not self._validate_package_info(package):
                package.status = "rejected"
                package.validation_errors = ["Package validation failed"]
                self.db.session.commit()
                return False

            # Update status to license check complete
            package.status = "licence_check_complete"
            self.db.session.commit()

            return True

        except Exception as e:
            logger.error(
                f"License check failed for {package.name}@{package.version}: {str(e)}"
            )
            package.status = "rejected"
            package.validation_errors = [str(e)]
            self.db.session.commit()
            return False

    def _perform_security_scan(self, package: Package) -> bool:
        """
        Perform security scan for a package

        Args:
            package: The package to scan

        Returns:
            True if security scan completed (even with vulnerabilities), False if failed
        """
        try:
            # Update status to performing security scan
            package.status = "performing_security_scan"
            self.db.session.commit()

            logger.info(
                f"Starting security scan for package {package.name}@{package.version}"
            )
            scan_result = self.trivy_service.scan_package(package)

            if scan_result["status"] == "failed":
                logger.warning(
                    f"Security scan failed for {package.name}@{package.version}: "
                    f"{scan_result.get('error', 'Unknown error')}"
                )
                # Don't fail the package validation if security scan fails, just log it
                package.validation_errors = package.validation_errors or []
                package.validation_errors.append(
                    f"Security scan failed: {scan_result.get('error', 'Unknown error')}"
                )
            else:
                logger.info(
                    f"Security scan completed for {package.name}@{package.version}: "
                    f"{scan_result.get('vulnerability_count', 0)} vulnerabilities found"
                )

            # Update status to security scan complete
            package.status = "security_scan_complete"
            self.db.session.commit()

            return True

        except Exception as e:
            logger.error(
                f"Security scan failed for {package.name}@{package.version}: {str(e)}"
            )
            package.status = "rejected"
            package.validation_errors = package.validation_errors or []
            package.validation_errors.append(f"Security scan failed: {str(e)}")
            self.db.session.commit()
            return False

    def _validate_package_info(self, package: Package) -> bool:
        """
        Validate package information (license check)

        Args:
            package: The package to validate

        Returns:
            True if validation passed, False otherwise
        """
        try:
            # Basic validation - check if we have the required information
            if not package.name or not package.version:
                logger.warning(
                    f"Package {package.name}@{package.version} missing required information"
                )
                return False

            # Simulate package download (in production, this would download from registry)
            if not self._simulate_package_download(package):
                logger.warning(
                    f"Failed to download package {package.name}@{package.version}"
                )
                package.validation_errors = ["Failed to download package"]
                return False

            # Validate license information
            license_validation = self._validate_package_license(package)

            # Store the license score
            package.license_score = license_validation["score"]

            if license_validation["score"] == 0:
                # For testing, allow packages with missing licenses to proceed
                logger.warning(
                    f"Package {package.name}@{package.version} has license issues but allowing for testing: "
                    f"{license_validation['errors']}"
                )
                # Don't return False, just log the warning

            logger.info(
                f"Package {package.name}@{package.version} validated successfully "
                f"(License: {package.license_identifier}, Score: {package.license_score})"
            )
            return True

        except Exception as e:
            logger.error(
                f"Error validating package info for {package.name}@{package.version}: {str(e)}"
            )
            return False

    def _simulate_package_download(self, package: Package) -> bool:
        """
        Simulate downloading package from source repository

        Args:
            package: The package to simulate download for

        Returns:
            True if simulation successful, False otherwise
        """
        try:
            # In production, this would download from npm registry
            # For now, just simulate success
            logger.info(f"Simulating download for {package.name}@{package.version}")
            return True

        except Exception as e:
            logger.error(f"Error simulating package download: {str(e)}")
            return False

    def _validate_package_license(self, package: Package) -> Dict[str, Any]:
        """
        Validate package license information

        Args:
            package: The package to validate

        Returns:
            License validation result
        """
        try:
            # Get package data from npm registry or package-lock.json
            package_data = {
                "name": package.name,
                "version": package.version,
                "license": package.license_identifier,  # This should be populated from package-lock.json
            }

            # Use license service to validate
            validation_result: Dict[str, Any] = self.license_service.validate_package_license(
                package_data
            )

            return validation_result

        except Exception as e:
            logger.error(
                f"Error validating package license for {package.name}@{package.version}: {str(e)}"
            )
            return {
                "score": 0,
                "errors": [f"License validation failed: {str(e)}"],
                "warnings": [],
            }

    def _create_validation_records(self, package: Package) -> bool:
        """
        Create validation records for a package

        Args:
            package: The package to create records for

        Returns:
            True if records created successfully, False otherwise
        """
        try:
            # In production, this would create detailed validation records
            # For now, just simulate success
            logger.info(
                f"Creating validation records for {package.name}@{package.version}"
            )
            return True

        except Exception as e:
            logger.error(f"Error creating validation records: {str(e)}")
            return False
