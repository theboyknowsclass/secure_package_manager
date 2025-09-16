import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from models import PackageStatus, SupportedLicense, db

logger = logging.getLogger(__name__)


class LicenseService:
    """Service for license validation and management"""

    def __init__(self) -> None:
        self.logger = logger
        # Cache for license lookups to avoid repeated database queries
        self._license_cache: Dict[str, Optional[SupportedLicense]] = {}
        self._cache_loaded = False

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
            "license_status": None,
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
            "score": 50,
            "license_status": None,
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
            "license_status": "blocked",
            "errors": [f'License "{license_identifier}" is blocked by policy'],
            "warnings": [f'License "{license_identifier}" is explicitly prohibited'],
        }

    def _create_avoid_license_result(self, license_identifier: str) -> Dict[str, Any]:
        """Create result for avoided licenses"""
        return {
            "score": 30,
            "license_status": "avoid",
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
        result = {
            "score": score, 
            "license_status": license.status,
            "errors": [], 
            "warnings": []
        }

        self.logger.info(
            f"License validation for {package_name}: {license_identifier} - Score: {score} (Allowed)"
        )
        return result

    def _create_always_allowed_license_result(
        self, license: SupportedLicense, license_identifier: str, package_name: str
    ) -> Dict[str, Any]:
        """Create result for always allowed licenses"""
        score = self._calculate_license_score(license)
        result = {
            "score": score, 
            "license_status": license.status,
            "errors": [], 
            "warnings": []
        }

        self.logger.info(
            f"License validation for {package_name}: {license_identifier} - Score: {score} (Always Allowed)"
        )
        return result

    def _create_unknown_status_result(self, license_identifier: str) -> Dict[str, Any]:
        """Create result for licenses with unknown status"""
        return {
            "score": 0,
            "license_status": None,
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
        """Parse a license expression to extract individual license identifiers with improved boolean logic"""
        if not license_expression:
            return []
        
        # Normalize the expression
        expression = license_expression.strip()
        
        # Handle nested parentheses and complex expressions
        licenses = self._parse_complex_expression(expression)

        # Clean up each license identifier
        cleaned_licenses = []
        for license in licenses:
            cleaned_license = license.strip().strip('"').strip("'")
            if cleaned_license and cleaned_license not in ["OR", "AND", "|", "&", "(", ")"]:
                cleaned_licenses.append(cleaned_license)

        return cleaned_licenses

    def _parse_complex_expression(self, expression: str) -> List[str]:
        """Parse complex license expressions with proper handling of parentheses and operators"""
        licenses = []
        current_license = ""
        paren_depth = 0
        i = 0
        
        while i < len(expression):
            char = expression[i]
            
            if char == "(":
                paren_depth += 1
                if paren_depth == 1 and current_license.strip():
                    # We're entering a nested expression, save current license
                    licenses.append(current_license.strip())
                    current_license = ""
            elif char == ")":
                paren_depth -= 1
                if paren_depth == 0 and current_license.strip():
                    # We're exiting a nested expression, save current license
                    licenses.append(current_license.strip())
                    current_license = ""
            elif paren_depth == 0:
                # We're at the top level, check for operators
                if self._is_operator_at_position(expression, i):
                    if current_license.strip():
                        licenses.append(current_license.strip())
                        current_license = ""
                    # Skip the operator and any following whitespace
                    i = self._skip_operator_and_whitespace(expression, i)
                    continue
                else:
                    current_license += char
            else:
                # We're inside parentheses, just collect characters
                current_license += char
            
            i += 1
        
        # Add the last license if there is one
        if current_license.strip():
            licenses.append(current_license.strip())
        
        return licenses

    def _is_operator_at_position(self, expression: str, position: int) -> bool:
        """Check if there's an operator at the given position"""
        operators = [" OR ", " AND ", "|", "&"]
        
        for operator in operators:
            if expression[position:position + len(operator)].upper() == operator.upper():
                return True
        
        return False

    def _skip_operator_and_whitespace(self, expression: str, position: int) -> int:
        """Skip the operator and any following whitespace, return new position"""
        operators = [" OR ", " AND ", "|", "&"]
        
        for operator in operators:
            if expression[position:position + len(operator)].upper() == operator.upper():
                return position + len(operator)
        
        # Single character operators
        if expression[position] in ["|", "&"]:
            return position + 1
        
        return position

    def _validate_or_expression(
        self,
        individual_licenses: List[str],
        original_expression: str,
        package_name: str,
    ) -> Dict[str, Any]:
        """Validate OR expression - use the best (highest scoring) license with improved edge case handling"""
        if not individual_licenses:
            return {
                "score": 0,
                "license_status": None,
                "errors": ["Empty OR expression"],
                "warnings": [],
            }
        
        best_score = -1  # Start with -1 to handle score 0 licenses
        best_result = None
        all_errors = []
        all_warnings = []
        valid_licenses = []
        invalid_licenses = []

        for license_id in individual_licenses:
            if not license_id or not license_id.strip():
                continue
                
            # Look up each license
            license = self._lookup_license_in_db(license_id.strip())
            if license:
                result = self._validate_license_status(
                    license, license_id.strip(), package_name
                )
                valid_licenses.append((license_id.strip(), result))
                
                if result["score"] > best_score:
                    best_score = result["score"]
                    best_result = result
            else:
                invalid_licenses.append(license_id.strip())
                all_errors.append(f'License "{license_id.strip()}" is not recognized')
                all_warnings.append(
                    f'License "{license_id.strip()}" is not in the license database'
                )

        if best_result:
            # Add information about the OR expression and other valid licenses
            if len(valid_licenses) > 1:
                other_licenses = [lid for lid, _ in valid_licenses if lid != best_result.get("license_identifier", "")]
                if other_licenses:
                    best_result["warnings"].append(
                        f"OR expression contains {len(valid_licenses)} valid licenses, using best: {best_result.get('license_identifier', 'Unknown')}"
                    )
                    best_result["warnings"].append(
                        f"Other valid licenses in expression: {', '.join(other_licenses)}"
                    )
            
            if invalid_licenses:
                best_result["warnings"].append(
                    f"Some licenses in OR expression were not recognized: {', '.join(invalid_licenses)}"
                )
            
            return best_result
        else:
            # No valid licenses found
            return {
                "score": 0,
                "license_status": None,
                "errors": all_errors + ["No valid licenses found in OR expression"],
                "warnings": all_warnings + [f"OR expression '{original_expression}' contains no recognized licenses"],
            }

    def validate_packages_batch(self, packages_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate multiple packages' licenses in batch for improved performance
        
        Args:
            packages_data: List of package data dictionaries
            
        Returns:
            List of validation results in the same order as input
        """
        try:
            # Load license cache if not already loaded
            if not self._cache_loaded:
                self._load_license_cache()
            
            # Extract unique license identifiers from all packages
            unique_licenses = set()
            for package_data in packages_data:
                license_identifier = self._parse_license_info(package_data)
                if license_identifier:
                    unique_licenses.add(license_identifier)
            
            # Batch lookup all unique licenses
            self._batch_lookup_licenses(list(unique_licenses))
            
            # Process each package using cached license data
            results = []
            for package_data in packages_data:
                result = self._validate_package_license_cached(package_data)
                results.append(result)
            
            self.logger.debug(f"Batch validated {len(packages_data)} packages with {len(unique_licenses)} unique licenses")
            return results
            
        except Exception as e:
            self.logger.error(f"Error in batch license validation: {str(e)}")
            # Fallback to individual validation
            return [self.validate_package_license(package_data) for package_data in packages_data]

    def _load_license_cache(self) -> None:
        """Load all supported licenses into cache for faster lookups"""
        try:
            licenses = SupportedLicense.query.all()
            for license in licenses:
                self._license_cache[license.identifier] = license
                # Also cache common variations
                variations = self._generate_license_variations(license.identifier)
                for variation in variations:
                    if variation not in self._license_cache:
                        self._license_cache[variation] = license
            
            self._cache_loaded = True
            self.logger.info(f"Loaded {len(licenses)} licenses into cache with {len(self._license_cache)} total entries")
            
        except Exception as e:
            self.logger.error(f"Error loading license cache: {str(e)}")
            self._cache_loaded = False

    def _generate_license_variations(self, license_identifier: str) -> List[str]:
        """Generate common variations of a license identifier for caching"""
        variations = [
            license_identifier.lower(),
            license_identifier.upper(),
            license_identifier.replace("-", " "),
            license_identifier.replace(" ", "-"),
            license_identifier.replace("_", "-"),
            license_identifier.replace("_", " "),
        ]
        return [v for v in variations if v != license_identifier]

    def _batch_lookup_licenses(self, license_identifiers: List[str]) -> None:
        """Batch lookup licenses that aren't already in cache"""
        try:
            # Find licenses not in cache
            missing_licenses = [lid for lid in license_identifiers if lid not in self._license_cache]
            
            if not missing_licenses:
                return
            
            # Batch query for missing licenses
            licenses = SupportedLicense.query.filter(
                SupportedLicense.identifier.in_(missing_licenses)
            ).all()
            
            # Add to cache
            for license in licenses:
                self._license_cache[license.identifier] = license
                # Cache variations
                variations = self._generate_license_variations(license.identifier)
                for variation in variations:
                    if variation not in self._license_cache:
                        self._license_cache[variation] = license
            
            # Mark missing licenses as None in cache
            found_identifiers = {license.identifier for license in licenses}
            for missing_license in missing_licenses:
                if missing_license not in found_identifiers:
                    self._license_cache[missing_license] = None
            
            self.logger.debug(f"Batch looked up {len(missing_licenses)} licenses, found {len(licenses)}")
            
        except Exception as e:
            self.logger.error(f"Error in batch license lookup: {str(e)}")

    def _validate_package_license_cached(self, package_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate package license using cached license data"""
        try:
            # Parse license information from package data
            license_identifier = self._parse_license_info(package_data)
            package_name = package_data.get("name", "Unknown")

            # Handle missing license
            if not license_identifier:
                return self._create_no_license_result()

            # Check if this is a complex license expression
            if self._is_complex_license_expression(license_identifier):
                return self._validate_complex_license_expression_cached(
                    license_identifier, package_name
                )

            # Look up license in cache
            license = self._license_cache.get(license_identifier)
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

    def _validate_complex_license_expression_cached(
        self, license_expression: str, package_name: str
    ) -> Dict[str, Any]:
        """Validate complex license expressions using cached data"""
        try:
            # Parse the license expression to extract individual licenses
            individual_licenses = self._parse_license_expression(license_expression)

            if not individual_licenses:
                return self._create_unknown_license_result(license_expression)

            # For OR expressions, use the best (highest scoring) license
            # For AND expressions, use the worst (lowest scoring) license
            if " OR " in license_expression.upper() or "|" in license_expression:
                return self._validate_or_expression_cached(
                    individual_licenses, license_expression, package_name
                )
            elif " AND " in license_expression.upper() or "&" in license_expression:
                return self._validate_and_expression_cached(
                    individual_licenses, license_expression, package_name
                )
            else:
                # Default to OR behavior for complex expressions
                return self._validate_or_expression_cached(
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

    def _validate_or_expression_cached(
        self,
        individual_licenses: List[str],
        original_expression: str,
        package_name: str,
    ) -> Dict[str, Any]:
        """Validate OR expression using cached license data"""
        best_score = 0
        best_result = None
        all_errors = []
        all_warnings = []

        for license_id in individual_licenses:
            # Look up each license in cache
            license = self._license_cache.get(license_id)
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
                "license_status": None,
                "errors": all_errors,
                "warnings": all_warnings,
            }

    def _validate_and_expression_cached(
        self,
        individual_licenses: List[str],
        original_expression: str,
        package_name: str,
    ) -> Dict[str, Any]:
        """Validate AND expression using cached license data"""
        worst_score = 100
        worst_result = None
        all_errors = []
        all_warnings = []
        valid_licenses = []

        for license_id in individual_licenses:
            # Look up each license in cache
            license = self._license_cache.get(license_id)
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
                "license_status": None,
                "errors": all_errors,
                "warnings": all_warnings,
            }

    def _validate_and_expression(
        self,
        individual_licenses: List[str],
        original_expression: str,
        package_name: str,
    ) -> Dict[str, Any]:
        """Validate AND expression - use the worst (lowest scoring) license with improved edge case handling"""
        if not individual_licenses:
            return {
                "score": 0,
                "license_status": None,
                "errors": ["Empty AND expression"],
                "warnings": [],
            }
        
        worst_score = 101  # Start with 101 to handle score 100 licenses
        worst_result = None
        all_errors = []
        all_warnings = []
        valid_licenses = []
        invalid_licenses = []

        for license_id in individual_licenses:
            if not license_id or not license_id.strip():
                continue
                
            # Look up each license
            license = self._lookup_license_in_db(license_id.strip())
            if license:
                result = self._validate_license_status(
                    license, license_id.strip(), package_name
                )
                valid_licenses.append((license_id.strip(), result))
                
                if result["score"] < worst_score:
                    worst_score = result["score"]
                    worst_result = result
            else:
                invalid_licenses.append(license_id.strip())
                all_errors.append(f'License "{license_id.strip()}" is not recognized')
                all_warnings.append(
                    f'License "{license_id.strip()}" is not in the license database'
                )

        if worst_result:
            # Add information about the AND expression and all licenses
            if len(valid_licenses) > 1:
                all_license_scores = [f"{lid}({result['score']})" for lid, result in valid_licenses]
                worst_result["warnings"].append(
                    f"AND expression contains {len(valid_licenses)} licenses, using worst: {worst_result.get('license_identifier', 'Unknown')}"
                )
                worst_result["warnings"].append(
                    f"All license scores in expression: {', '.join(all_license_scores)}"
                )
            
            if invalid_licenses:
                worst_result["warnings"].append(
                    f"Some licenses in AND expression were not recognized: {', '.join(invalid_licenses)}"
                )
                # For AND expressions, any unrecognized license should fail the entire expression
                worst_result["score"] = 0
                worst_result["errors"].append("AND expression contains unrecognized licenses")
            
            return worst_result
        else:
            # No valid licenses found
            return {
                "score": 0,
                "license_status": None,
                "errors": all_errors + ["No valid licenses found in AND expression"],
                "warnings": all_warnings + [f"AND expression '{original_expression}' contains no recognized licenses"],
            }