"""License Service.

Handles license validation and management for packages. This service manages its own database sessions
and operations, following the service-first architecture pattern.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from database.operations.package_operations import PackageOperations
from database.operations.package_status_operations import PackageStatusOperations
from database.operations.supported_license_operations import SupportedLicenseOperations
from database.session_helper import SessionHelper

logger = logging.getLogger(__name__)


class LicenseService:
    """Service for license validation and management.

    This service manages its own database sessions and operations,
    following the service-first architecture pattern.
    """

    def __init__(self) -> None:
        """Initialize the license service."""
        self.logger = logger
        # Cache for license data to avoid repeated database queries
        # Store values instead of database objects to avoid session issues
        self._license_cache: Dict[str, Optional[Dict[str, Any]]] = {}
        self._cache_loaded = False
        # Operations instances (set up in _setup_operations)
        self._session = None
        self._package_ops = None
        self._status_ops = None
        self._license_ops = None

    def _setup_operations(self, session):
        """Set up operations instances for the current session."""
        self._session = session
        self._package_ops = PackageOperations(session)
        self._status_ops = PackageStatusOperations(session)
        self._license_ops = SupportedLicenseOperations(session)

    def process_license_groups(
        self, max_license_groups: int = 20
    ) -> Dict[str, Any]:
        """Process license groups for packages that need license checking.

        Args:
            max_license_groups: Maximum number of license groups to process

        Returns:
            Dict with processing results
        """
        try:
            with SessionHelper.get_session() as db:
                # Set up operations
                self._setup_operations(db.session)
                
                # Find packages that need license checking
                pending_packages = self._package_ops.get_packages_needing_license_check()

                if not pending_packages:
                    return {
                        "success": True,
                        "processed_count": 0,
                        "successful_packages": 0,
                        "failed_packages": 0,
                        "license_groups_processed": 0
                    }

                # Group packages by license for efficient processing
                license_groups = self._group_packages_by_license(pending_packages)

                # Process license groups
                successful_packages = []
                failed_packages = []
                groups_processed = 0

                for i, (license_string, packages) in enumerate(license_groups.items()):
                    if i >= max_license_groups:
                        break

                    try:
                        group_successful, group_failed = (
                            self.process_license_group(
                                license_string, packages
                            )
                        )
                        successful_packages.extend(group_successful)
                        failed_packages.extend(group_failed)
                        groups_processed += 1

                    except Exception as e:
                        self.logger.error(
                            f"Error processing license group {license_string}: {str(e)}"
                        )
                        # Mark all packages in this group as failed
                        for package in packages:
                            failed_packages.append(
                                {
                                    "package": package,
                                    "error": f"License group processing failed: {str(e)}",
                                }
                            )

                # Handle fallback processing for any remaining packages
                if len(license_groups) > max_license_groups:
                    remaining_packages = []
                    for i, (license_string, packages) in enumerate(license_groups.items()):
                        if i >= max_license_groups:
                            remaining_packages.extend(packages)

                    if remaining_packages:
                        self.logger.info(
                            f"Processing {len(remaining_packages)} remaining packages individually"
                        )
                        fallback_successful, fallback_failed = (
                            self.process_package_batch(
                                remaining_packages
                            )
                        )
                        successful_packages.extend(fallback_successful)
                        failed_packages.extend(fallback_failed)

                # Handle failed packages
                if failed_packages:
                    self._handle_failed_packages(failed_packages)

                db.commit()

                return {
                    "success": True,
                    "processed_count": len(successful_packages) + len(failed_packages),
                    "successful_packages": len(successful_packages),
                    "failed_packages": len(failed_packages),
                    "license_groups_processed": groups_processed
                }

        except Exception as e:
            self.logger.error(f"Error processing license groups: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "processed_count": 0,
                "successful_packages": 0,
                "failed_packages": 0,
                "license_groups_processed": 0
            }

    def validate_package_license(
        self, package_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate a package's license against 4-tier status system.

        Args:
            package_data: Package data including license information
            license_ops: License operations instance (from calling session)

        Returns:
            Dict: Validation result with score and errors
        """
        try:
            # Parse license information from package data
            license_identifier = self._parse_license_info(package_data)
            package_name = package_data.get("name", "Unknown")

            # Handle missing license
            if not license_identifier:
                return self._create_no_license_result()

            # Check if this is a complex license expression
            if self._is_complex_license_expression(license_identifier):
                return self._validate_complex_license_expression(
                    license_identifier, package_name
                )

            # Look up license in database
            license_data = self._lookup_license_in_db(license_identifier)
            if not license_data:
                return self._create_unknown_license_result(license_identifier)

            # Use cached data
            license_status = license_data["status"]
            license_name = license_data["name"]
            score = self._calculate_license_score(license_data)

            return {
                "valid": True,
                "score": score,
                "license_identifier": license_identifier,
                "license_status": license_status,
                "license_name": license_name,
                "errors": [],
            }

        except Exception as e:
            self.logger.error(f"Error validating package license: {str(e)}")
            return {
                "valid": False,
                "score": 0,
                "license_identifier": (
                    license_identifier
                    if "license_identifier" in locals()
                    else "Unknown"
                ),
                "license_status": "Unknown",
                "license_name": "Unknown",
                "errors": [str(e)],
            }

    def process_license_group(
        self, license_string: str, packages: List[Any]
    ) -> Tuple[List[Any], List[Any]]:
        """Process a group of packages with the same license.

        Args:
            license_string: The license identifier for this group
            packages: List of packages to process
            status_ops: Package status operations instance
            license_ops: Supported license operations instance

        Returns:
            Tuple of (successful_packages, failed_packages)
        """
        successful_packages = []
        failed_packages = []

        try:
            # Validate the license for this group
            license_validation = self._validate_license_string(
                license_string
            )

            if not license_validation.get("valid", False):
                # All packages in this group fail
                for package in packages:
                    failed_packages.append(
                        {
                            "package": package,
                            "error": f"License validation failed: {', '.join(license_validation.get('errors', []))}",
                        }
                    )
                return successful_packages, failed_packages

            # Process each package in the group
            for package in packages:
                try:
                    result = self._process_single_package(
                        package, license_validation
                    )
                    if result["success"]:
                        successful_packages.append(result)
                    else:
                        failed_packages.append(
                            {
                                "package": package,
                                "error": result.get("error", "Unknown error"),
                            }
                        )
                except Exception as e:
                    failed_packages.append(
                        {
                            "package": package,
                            "error": f"Error processing package: {str(e)}",
                        }
                    )

        except Exception as e:
            self.logger.error(
                f"Error processing license group {license_string}: {str(e)}"
            )
            # Mark all packages as failed
            for package in packages:
                failed_packages.append(
                    {
                        "package": package,
                        "error": f"License group processing failed: {str(e)}",
                    }
                )

        return successful_packages, failed_packages

    def process_package_batch(
        self, packages: List[Any]
    ) -> Tuple[List[Any], List[Any]]:
        """Process a batch of packages individually.

        Args:
            packages: List of packages to process
            status_ops: Package status operations instance
            license_ops: Supported license operations instance

        Returns:
            Tuple of (successful_packages, failed_packages)
        """
        successful_packages = []
        failed_packages = []

        for package in packages:
            try:
                result = self._process_single_package_individual(package)
                if result["success"]:
                    successful_packages.append(result)
                else:
                    failed_packages.append(
                        {
                            "package": package,
                            "error": result.get("error", "Unknown error"),
                        }
                    )
            except Exception as e:
                failed_packages.append(
                    {
                        "package": package,
                        "error": f"Error processing package {package.name}@{package.version}: {str(e)}",
                    }
                )

        return successful_packages, failed_packages

    def _parse_license_info(
        self, package_data: Dict[str, Any]
    ) -> Optional[str]:
        """Parse license information from package data."""
        # Check for license field
        license_info = package_data.get("license")
        if license_info:
            if isinstance(license_info, str):
                return license_info
            elif isinstance(license_info, dict):
                return license_info.get("type", license_info.get("name"))

        # Check for licenses field (array)
        licenses = package_data.get("licenses")
        if licenses and isinstance(licenses, list) and len(licenses) > 0:
            first_license = licenses[0]
            if isinstance(first_license, str):
                return first_license
            elif isinstance(first_license, dict):
                return first_license.get("type", first_license.get("name"))

        return None

    def _is_complex_license_expression(self, license_identifier: str) -> bool:
        """Check if the license identifier is a complex expression."""
        complex_indicators = [
            " OR ",
            " AND ",
            "(",
            ")",
            "MIT OR",
            "Apache-2.0 OR",
        ]
        return any(
            indicator in license_identifier for indicator in complex_indicators
        )

    def _group_packages_by_license(
        self, packages: List[Any]
    ) -> Dict[str, List[Any]]:
        """Group packages by their license string for efficient processing."""
        license_groups = {}

        for package in packages:
            license_string = package.license_identifier or "No License"
            if license_string not in license_groups:
                license_groups[license_string] = []
            license_groups[license_string].append(package)

        return license_groups

    def _handle_failed_packages(
        self, failed_packages: List[Dict[str, Any]]
    ) -> None:
        """Handle packages that failed license validation."""
        for failed_item in failed_packages:
            package = failed_item["package"]
            error = failed_item["error"]

            try:
                # Update package status to indicate failure
                self._status_ops.update_status(package.id, "Licence Check Failed")

                # Log the failure
                self.logger.warning(
                    f"Package {package.name}@{package.version} failed license validation: {error}"
                )

            except Exception as e:
                self.logger.error(
                    f"Error handling failed package {package.name}@{package.version}: {str(e)}"
                )

    def _validate_complex_license_expression(
        self, license_identifier: str, package_name: str
    ) -> Dict[str, Any]:
        """Validate complex license expressions."""
        # For complex expressions, we'll use a conservative approach
        # and score them based on the most restrictive license found

        # Extract individual licenses from the expression
        individual_licenses = self._extract_individual_licenses(
            license_identifier
        )

        if not individual_licenses:
            return self._create_unknown_license_result(license_identifier)

        # Find the most restrictive license
        min_score = float("inf")
        best_license_status = None
        best_license_name = None
        best_license_identifier = None

        for license_name in individual_licenses:
            license_data = self._lookup_license_in_db(license_name.strip())
            if license_data:
                # Use cached data
                license_status = license_data["status"]
                license_name_value = license_data["name"]
                
                score = self._calculate_license_score(license_data)
                if score < min_score:
                    min_score = score
                    best_license_status = license_status
                    best_license_name = license_name_value
                    best_license_identifier = license_name.strip()

        if best_license_status:
            return {
                "valid": True,
                "score": min_score,
                "license_identifier": best_license_identifier,
                "license_status": best_license_status,
                "license_name": best_license_name,
                "errors": [],
            }
        else:
            return self._create_unknown_license_result(license_identifier)

    def _extract_individual_licenses(
        self, license_expression: str
    ) -> List[str]:
        """Extract individual license names from a complex expression."""
        # Simple extraction - split on common operators
        import re

        # Remove parentheses and split on OR/AND
        cleaned = re.sub(r"[()]", "", license_expression)
        licenses = re.split(r"\s+(?:OR|AND)\s+", cleaned, flags=re.IGNORECASE)

        # Clean up each license name
        return [license.strip() for license in licenses if license.strip()]

    def _lookup_license_in_db(
        self, license_identifier: str
    ) -> Optional[Dict[str, Any]]:
        """Look up a license in the database and return cached values."""
        # Load cache if not already loaded
        if not self._cache_loaded:
            self._load_license_cache()
            self._cache_loaded = True

        # Check cache first
        if license_identifier in self._license_cache:
            return self._license_cache[license_identifier]

        # Look up in database and extract values immediately
        license_obj = self._license_ops.get_by_identifier(license_identifier)
        if license_obj:
            # Extract values while session is active
            license_data = {
                "status": license_obj.status,
                "name": license_obj.name,
                "identifier": license_obj.identifier
            }
            self._license_cache[license_identifier] = license_data
            return license_data
        else:
            self._license_cache[license_identifier] = None
            return None

    def _load_license_cache(self) -> None:
        """Load all supported licenses into cache."""
        try:
            licenses = self._license_ops.get_all()
            for license_obj in licenses:
                # Extract values while session is active
                license_data = {
                    "status": license_obj.status,
                    "name": license_obj.name,
                    "identifier": license_obj.identifier
                }
                self._license_cache[license_obj.identifier] = license_data
        except Exception as e:
            self.logger.error(f"Error loading license cache: {str(e)}")

    def _calculate_license_score(self, license_data: Dict[str, Any]) -> int:
        """Calculate score based on license status."""
        status_scores = {
            "always_allowed": 100,
            "allowed": 75,
            "unknown": 50,
            "avoid": 25,
            "blocked": 0,
        }
        return status_scores.get(license_data.get("status"), 0)

    def _create_no_license_result(self) -> Dict[str, Any]:
        """Create result for packages with no license."""
        return {
            "valid": True,
            "score": 50,
            "license_identifier": "No License",
            "license_status": "unknown",
            "license_name": "No License",
            "errors": [],
        }

    def _create_unknown_license_result(
        self, license_identifier: str
    ) -> Dict[str, Any]:
        """Create result for unknown licenses."""
        return {
            "valid": True,
            "score": 50,
            "license_identifier": license_identifier,
            "license_status": "unknown",
            "license_name": "Unknown",
            "errors": [],
        }

    def _validate_license_string(
        self, license_string: str
    ) -> Dict[str, Any]:
        """Validate a license string."""
        if not license_string or license_string == "No License":
            return self._create_no_license_result()

        if self._is_complex_license_expression(license_string):
            return self._validate_complex_license_expression(
                license_string, "Unknown"
            )

        license_data = self._lookup_license_in_db(license_string)
        if not license_data:
            return self._create_unknown_license_result(license_string)

        # Use cached data
        license_status = license_data["status"]
        license_name = license_data["name"]
        score = self._calculate_license_score(license_data)

        return {
            "valid": True,
            "score": score,
            "license_identifier": license_string,
            "license_status": license_status,
            "license_name": license_name,
            "errors": [],
        }

    def _process_single_package(
        self,
        package: Any,
        license_validation: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Process a single package with pre-validated license."""
        try:
            # Update package status to next stage
            self._status_ops.go_to_next_stage(package.id)

            # Update package with license information
            package.license_identifier = license_validation["license_identifier"]
            
            # Update package status with license validation results
            self._status_ops.update_license_info(
                package.id, 
                license_validation["score"], 
                license_validation["license_status"]
            )

            return {
                "success": True,
                "package": package,
                "score": license_validation["score"],
                "license_status": license_validation["license_status"],
            }

        except Exception as e:
            return {
                "success": False,
                "package": package,
                "error": str(e),
            }

    def _process_single_package_individual(
        self, package: Any
    ) -> Dict[str, Any]:
        """Process a single package individually (fallback method)."""
        try:
            # Get package data for validation
            package_data = {
                "name": package.name,
                "version": package.version,
                "license": package.license_identifier,
            }

            # Validate license
            license_validation = self.validate_package_license(package_data)

            if not license_validation.get("valid", False):
                return {
                    "success": False,
                    "package": package,
                    "error": f"License validation failed: {', '.join(license_validation.get('errors', []))}",
                }

            # Update package status to next stage
            self._status_ops.go_to_next_stage(package.id)

            # Update package with license information
            package.license_identifier = license_validation["license_identifier"]
            
            # Update package status with license validation results
            self._status_ops.update_license_info(
                package.id, 
                license_validation["score"], 
                license_validation["license_status"]
            )

            return {
                "success": True,
                "package": package,
                "score": license_validation["score"],
                "license_status": license_validation["license_status"],
            }

        except Exception as e:
            return {
                "success": False,
                "package": package,
                "error": str(e),
            }
