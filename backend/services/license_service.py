import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from models import PackageStatus, SupportedLicense, db

logger = logging.getLogger(__name__)


class LicenseService:
    """Service for license validation and management"""

    def __init__(self) -> None:
        self.logger = logger

    def validate_package_license(self, package_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a package's license against 4-tier status system

        Args:
            package_data (dict): Package data including license information

        Returns:
            dict: Validation result with score and errors
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
            license = self._lookup_license_in_db(license_identifier)
            if not license:
                return self._create_unknown_license_result(license_identifier)

            # Validate based on license status
            return self._validate_license_status(
                license, license_identifier, package_name
            )

        except Exception as e:
            self.logger.error(
                f"License validation error for {package_data.get('name', 'Unknown')}: {str(e)}"
            )
            return {
                "score": 0,
                "errors": [f"License validation failed: {str(e)}"],
                "warnings": [],
            }

    def update_package_license_status(
        self,
        package_id: int,
        license_score: int,
        errors: List[str] | None = None,
        warnings: List[str] | None = None,
    ) -> None:
        """
        Update package status with license validation results

        Args:
            package_id: The package ID to update
            license_score: The calculated license score
            errors: List of validation errors
            warnings: List of validation warnings
        """
        try:
            package_status = PackageStatus.query.filter_by(
                package_id=package_id
            ).first()
            if package_status:
                package_status.license_score = license_score
                # Update status based on license score
                if license_score >= 80:
                    package_status.status = "Licence Checked"
                elif license_score >= 30:
                    package_status.status = "Licence Checked"  # Still allow but with warning
                else:
                    package_status.status = "Rejected"

                package_status.updated_at = datetime.utcnow()
                db.session.commit()

                self.logger.info(
                    f"Updated package {package_id} license status: score={license_score}, status={package_status.status}"
                )
            else:
                self.logger.warning(
                    f"Package status not found for package {package_id}"
                )

        except Exception as e:
            self.logger.error(f"Error updating package license status: {str(e)}")
            db.session.rollback()

    def _parse_license_info(self, package_data: Dict[str, Any]) -> Optional[str]:
        """Parse and normalize license information from package data"""
        license_identifier = package_data.get("license")

        if not license_identifier:
            return None

        # Handle multiple licenses (array format)
        if isinstance(license_identifier, list):
            if len(license_identifier) == 0:
                return None
            # Use the first license for validation
            license_identifier = license_identifier[0]

        # Handle license objects (e.g., {"type": "MIT", "url": "..."})
        if isinstance(license_identifier, dict):
            license_identifier = license_identifier.get("type", "")

        # Clean up license identifier
        license_identifier = str(license_identifier).strip()

        return license_identifier if license_identifier else None

    def _create_no_license_result(self) -> Dict[str, Any]:
        """Create result for packages with no license information"""
        return {
            "score": 0,
            "errors": ["No license information found"],
            "warnings": ["Package has no license specified"],
        }

    def _lookup_license_in_db(
        self, license_identifier: str
    ) -> Optional[SupportedLicense]:
        """Look up license in database, including variations"""
        # Find the license in the database
        license: Optional[SupportedLicense] = SupportedLicense.query.filter_by(
            identifier=license_identifier
        ).first()

        if not license:
            # Check for common variations
            license = self._find_license_variation(license_identifier)

        return license

    def _create_unknown_license_result(self, license_identifier: str) -> Dict[str, Any]:
        """Create result for unknown licenses"""
        return {
            "score": 0,
            "errors": [f'License "{license_identifier}" is not recognized'],
            "warnings": [
                f'License "{license_identifier}" is not in the license database'
            ],
        }

    def _validate_license_status(
        self, license: SupportedLicense, license_identifier: str, package_name: str
    ) -> Dict[str, Any]:
        """Validate license based on its status"""
        if license.status == "blocked":
            return self._create_blocked_license_result(license_identifier)
        elif license.status == "avoid":
            return self._create_avoid_license_result(license_identifier)
        elif license.status == "allowed":
            return self._create_allowed_license_result(
                license, license_identifier, package_name
            )
        elif license.status == "always_allowed":
            return self._create_always_allowed_license_result(
                license, license_identifier, package_name
            )
        else:
            return self._create_unknown_status_result(license_identifier)

    def _create_blocked_license_result(self, license_identifier: str) -> Dict[str, Any]:
        """Create result for blocked licenses"""
        return {
            "score": 0,
            "errors": [f'License "{license_identifier}" is blocked by policy'],
            "warnings": [f'License "{license_identifier}" is explicitly prohibited'],
        }

    def _create_avoid_license_result(self, license_identifier: str) -> Dict[str, Any]:
        """Create result for avoided licenses"""
        return {
            "score": 30,
            "errors": [],
            "warnings": [
                f'License "{license_identifier}" is discouraged and may have restrictions'
            ],
        }

    def _create_allowed_license_result(
        self, license: SupportedLicense, license_identifier: str, package_name: str
    ) -> Dict[str, Any]:
        """Create result for allowed licenses"""
        score = self._calculate_license_score(license)
        result = {"score": score, "errors": [], "warnings": []}

        self.logger.info(
            f"License validation for {package_name}: {license_identifier} - Score: {score} (Allowed)"
        )
        return result

    def _create_always_allowed_license_result(
        self, license: SupportedLicense, license_identifier: str, package_name: str
    ) -> Dict[str, Any]:
        """Create result for always allowed licenses"""
        score = self._calculate_license_score(license)
        result = {"score": score, "errors": [], "warnings": []}

        self.logger.info(
            f"License validation for {package_name}: {license_identifier} - Score: {score} (Always Allowed)"
        )
        return result

    def _create_unknown_status_result(self, license_identifier: str) -> Dict[str, Any]:
        """Create result for licenses with unknown status"""
        return {
            "score": 0,
            "errors": [f'License "{license_identifier}" has unknown status'],
            "warnings": [],
        }

    def _find_license_variation(
        self, license_identifier: str
    ) -> Optional[SupportedLicense]:
        """Find license by common variations"""
        variations = [
            license_identifier.lower(),
            license_identifier.upper(),
            license_identifier.replace("-", " "),
            license_identifier.replace(" ", "-"),
            license_identifier.replace("_", "-"),
            license_identifier.replace("_", " "),
        ]

        for variation in variations:
            license: Optional[SupportedLicense] = SupportedLicense.query.filter_by(
                identifier=variation
            ).first()
            if license:
                return license

        # Try partial matches
        licenses: List[SupportedLicense] = SupportedLicense.query.filter(
            SupportedLicense.identifier.ilike(f"%{license_identifier}%")
        ).all()

        if licenses:
            return licenses[0]  # Return first match

        return None

    def _calculate_license_score(self, supported_license: SupportedLicense) -> int:
        """Calculate license compliance score based on status"""
        if supported_license.status == "always_allowed":
            return 100
        elif supported_license.status == "allowed":
            return 80
        elif supported_license.status == "avoid":
            return 30
        elif supported_license.status == "blocked":
            return 0
        else:
            return 0

    def get_supported_licenses(
        self, status: Optional[str] = None
    ) -> List[SupportedLicense]:
        """Get all supported licenses, optionally filtered by status"""
        try:
            query = SupportedLicense.query
            if status:
                query = query.filter_by(status=status)
            return list(query.all())
        except Exception as e:
            self.logger.error(f"Error getting supported licenses: {str(e)}")
            return []

    def is_license_allowed(self, license_identifier: str) -> bool:
        """Check if a license is allowed (not blocked)"""
        try:
            license = SupportedLicense.query.filter_by(
                identifier=license_identifier
            ).first()

            if not license:
                return False

            return license.status in ["always_allowed", "allowed", "avoid"]
        except Exception as e:
            self.logger.error(f"Error checking license support: {str(e)}")
            return False

    def _is_complex_license_expression(self, license_identifier: str) -> bool:
        """Check if the license identifier is a complex expression with OR/AND operators"""
        if not license_identifier:
            return False

        # Check for common complex expression patterns
        complex_patterns = [" OR ", " AND ", "(", ")", "|", "&"]

        return any(
            pattern in license_identifier.upper() for pattern in complex_patterns
        )

    def _validate_complex_license_expression(
        self, license_expression: str, package_name: str
    ) -> Dict[str, Any]:
        """Validate complex license expressions like (MIT OR CC0-1.0)"""
        try:
            # Parse the license expression to extract individual licenses
            individual_licenses = self._parse_license_expression(license_expression)

            if not individual_licenses:
                return self._create_unknown_license_result(license_expression)

            # For OR expressions, use the best (highest scoring) license
            # For AND expressions, use the worst (lowest scoring) license
            if " OR " in license_expression.upper() or "|" in license_expression:
                return self._validate_or_expression(
                    individual_licenses, license_expression, package_name
                )
            elif " AND " in license_expression.upper() or "&" in license_expression:
                return self._validate_and_expression(
                    individual_licenses, license_expression, package_name
                )
            else:
                # Default to OR behavior for complex expressions
                return self._validate_or_expression(
                    individual_licenses, license_expression, package_name
                )

        except Exception as e:
            self.logger.error(
                f"Error validating complex license expression '{license_expression}': {str(e)}"
            )
            return {
                "score": 0,
                "errors": [f"Failed to parse license expression: {license_expression}"],
                "warnings": [],
            }

    def _parse_license_expression(self, license_expression: str) -> List[str]:
        """Parse a license expression to extract individual license identifiers"""
        # Remove parentheses and normalize
        cleaned = license_expression.replace("(", "").replace(")", "").strip()

        # Split by OR/AND operators
        licenses = []
        for separator in [" OR ", " AND ", "|", "&"]:
            if separator in cleaned.upper():
                licenses = [
                    license.strip() for license in cleaned.upper().split(separator)
                ]
                break

        # If no separators found, treat as single license
        if not licenses:
            licenses = [cleaned]

        # Clean up each license identifier
        cleaned_licenses = []
        for license in licenses:
            cleaned_license = license.strip()
            if cleaned_license:
                cleaned_licenses.append(cleaned_license)

        return cleaned_licenses

    def _validate_or_expression(
        self,
        individual_licenses: List[str],
        original_expression: str,
        package_name: str,
    ) -> Dict[str, Any]:
        """Validate OR expression - use the best (highest scoring) license"""
        best_score = 0
        best_result = None
        all_errors = []
        all_warnings = []

        for license_id in individual_licenses:
            # Look up each license
            license = self._lookup_license_in_db(license_id)
            if license:
                result = self._validate_license_status(
                    license, license_id, package_name
                )
                if result["score"] > best_score:
                    best_score = result["score"]
                    best_result = result
            else:
                all_errors.append(f'License "{license_id}" is not recognized')
                all_warnings.append(
                    f'License "{license_id}" is not in the license database'
                )

        if best_result:
            # Add information about the OR expression
            best_result["warnings"].append(
                f"Using best license from OR expression: {original_expression}"
            )
            return best_result
        else:
            return {
                "score": 0,
                "errors": all_errors,
                "warnings": all_warnings,
            }

    def _validate_and_expression(
        self,
        individual_licenses: List[str],
        original_expression: str,
        package_name: str,
    ) -> Dict[str, Any]:
        """Validate AND expression - use the worst (lowest scoring) license"""
        worst_score = 100
        worst_result = None
        all_errors = []
        all_warnings = []
        valid_licenses = []

        for license_id in individual_licenses:
            # Look up each license
            license = self._lookup_license_in_db(license_id)
            if license:
                result = self._validate_license_status(
                    license, license_id, package_name
                )
                valid_licenses.append(result)
                if result["score"] < worst_score:
                    worst_score = result["score"]
                    worst_result = result
            else:
                all_errors.append(f'License "{license_id}" is not recognized')
                all_warnings.append(
                    f'License "{license_id}" is not in the license database'
                )

        if worst_result:
            # Add information about the AND expression
            worst_result["warnings"].append(
                f"Using worst license from AND expression: {original_expression}"
            )
            return worst_result
        else:
            return {
                "score": 0,
                "errors": all_errors,
                "warnings": all_warnings,
            }
