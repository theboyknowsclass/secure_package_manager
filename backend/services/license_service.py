"""License Service.

Handles license validation and management for packages. This service is used
by both the API (for immediate processing) and workers (for background processing).

This service works with entity-based operations structure and focuses purely on business logic.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class LicenseService:
    """Service for license validation and management.

    This service handles the business logic of license validation and
    scoring. It works with database operations passed in from the caller
    (worker or API) to maintain separation of concerns.
    """

    def __init__(self) -> None:
        """Initialize the license service."""
        self.logger = logger
        # Cache for license lookups to avoid repeated database queries
        self._license_cache: Dict[str, Optional[Any]] = {}
        self._cache_loaded = False

    def validate_package_license(
        self, package_data: Dict[str, Any], ops: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate a package's license against 4-tier status system.

        Args:
            package_data: Package data including license information
            ops: Dictionary of database operations instances

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
                    license_identifier, package_name, ops
                )

            # Look up license in database
            license = self._lookup_license_in_db(license_identifier, ops)
            if not license:
                return self._create_unknown_license_result(license_identifier)

            # Calculate score based on license tier
            score = self._calculate_license_score(license)

            return {
                "valid": True,
                "score": score,
                "license_identifier": license_identifier,
                "license_tier": license.tier,
                "license_name": license.name,
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
                "license_tier": "Unknown",
                "license_name": "Unknown",
                "errors": [str(e)],
            }

    def process_license_group(
        self, license_string: str, packages: List[Any], ops: Dict[str, Any]
    ) -> Tuple[List[Any], List[Any]]:
        """Process a group of packages with the same license.

        Args:
            license_string: The license identifier for this group
            packages: List of packages to process
            ops: Dictionary of database operations instances

        Returns:
            Tuple of (successful_packages, failed_packages)
        """
        successful_packages = []
        failed_packages = []

        try:
            # Validate the license for this group
            license_validation = self._validate_license_string(
                license_string, ops
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
                        package, license_validation, ops
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
        self, packages: List[Any], ops: Dict[str, Any]
    ) -> Tuple[List[Any], List[Any]]:
        """Process a batch of packages individually.

        Args:
            packages: List of packages to process
            ops: Dictionary of database operations instances

        Returns:
            Tuple of (successful_packages, failed_packages)
        """
        successful_packages = []
        failed_packages = []

        for package in packages:
            try:
                result = self._process_single_package_individual(package, ops)
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

    def _validate_complex_license_expression(
        self, license_identifier: str, package_name: str, ops: Dict[str, Any]
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
        best_license = None

        for license_name in individual_licenses:
            license_obj = self._lookup_license_in_db(license_name.strip(), ops)
            if license_obj:
                score = self._calculate_license_score(license_obj)
                if score < min_score:
                    min_score = score
                    best_license = license_obj

        if best_license:
            return {
                "valid": True,
                "score": min_score,
                "license_identifier": license_identifier,
                "license_tier": best_license.tier,
                "license_name": best_license.name,
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
        self, license_identifier: str, ops: Dict[str, Any]
    ) -> Optional[Any]:
        """Look up a license in the database."""
        # Load cache if not already loaded
        if not self._cache_loaded:
            self._load_license_cache(ops)
            self._cache_loaded = True

        # Check cache first
        if license_identifier in self._license_cache:
            return self._license_cache[license_identifier]

        # Look up in database
        license_obj = ops["supported_license"].get_by_name(license_identifier)
        self._license_cache[license_identifier] = license_obj
        return license_obj

    def _load_license_cache(self, ops: Dict[str, Any]) -> None:
        """Load all supported licenses into cache."""
        try:
            licenses = ops["supported_license"].get_all()
            for license_obj in licenses:
                self._license_cache[license_obj.name] = license_obj
        except Exception as e:
            self.logger.error(f"Error loading license cache: {str(e)}")

    def _calculate_license_score(self, license_obj: Any) -> int:
        """Calculate score based on license tier."""
        tier_scores = {
            "Approved": 100,
            "Conditional": 75,
            "Restricted": 25,
            "Prohibited": 0,
        }
        return tier_scores.get(license_obj.tier, 0)

    def _create_no_license_result(self) -> Dict[str, Any]:
        """Create result for packages with no license."""
        return {
            "valid": False,
            "score": 0,
            "license_identifier": "No License",
            "license_tier": "Prohibited",
            "license_name": "No License",
            "errors": ["Package has no license information"],
        }

    def _create_unknown_license_result(
        self, license_identifier: str
    ) -> Dict[str, Any]:
        """Create result for unknown licenses."""
        return {
            "valid": False,
            "score": 0,
            "license_identifier": license_identifier,
            "license_tier": "Unknown",
            "license_name": "Unknown",
            "errors": [f"Unknown license: {license_identifier}"],
        }

    def _validate_license_string(
        self, license_string: str, ops: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate a license string."""
        if not license_string or license_string == "No License":
            return self._create_no_license_result()

        if self._is_complex_license_expression(license_string):
            return self._validate_complex_license_expression(
                license_string, "Unknown", ops
            )

        license_obj = self._lookup_license_in_db(license_string, ops)
        if not license_obj:
            return self._create_unknown_license_result(license_string)

        return {
            "valid": True,
            "score": self._calculate_license_score(license_obj),
            "license_identifier": license_string,
            "license_tier": license_obj.tier,
            "license_name": license_obj.name,
            "errors": [],
        }

    def _process_single_package(
        self,
        package: Any,
        license_validation: Dict[str, Any],
        ops: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Process a single package with pre-validated license."""
        try:
            # Update package status
            ops["package_status"].update_package_status(
                package.id,
                "Licence Checked",
                ops["package_status"].PackageStatus,
            )

            # Update package with license information
            package.license = license_validation["license_identifier"]
            package.license_score = license_validation["score"]
            package.license_tier = license_validation["license_tier"]
            package.updated_at = datetime.utcnow()

            return {
                "success": True,
                "package": package,
                "score": license_validation["score"],
                "license_tier": license_validation["license_tier"],
            }

        except Exception as e:
            return {
                "success": False,
                "package": package,
                "error": str(e),
            }

    def _process_single_package_individual(
        self, package: Any, ops: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process a single package individually (fallback method)."""
        try:
            # Get package data for validation
            package_data = {
                "name": package.name,
                "version": package.version,
                "license": package.license,
            }

            # Validate license
            license_validation = self.validate_package_license(
                package_data, ops
            )

            if not license_validation.get("valid", False):
                return {
                    "success": False,
                    "package": package,
                    "error": f"License validation failed: {', '.join(license_validation.get('errors', []))}",
                }

            # Update package status
            ops["package_status"].update_package_status(
                package.id,
                "Licence Checked",
                ops["package_status"].PackageStatus,
            )

            # Update package with license information
            package.license = license_validation["license_identifier"]
            package.license_score = license_validation["score"]
            package.license_tier = license_validation["license_tier"]
            package.updated_at = datetime.utcnow()

            return {
                "success": True,
                "package": package,
                "score": license_validation["score"],
                "license_tier": license_validation["license_tier"],
            }

        except Exception as e:
            return {
                "success": False,
                "package": package,
                "error": str(e),
            }
