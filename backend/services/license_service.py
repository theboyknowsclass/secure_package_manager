import logging

from models import SupportedLicense

logger = logging.getLogger(__name__)


class LicenseService:
    """Service for license validation and management"""

    def __init__(self):
        self.logger = logger

    def validate_package_license(self, package_data):
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

    def _parse_license_info(self, package_data):
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

    def _create_no_license_result(self):
        """Create result for packages with no license information"""
        return {
            "score": 0,
            "errors": ["No license information found"],
            "warnings": ["Package has no license specified"],
        }

    def _lookup_license_in_db(self, license_identifier):
        """Look up license in database, including variations"""
        # Find the license in the database
        license = SupportedLicense.query.filter_by(
            identifier=license_identifier
        ).first()

        if not license:
            # Check for common variations
            license = self._find_license_variation(license_identifier)

        return license

    def _create_unknown_license_result(self, license_identifier):
        """Create result for unknown licenses"""
        return {
            "score": 0,
            "errors": [f'License "{license_identifier}" is not recognized'],
            "warnings": [
                f'License "{license_identifier}" is not in the license database'
            ],
        }

    def _validate_license_status(self, license, license_identifier, package_name):
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

    def _create_blocked_license_result(self, license_identifier):
        """Create result for blocked licenses"""
        return {
            "score": 0,
            "errors": [f'License "{license_identifier}" is blocked by policy'],
            "warnings": [f'License "{license_identifier}" is explicitly prohibited'],
        }

    def _create_avoid_license_result(self, license_identifier):
        """Create result for avoided licenses"""
        return {
            "score": 30,
            "errors": [],
            "warnings": [
                f'License "{license_identifier}" is discouraged and may have restrictions'
            ],
        }

    def _create_allowed_license_result(self, license, license_identifier, package_name):
        """Create result for allowed licenses"""
        score = self._calculate_license_score(license)
        result = {"score": score, "errors": [], "warnings": []}

        self.logger.info(
            f"License validation for {package_name}: {license_identifier} - Score: {score} (Allowed)"
        )
        return result

    def _create_always_allowed_license_result(
        self, license, license_identifier, package_name
    ):
        """Create result for always allowed licenses"""
        score = self._calculate_license_score(license)
        result = {"score": score, "errors": [], "warnings": []}

        self.logger.info(
            f"License validation for {package_name}: {license_identifier} - Score: {score} (Always Allowed)"
        )
        return result

    def _create_unknown_status_result(self, license_identifier):
        """Create result for licenses with unknown status"""
        return {
            "score": 0,
            "errors": [f'License "{license_identifier}" has unknown status'],
            "warnings": [],
        }

    def _find_license_variation(self, license_identifier):
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
            license = SupportedLicense.query.filter_by(identifier=variation).first()
            if license:
                return license

        # Try partial matches
        licenses = SupportedLicense.query.filter(
            SupportedLicense.identifier.ilike(f"%{license_identifier}%")
        ).all()

        if licenses:
            return licenses[0]  # Return first match

        return None

    def _calculate_license_score(self, supported_license):
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

    def get_supported_licenses(self, status=None):
        """Get all supported licenses, optionally filtered by status"""
        try:
            query = SupportedLicense.query
            if status:
                query = query.filter_by(status=status)
            return query.all()
        except Exception as e:
            self.logger.error(f"Error getting supported licenses: {str(e)}")
            return []

    def is_license_allowed(self, license_identifier):
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
