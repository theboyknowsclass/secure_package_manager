"""Tests for LicenseService.

Tests the business logic of license validation and management.
"""

import unittest
from datetime import datetime
from unittest.mock import MagicMock, Mock

from services.license_service import LicenseService


class TestLicenseService(unittest.TestCase):
    """Test cases for LicenseService."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = LicenseService()
        self.mock_ops = self._create_mock_operations()

    def _create_mock_operations(self):
        """Create mock database operations."""
        mock_ops = {
            "supported_license": Mock(),
            "package_status": Mock(),
        }

        # Mock supported license operations
        mock_license = Mock()
        mock_license.name = "MIT"
        mock_license.tier = "Approved"
        mock_ops.supported_license.get_by_name.return_value = mock_license
        mock_ops.supported_license.get_all.return_value = [mock_license]

        # Mock package status operations
        mock_ops.package_status.PackageStatus = Mock()
        mock_ops.package_status.update_package_status.return_value = None

        return mock_ops

    def test_validate_package_license_approved(self):
        """Test validation of an approved license."""
        package_data = {
            "name": "test-package",
            "version": "1.0.0",
            "license": "MIT",
        }

        result = self.service.validate_package_license(
            package_data, self.mock_ops
        )

        self.assertTrue(result["valid"])
        self.assertEqual(result["score"], 100)
        self.assertEqual(result["license_identifier"], "MIT")
        self.assertEqual(result["license_tier"], "Approved")
        self.assertEqual(result["license_name"], "MIT")
        self.assertEqual(result["errors"], [])

    def test_validate_package_license_no_license(self):
        """Test validation of a package with no license."""
        package_data = {"name": "test-package", "version": "1.0.0"}

        result = self.service.validate_package_license(
            package_data, self.mock_ops
        )

        self.assertFalse(result["valid"])
        self.assertEqual(result["score"], 0)
        self.assertEqual(result["license_identifier"], "No License")
        self.assertEqual(result["license_tier"], "Prohibited")
        self.assertEqual(result["license_name"], "No License")
        self.assertIn("Package has no license information", result["errors"])

    def test_validate_package_license_unknown(self):
        """Test validation of an unknown license."""
        package_data = {
            "name": "test-package",
            "version": "1.0.0",
            "license": "Unknown-License",
        }

        # Mock unknown license
        self.mock_ops.supported_license.get_by_name.return_value = None

        result = self.service.validate_package_license(
            package_data, self.mock_ops
        )

        self.assertFalse(result["valid"])
        self.assertEqual(result["score"], 0)
        self.assertEqual(result["license_identifier"], "Unknown-License")
        self.assertEqual(result["license_tier"], "Unknown")
        self.assertEqual(result["license_name"], "Unknown")
        self.assertIn("Unknown license: Unknown-License", result["errors"])

    def test_validate_package_license_complex_expression(self):
        """Test validation of a complex license expression."""
        package_data = {
            "name": "test-package",
            "version": "1.0.0",
            "license": "MIT OR Apache-2.0",
        }

        # Mock licenses for complex expression
        mit_license = Mock()
        mit_license.name = "MIT"
        mit_license.tier = "Approved"

        apache_license = Mock()
        apache_license.name = "Apache-2.0"
        apache_license.tier = "Approved"

        def mock_get_by_name(name):
            if name == "MIT":
                return mit_license
            elif name == "Apache-2.0":
                return apache_license
            return None

        self.mock_ops.supported_license.get_by_name.side_effect = (
            mock_get_by_name
        )

        result = self.service.validate_package_license(
            package_data, self.mock_ops
        )

        self.assertTrue(result["valid"])
        self.assertEqual(
            result["score"], 100
        )  # Both are approved, so score is 100
        self.assertEqual(result["license_identifier"], "MIT OR Apache-2.0")
        self.assertEqual(result["license_tier"], "Approved")

    def test_validate_package_license_license_object(self):
        """Test validation with license as an object."""
        package_data = {
            "name": "test-package",
            "version": "1.0.0",
            "license": {"type": "MIT"},
        }

        result = self.service.validate_package_license(
            package_data, self.mock_ops
        )

        self.assertTrue(result["valid"])
        self.assertEqual(result["license_identifier"], "MIT")

    def test_validate_package_license_licenses_array(self):
        """Test validation with licenses as an array."""
        package_data = {
            "name": "test-package",
            "version": "1.0.0",
            "licenses": [{"type": "MIT"}],
        }

        result = self.service.validate_package_license(
            package_data, self.mock_ops
        )

        self.assertTrue(result["valid"])
        self.assertEqual(result["license_identifier"], "MIT")

    def test_process_license_group_success(self):
        """Test successful processing of a license group."""
        # Create mock packages
        package1 = Mock()
        package1.id = 1
        package1.name = "package1"
        package1.version = "1.0.0"
        package1.license = "MIT"

        package2 = Mock()
        package2.id = 2
        package2.name = "package2"
        package2.version = "2.0.0"
        package2.license = "MIT"

        packages = [package1, package2]

        successful, failed = self.service.process_license_group(
            "MIT", packages, self.mock_ops
        )

        self.assertEqual(len(successful), 2)
        self.assertEqual(len(failed), 0)

        # Verify package status updates were called
        self.assertEqual(
            self.mock_ops.package_status.update_package_status.call_count, 2
        )

    def test_process_license_group_failure(self):
        """Test processing of a license group with invalid license."""
        # Create mock packages
        package = Mock()
        package.id = 1
        package.name = "package1"
        package.version = "1.0.0"
        package.license = "Invalid-License"

        packages = [package]

        # Mock unknown license
        self.mock_ops.supported_license.get_by_name.return_value = None

        successful, failed = self.service.process_license_group(
            "Invalid-License", packages, self.mock_ops
        )

        self.assertEqual(len(successful), 0)
        self.assertEqual(len(failed), 1)
        self.assertIn("License validation failed", failed[0]["error"])

    def test_process_package_batch_success(self):
        """Test successful processing of a package batch."""
        # Create mock packages
        package1 = Mock()
        package1.id = 1
        package1.name = "package1"
        package1.version = "1.0.0"
        package1.license = "MIT"

        package2 = Mock()
        package2.id = 2
        package2.name = "package2"
        package2.version = "2.0.0"
        package2.license = "MIT"

        packages = [package1, package2]

        successful, failed = self.service.process_package_batch(
            packages, self.mock_ops
        )

        self.assertEqual(len(successful), 2)
        self.assertEqual(len(failed), 0)

    def test_process_package_batch_mixed_results(self):
        """Test processing of a package batch with mixed results."""
        # Create mock packages
        package1 = Mock()
        package1.id = 1
        package1.name = "package1"
        package1.version = "1.0.0"
        package1.license = "MIT"

        package2 = Mock()
        package2.id = 2
        package2.name = "package2"
        package2.version = "2.0.0"
        package2.license = "Invalid-License"

        packages = [package1, package2]

        # Mock mixed results
        def mock_get_by_name(name):
            if name == "MIT":
                mock_license = Mock()
                mock_license.name = "MIT"
                mock_license.tier = "Approved"
                return mock_license
            return None

        self.mock_ops.supported_license.get_by_name.side_effect = (
            mock_get_by_name
        )

        successful, failed = self.service.process_package_batch(
            packages, self.mock_ops
        )

        self.assertEqual(len(successful), 1)
        self.assertEqual(len(failed), 1)

    def test_extract_individual_licenses(self):
        """Test extraction of individual licenses from complex expressions."""
        # Test OR expression
        licenses = self.service._extract_individual_licenses(
            "MIT OR Apache-2.0"
        )
        self.assertEqual(licenses, ["MIT", "Apache-2.0"])

        # Test AND expression
        licenses = self.service._extract_individual_licenses(
            "MIT AND Apache-2.0"
        )
        self.assertEqual(licenses, ["MIT", "Apache-2.0"])

        # Test with parentheses
        licenses = self.service._extract_individual_licenses(
            "(MIT OR Apache-2.0) AND BSD-3-Clause"
        )
        self.assertEqual(licenses, ["MIT OR Apache-2.0", "BSD-3-Clause"])

    def test_calculate_license_score(self):
        """Test license score calculation."""
        # Test approved license
        approved_license = Mock()
        approved_license.tier = "Approved"
        score = self.service._calculate_license_score(approved_license)
        self.assertEqual(score, 100)

        # Test conditional license
        conditional_license = Mock()
        conditional_license.tier = "Conditional"
        score = self.service._calculate_license_score(conditional_license)
        self.assertEqual(score, 75)

        # Test restricted license
        restricted_license = Mock()
        restricted_license.tier = "Restricted"
        score = self.service._calculate_license_score(restricted_license)
        self.assertEqual(score, 25)

        # Test prohibited license
        prohibited_license = Mock()
        prohibited_license.tier = "Prohibited"
        score = self.service._calculate_license_score(prohibited_license)
        self.assertEqual(score, 0)

        # Test unknown tier
        unknown_license = Mock()
        unknown_license.tier = "Unknown"
        score = self.service._calculate_license_score(unknown_license)
        self.assertEqual(score, 0)

    def test_is_complex_license_expression(self):
        """Test detection of complex license expressions."""
        # Test simple license
        self.assertFalse(self.service._is_complex_license_expression("MIT"))

        # Test OR expression
        self.assertTrue(
            self.service._is_complex_license_expression("MIT OR Apache-2.0")
        )

        # Test AND expression
        self.assertTrue(
            self.service._is_complex_license_expression("MIT AND Apache-2.0")
        )

        # Test with parentheses
        self.assertTrue(
            self.service._is_complex_license_expression("(MIT OR Apache-2.0)")
        )

        # Test with spaces
        self.assertTrue(
            self.service._is_complex_license_expression(
                "MIT OR Apache-2.0 OR BSD-3-Clause"
            )
        )


if __name__ == "__main__":
    unittest.main()
