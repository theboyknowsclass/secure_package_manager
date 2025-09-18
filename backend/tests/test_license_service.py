#!/usr/bin/env python3
"""
Comprehensive test suite for license validation service.
Tests various npm license field formats and complex expressions.
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch

# Add the parent directory to the path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models import SupportedLicense
from services.license_service import LicenseService


class TestLicenseService(unittest.TestCase):
    """Test suite for LicenseService"""

    def setUp(self):
        """Set up test fixtures"""
        self.license_service = LicenseService()

        # Mock database models for testing
        self.mock_mit_license = Mock(spec=SupportedLicense)
        self.mock_mit_license.identifier = "MIT"
        self.mock_mit_license.status = "always_allowed"

        self.mock_apache_license = Mock(spec=SupportedLicense)
        self.mock_apache_license.identifier = "Apache-2.0"
        self.mock_apache_license.status = "always_allowed"

        self.mock_cc0_license = Mock(spec=SupportedLicense)
        self.mock_cc0_license.identifier = "CC0-1.0"
        self.mock_cc0_license.status = "allowed"

        self.mock_gpl_license = Mock(spec=SupportedLicense)
        self.mock_gpl_license.identifier = "GPL-3.0"
        self.mock_gpl_license.status = "avoid"

        self.mock_blocked_license = Mock(spec=SupportedLicense)
        self.mock_blocked_license.identifier = "GPL"
        self.mock_blocked_license.status = "blocked"

    def test_single_spdx_identifier_mit(self):
        """Test single SPDX identifier: MIT"""
        package_data = {"name": "test-package", "license": "MIT"}

        with patch.object(
            self.license_service,
            "_lookup_license_in_db",
            return_value=self.mock_mit_license,
        ):
            result = self.license_service.validate_package_license(package_data)

            self.assertEqual(result["score"], 100)
            self.assertEqual(len(result["errors"]), 0)
            self.assertEqual(len(result["warnings"]), 0)

    def test_single_spdx_identifier_apache(self):
        """Test single SPDX identifier: Apache-2.0"""
        package_data = {"name": "test-package", "license": "Apache-2.0"}

        with patch.object(
            self.license_service,
            "_lookup_license_in_db",
            return_value=self.mock_apache_license,
        ):
            result = self.license_service.validate_package_license(package_data)

            self.assertEqual(result["score"], 100)
            self.assertEqual(len(result["errors"]), 0)
            self.assertEqual(len(result["warnings"]), 0)

    def test_single_spdx_identifier_cc0(self):
        """Test single SPDX identifier: CC0-1.0"""
        package_data = {"name": "test-package", "license": "CC0-1.0"}

        with patch.object(
            self.license_service,
            "_lookup_license_in_db",
            return_value=self.mock_cc0_license,
        ):
            result = self.license_service.validate_package_license(package_data)

            self.assertEqual(result["score"], 80)
            self.assertEqual(len(result["errors"]), 0)
            self.assertEqual(len(result["warnings"]), 0)

    def test_single_spdx_identifier_gpl_avoid(self):
        """Test single SPDX identifier: GPL-3.0 (avoid status)"""
        package_data = {"name": "test-package", "license": "GPL-3.0"}

        with patch.object(
            self.license_service,
            "_lookup_license_in_db",
            return_value=self.mock_gpl_license,
        ):
            result = self.license_service.validate_package_license(package_data)

            self.assertEqual(result["score"], 30)
            self.assertEqual(len(result["errors"]), 0)
            self.assertGreater(len(result["warnings"]), 0)

    def test_single_spdx_identifier_blocked(self):
        """Test single SPDX identifier: GPL (blocked status)"""
        package_data = {"name": "test-package", "license": "GPL"}

        with patch.object(
            self.license_service,
            "_lookup_license_in_db",
            return_value=self.mock_blocked_license,
        ):
            result = self.license_service.validate_package_license(package_data)

            self.assertEqual(result["score"], 0)
            self.assertGreater(len(result["errors"]), 0)
            self.assertGreater(len(result["warnings"]), 0)

    def test_license_array_format(self):
        """Test license field as array (legacy format)"""
        package_data = {"name": "test-package", "license": ["MIT", "Apache-2.0"]}

        with patch.object(
            self.license_service,
            "_lookup_license_in_db",
            return_value=self.mock_mit_license,
        ):
            result = self.license_service.validate_package_license(package_data)

            self.assertEqual(result["score"], 100)
            self.assertEqual(len(result["errors"]), 0)

    def test_license_object_format(self):
        """Test license field as object with type"""
        package_data = {
            "name": "test-package",
            "license": {"type": "MIT", "url": "https://opensource.org/licenses/MIT"},
        }

        with patch.object(
            self.license_service,
            "_lookup_license_in_db",
            return_value=self.mock_mit_license,
        ):
            result = self.license_service.validate_package_license(package_data)

            self.assertEqual(result["score"], 100)
            self.assertEqual(len(result["errors"]), 0)

    def test_missing_license(self):
        """Test package with no license information"""
        package_data = {"name": "test-package"}

        result = self.license_service.validate_package_license(package_data)

        self.assertEqual(result["score"], 0)
        self.assertGreater(len(result["errors"]), 0)
        self.assertGreater(len(result["warnings"]), 0)

    def test_empty_license_string(self):
        """Test package with empty license string"""
        package_data = {"name": "test-package", "license": ""}

        result = self.license_service.validate_package_license(package_data)

        self.assertEqual(result["score"], 0)
        self.assertGreater(len(result["errors"]), 0)

    def test_unknown_license(self):
        """Test package with unknown license"""
        package_data = {"name": "test-package", "license": "UNKNOWN-LICENSE"}

        with patch.object(self.license_service, "_lookup_license_in_db", return_value=None):
            result = self.license_service.validate_package_license(package_data)

            self.assertEqual(result["score"], 50)
            self.assertGreater(len(result["errors"]), 0)
            self.assertGreater(len(result["warnings"]), 0)

    def test_or_expression_simple(self):
        """Test OR expression: MIT OR Apache-2.0"""
        package_data = {"name": "test-package", "license": "MIT OR Apache-2.0"}

        def mock_lookup(license_id):
            if license_id == "MIT":
                return self.mock_mit_license
            elif license_id == "Apache-2.0":
                return self.mock_apache_license
            return None

        with patch.object(self.license_service, "_lookup_license_in_db", side_effect=mock_lookup):
            result = self.license_service.validate_package_license(package_data)

            self.assertEqual(result["score"], 100)  # Should use best license (MIT)
            self.assertEqual(len(result["errors"]), 0)
            self.assertGreater(len(result["warnings"]), 0)  # Should have warning about OR expression

    def test_or_expression_with_parentheses(self):
        """Test OR expression with parentheses: (MIT OR CC0-1.0)"""
        package_data = {"name": "test-package", "license": "(MIT OR CC0-1.0)"}

        def mock_lookup(license_id):
            if license_id == "MIT":
                return self.mock_mit_license
            elif license_id == "CC0-1.0":
                return self.mock_cc0_license
            return None

        with patch.object(self.license_service, "_lookup_license_in_db", side_effect=mock_lookup):
            result = self.license_service.validate_package_license(package_data)

            self.assertEqual(result["score"], 100)  # Should use best license (MIT)
            self.assertEqual(len(result["errors"]), 0)
            self.assertGreater(len(result["warnings"]), 0)

    def test_or_expression_alternative_syntax(self):
        """Test OR expression with alternative syntax: MIT | Apache-2.0"""
        package_data = {"name": "test-package", "license": "MIT | Apache-2.0"}

        def mock_lookup(license_id):
            if license_id == "MIT":
                return self.mock_mit_license
            elif license_id == "Apache-2.0":
                return self.mock_apache_license
            return None

        with patch.object(self.license_service, "_lookup_license_in_db", side_effect=mock_lookup):
            result = self.license_service.validate_package_license(package_data)

            self.assertEqual(result["score"], 100)  # Should use best license (MIT)
            self.assertEqual(len(result["errors"]), 0)
            self.assertGreater(len(result["warnings"]), 0)

    def test_and_expression(self):
        """Test AND expression: MIT AND GPL-3.0"""
        package_data = {"name": "test-package", "license": "MIT AND GPL-3.0"}

        def mock_lookup(license_id):
            if license_id == "MIT":
                return self.mock_mit_license
            elif license_id == "GPL-3.0":
                return self.mock_gpl_license
            return None

        with patch.object(self.license_service, "_lookup_license_in_db", side_effect=mock_lookup):
            result = self.license_service.validate_package_license(package_data)

            self.assertEqual(result["score"], 30)  # Should use worst license (GPL-3.0)
            self.assertEqual(len(result["errors"]), 0)
            self.assertGreater(len(result["warnings"]), 0)  # Should have warning about AND expression

    def test_and_expression_alternative_syntax(self):
        """Test AND expression with alternative syntax: MIT & GPL-3.0"""
        package_data = {"name": "test-package", "license": "MIT & GPL-3.0"}

        def mock_lookup(license_id):
            if license_id == "MIT":
                return self.mock_mit_license
            elif license_id == "GPL-3.0":
                return self.mock_gpl_license
            return None

        with patch.object(self.license_service, "_lookup_license_in_db", side_effect=mock_lookup):
            result = self.license_service.validate_package_license(package_data)

            self.assertEqual(result["score"], 30)  # Should use worst license (GPL-3.0)
            self.assertEqual(len(result["errors"]), 0)
            self.assertGreater(len(result["warnings"]), 0)

    def test_complex_expression_multiple_or(self):
        """Test complex expression with multiple OR: MIT OR CC0-1.0 OR Apache-2.0"""
        package_data = {
            "name": "test-package",
            "license": "MIT OR CC0-1.0 OR Apache-2.0",
        }

        def mock_lookup(license_id):
            if license_id == "MIT":
                return self.mock_mit_license
            elif license_id == "CC0-1.0":
                return self.mock_cc0_license
            elif license_id == "Apache-2.0":
                return self.mock_apache_license
            return None

        with patch.object(self.license_service, "_lookup_license_in_db", side_effect=mock_lookup):
            result = self.license_service.validate_package_license(package_data)

            self.assertEqual(result["score"], 100)  # Should use best license (MIT)
            self.assertEqual(len(result["errors"]), 0)
            self.assertGreater(len(result["warnings"]), 0)

    def test_or_expression_with_unknown_license(self):
        """Test OR expression where one license is unknown: MIT OR UNKNOWN"""
        package_data = {"name": "test-package", "license": "MIT OR UNKNOWN"}

        def mock_lookup(license_id):
            if license_id == "MIT":
                return self.mock_mit_license
            elif license_id == "UNKNOWN":
                return None
            return None

        with patch.object(self.license_service, "_lookup_license_in_db", side_effect=mock_lookup):
            result = self.license_service.validate_package_license(package_data)

            self.assertEqual(result["score"], 100)  # Should use known license (MIT)
            self.assertEqual(len(result["errors"]), 0)
            self.assertGreater(len(result["warnings"]), 0)

    def test_or_expression_all_unknown(self):
        """Test OR expression where all licenses are unknown"""
        package_data = {"name": "test-package", "license": "UNKNOWN1 OR UNKNOWN2"}

        with patch.object(self.license_service, "_lookup_license_in_db", return_value=None):
            result = self.license_service.validate_package_license(package_data)

            self.assertEqual(result["score"], 0)
            self.assertGreater(len(result["errors"]), 0)
            self.assertGreater(len(result["warnings"]), 0)

    def test_see_license_in_file(self):
        """Test 'SEE LICENSE IN' format"""
        package_data = {"name": "test-package", "license": "SEE LICENSE IN LICENSE.txt"}

        with patch.object(self.license_service, "_lookup_license_in_db", return_value=None):
            result = self.license_service.validate_package_license(package_data)

            self.assertEqual(result["score"], 0)
            self.assertGreater(len(result["errors"]), 0)
            self.assertGreater(len(result["warnings"]), 0)

    def test_unlicensed(self):
        """Test 'UNLICENSED' format"""
        package_data = {"name": "test-package", "license": "UNLICENSED"}

        with patch.object(self.license_service, "_lookup_license_in_db", return_value=None):
            result = self.license_service.validate_package_license(package_data)

            self.assertEqual(result["score"], 0)
            self.assertGreater(len(result["errors"]), 0)
            self.assertGreater(len(result["warnings"]), 0)

    def test_license_with_extra_spaces(self):
        """Test license with extra spaces: '  MIT  '"""
        package_data = {"name": "test-package", "license": "  MIT  "}

        with patch.object(
            self.license_service,
            "_lookup_license_in_db",
            return_value=self.mock_mit_license,
        ):
            result = self.license_service.validate_package_license(package_data)

            self.assertEqual(result["score"], 100)
            self.assertEqual(len(result["errors"]), 0)

    def test_license_case_insensitive(self):
        """Test license case handling: 'mit' should work like 'MIT'"""
        package_data = {"name": "test-package", "license": "mit"}

        with patch.object(
            self.license_service,
            "_lookup_license_in_db",
            return_value=self.mock_mit_license,
        ):
            result = self.license_service.validate_package_license(package_data)

            self.assertEqual(result["score"], 100)
            self.assertEqual(len(result["errors"]), 0)

    def test_license_with_hyphens_and_underscores(self):
        """Test license with different separators: 'Apache_2.0' vs 'Apache-2.0'"""
        package_data = {"name": "test-package", "license": "Apache_2.0"}

        # Mock the variation finding logic
        with patch.object(
            self.license_service,
            "_find_license_variation",
            return_value=self.mock_apache_license,
        ):
            with patch.object(self.license_service, "_lookup_license_in_db", return_value=None):
                result = self.license_service.validate_package_license(package_data)

                self.assertEqual(result["score"], 100)
                self.assertEqual(len(result["errors"]), 0)

    def test_license_score_calculation(self):
        """Test license score calculation for different statuses"""
        # Test always_allowed
        score = self.license_service._calculate_license_score(self.mock_mit_license)
        self.assertEqual(score, 100)

        # Test allowed
        self.mock_cc0_license.status = "allowed"
        score = self.license_service._calculate_license_score(self.mock_cc0_license)
        self.assertEqual(score, 80)

        # Test avoid
        score = self.license_service._calculate_license_score(self.mock_gpl_license)
        self.assertEqual(score, 30)

        # Test blocked
        score = self.license_service._calculate_license_score(self.mock_blocked_license)
        self.assertEqual(score, 0)

    def test_is_complex_license_expression(self):
        """Test detection of complex license expressions"""
        # Simple licenses
        self.assertFalse(self.license_service._is_complex_license_expression("MIT"))
        self.assertFalse(self.license_service._is_complex_license_expression("Apache-2.0"))

        # Complex expressions
        self.assertTrue(self.license_service._is_complex_license_expression("MIT OR Apache-2.0"))
        self.assertTrue(self.license_service._is_complex_license_expression("MIT AND Apache-2.0"))
        self.assertTrue(self.license_service._is_complex_license_expression("(MIT OR Apache-2.0)"))
        self.assertTrue(self.license_service._is_complex_license_expression("MIT | Apache-2.0"))
        self.assertTrue(self.license_service._is_complex_license_expression("MIT & Apache-2.0"))

        # Edge cases
        self.assertFalse(self.license_service._is_complex_license_expression(""))
        self.assertFalse(self.license_service._is_complex_license_expression(None))

    def test_parse_license_expression(self):
        """Test parsing of license expressions"""
        # OR expression
        licenses = self.license_service._parse_license_expression("MIT OR Apache-2.0")
        self.assertEqual(licenses, ["MIT", "Apache-2.0"])

        # AND expression
        licenses = self.license_service._parse_license_expression("MIT AND GPL-3.0")
        self.assertEqual(licenses, ["MIT", "GPL-3.0"])

        # With parentheses
        licenses = self.license_service._parse_license_expression("(MIT OR CC0-1.0)")
        self.assertEqual(licenses, ["MIT", "CC0-1.0"])

        # Alternative syntax
        licenses = self.license_service._parse_license_expression("MIT | Apache-2.0")
        self.assertEqual(licenses, ["MIT", "Apache-2.0"])

        # Multiple OR
        licenses = self.license_service._parse_license_expression("MIT OR CC0-1.0 OR Apache-2.0")
        self.assertEqual(licenses, ["MIT", "CC0-1.0", "Apache-2.0"])

        # Single license
        licenses = self.license_service._parse_license_expression("MIT")
        self.assertEqual(licenses, ["MIT"])

    def test_validation_error_handling(self):
        """Test error handling in validation"""
        package_data = {"name": "test-package", "license": "MIT"}

        # Mock an exception in the validation process
        with patch.object(
            self.license_service,
            "_lookup_license_in_db",
            side_effect=Exception("Database error"),
        ):
            result = self.license_service.validate_package_license(package_data)

            self.assertEqual(result["score"], 0)
            self.assertGreater(len(result["errors"]), 0)
            self.assertIn("License validation failed", result["errors"][0])


class TestLicenseServiceIntegration(unittest.TestCase):
    """Integration tests for LicenseService with real database models"""

    def setUp(self):
        """Set up integration test fixtures"""
        self.license_service = LicenseService()

    def test_license_variation_finding(self):
        """Test finding license variations"""
        # This would require a real database connection
        # For now, we'll test the logic with mocked data

    def test_license_database_lookup(self):
        """Test actual database lookup"""
        # This would require a real database connection
        # For now, we'll test the logic with mocked data


if __name__ == "__main__":
    # Run the tests
    unittest.main(verbosity=2)
