#!/usr/bin/env python3
"""
Test suite for various npm license field formats.
Based on real-world examples from npm packages.
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch

# Add the parent directory to the path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.license_service import LicenseService


class TestNpmLicenseFormats(unittest.TestCase):
    """Test suite for various npm license field formats"""

    def setUp(self):
        """Set up test fixtures"""
        self.license_service = LicenseService()

        # Mock common licenses
        self.mock_mit = Mock()
        self.mock_mit.identifier = "MIT"
        self.mock_mit.status = "always_allowed"

        self.mock_apache = Mock()
        self.mock_apache.identifier = "Apache-2.0"
        self.mock_apache.status = "always_allowed"

        self.mock_bsd = Mock()
        self.mock_bsd.identifier = "BSD"
        self.mock_bsd.status = "always_allowed"

        self.mock_isc = Mock()
        self.mock_isc.identifier = "ISC"
        self.mock_isc.status = "allowed"

        self.mock_0bsd = Mock()
        self.mock_0bsd.identifier = "0BSD"
        self.mock_0bsd.status = "allowed"

    def test_common_spdx_identifiers(self):
        """Test common SPDX license identifiers"""
        common_licenses = [
            "MIT",
            "Apache-2.0",
            "BSD-2-Clause",
            "BSD-3-Clause",
            "ISC",
            "0BSD",
            "Unlicense",
            "CC0-1.0",
            "LGPL-2.1",
            "LGPL-3.0",
            "GPL-2.0",
            "GPL-3.0",
            "AGPL-3.0",
            "MPL-2.0",
            "EPL-1.0",
            "EPL-2.0",
        ]

        for license_id in common_licenses:
            with self.subTest(license=license_id):
                package_data = {"name": "test-package", "license": license_id}

                # Mock successful lookup for known licenses
                with patch.object(
                    self.license_service,
                    "_lookup_license_in_db",
                    return_value=self.mock_mit,
                ):
                    result = self.license_service.validate_package_license(package_data)

                    # Should not have errors for valid SPDX identifiers
                    self.assertIsInstance(result, dict)
                    self.assertIn("score", result)
                    self.assertIn("errors", result)
                    self.assertIn("warnings", result)

    def test_legacy_licenses_array_format(self):
        """Test legacy licenses array format"""
        package_data = {
            "name": "test-package",
            "licenses": [
                {"type": "MIT", "url": "https://opensource.org/licenses/MIT"},
                {
                    "type": "Apache-2.0",
                    "url": "https://opensource.org/licenses/Apache-2.0",
                },
            ],
        }

        # The current implementation doesn't handle the "licenses" field
        # This test documents the limitation
        with patch.object(
            self.license_service, "_lookup_license_in_db", return_value=None
        ):
            result = self.license_service.validate_package_license(package_data)

            # Should return no license result since "license" field is missing
            self.assertEqual(result["score"], 0)
            self.assertGreater(len(result["errors"]), 0)

    def test_license_with_url_object(self):
        """Test license object with URL"""
        package_data = {
            "name": "test-package",
            "license": {"type": "MIT", "url": "https://opensource.org/licenses/MIT"},
        }

        with patch.object(
            self.license_service, "_lookup_license_in_db", return_value=self.mock_mit
        ):
            result = self.license_service.validate_package_license(package_data)

            self.assertEqual(result["score"], 100)
            self.assertEqual(len(result["errors"]), 0)

    def test_see_license_variations(self):
        """Test various 'SEE LICENSE IN' formats"""
        see_license_formats = [
            "SEE LICENSE IN LICENSE.txt",
            "SEE LICENSE IN LICENSE",
            "SEE LICENSE IN LICENSE.md",
            "SEE LICENSE IN COPYING",
            "SEE LICENSE IN COPYING.txt",
            "SEE LICENSE IN LICENCE",
            "SEE LICENSE IN LICENCE.txt",
        ]

        for license_format in see_license_formats:
            with self.subTest(license=license_format):
                package_data = {"name": "test-package", "license": license_format}

                with patch.object(
                    self.license_service, "_lookup_license_in_db", return_value=None
                ):
                    result = self.license_service.validate_package_license(package_data)

                    # Should be treated as unknown license
                    self.assertEqual(result["score"], 0)
                    self.assertGreater(len(result["errors"]), 0)

    def test_unlicensed_variations(self):
        """Test various unlicensed formats"""
        unlicensed_formats = [
            "UNLICENSED",
            "unlicensed",
            "Unlicensed",
            "UNLICENCED",  # Common typo
            "Proprietary",
            "proprietary",
            "Private",
            "private",
        ]

        for license_format in unlicensed_formats:
            with self.subTest(license=license_format):
                package_data = {"name": "test-package", "license": license_format}

                with patch.object(
                    self.license_service, "_lookup_license_in_db", return_value=None
                ):
                    result = self.license_service.validate_package_license(package_data)

                    # Should be treated as unknown license
                    self.assertEqual(result["score"], 0)
                    self.assertGreater(len(result["errors"]), 0)

    def test_custom_license_strings(self):
        """Test custom license strings"""
        custom_licenses = [
            "Custom License",
            "Custom",
            "All Rights Reserved",
            "Commercial",
            "Free for non-commercial use",
            "MIT-like",
            "BSD-like",
            "GPL-like",
        ]

        for license_format in custom_licenses:
            with self.subTest(license=license_format):
                package_data = {"name": "test-package", "license": license_format}

                with patch.object(
                    self.license_service, "_lookup_license_in_db", return_value=None
                ):
                    result = self.license_service.validate_package_license(package_data)

                    # Should be treated as unknown license
                    self.assertEqual(result["score"], 0)
                    self.assertGreater(len(result["errors"]), 0)

    def test_license_with_version_numbers(self):
        """Test licenses with version numbers"""
        versioned_licenses = [
            "MIT",
            "Apache-2.0",
            "GPL-2.0",
            "GPL-3.0",
            "LGPL-2.1",
            "LGPL-3.0",
            "AGPL-3.0",
            "MPL-2.0",
            "EPL-1.0",
            "EPL-2.0",
            "BSD-2-Clause",
            "BSD-3-Clause",
            "CC0-1.0",
        ]

        for license_format in versioned_licenses:
            with self.subTest(license=license_format):
                package_data = {"name": "test-package", "license": license_format}

                with patch.object(
                    self.license_service,
                    "_lookup_license_in_db",
                    return_value=self.mock_mit,
                ):
                    result = self.license_service.validate_package_license(package_data)

                    self.assertIsInstance(result, dict)
                    self.assertIn("score", result)

    def test_license_with_plus_sign(self):
        """Test licenses with plus sign (e.g., GPL-2.0+)"""
        plus_licenses = ["GPL-2.0+", "LGPL-2.1+", "GPL-3.0+"]

        for license_format in plus_licenses:
            with self.subTest(license=license_format):
                package_data = {"name": "test-package", "license": license_format}

                with patch.object(
                    self.license_service, "_lookup_license_in_db", return_value=None
                ):
                    result = self.license_service.validate_package_license(package_data)

                    # Should be treated as unknown license
                    self.assertEqual(result["score"], 0)
                    self.assertGreater(len(result["errors"]), 0)

    def test_license_with_only_operator(self):
        """Test license expressions with ONLY operator"""
        only_licenses = ["GPL-2.0-only", "LGPL-2.1-only", "GPL-3.0-only"]

        for license_format in only_licenses:
            with self.subTest(license=license_format):
                package_data = {"name": "test-package", "license": license_format}

                with patch.object(
                    self.license_service, "_lookup_license_in_db", return_value=None
                ):
                    result = self.license_service.validate_package_license(package_data)

                    # Should be treated as unknown license
                    self.assertEqual(result["score"], 0)
                    self.assertGreater(len(result["errors"]), 0)

    def test_license_with_or_later(self):
        """Test license expressions with OR LATER operator"""
        or_later_licenses = [
            "GPL-2.0-or-later",
            "LGPL-2.1-or-later",
            "GPL-3.0-or-later",
        ]

        for license_format in or_later_licenses:
            with self.subTest(license=license_format):
                package_data = {"name": "test-package", "license": license_format}

                with patch.object(
                    self.license_service, "_lookup_license_in_db", return_value=None
                ):
                    result = self.license_service.validate_package_license(package_data)

                    # Should be treated as unknown license
                    self.assertEqual(result["score"], 0)
                    self.assertGreater(len(result["errors"]), 0)

    def test_license_with_with_exception(self):
        """Test license expressions with WITH exception"""
        with_exception_licenses = [
            "GPL-2.0 WITH Classpath-exception-2.0",
            "GPL-3.0 WITH Autoconf-exception-3.0",
        ]

        for license_format in with_exception_licenses:
            with self.subTest(license=license_format):
                package_data = {"name": "test-package", "license": license_format}

                with patch.object(
                    self.license_service, "_lookup_license_in_db", return_value=None
                ):
                    result = self.license_service.validate_package_license(package_data)

                    # Should be treated as unknown license
                    self.assertEqual(result["score"], 0)
                    self.assertGreater(len(result["errors"]), 0)

    def test_empty_and_null_license_values(self):
        """Test empty and null license values"""
        empty_licenses = [None, "", " ", "\t", "\n", "null", "undefined"]

        for license_format in empty_licenses:
            with self.subTest(license=license_format):
                package_data = {"name": "test-package", "license": license_format}

                result = self.license_service.validate_package_license(package_data)

                # Should return no license result
                self.assertEqual(result["score"], 0)
                self.assertGreater(len(result["errors"]), 0)

    def test_license_with_special_characters(self):
        """Test licenses with special characters"""
        special_licenses = [
            "MIT/X11",
            "MIT (X11)",
            "MIT License",
            "Apache License 2.0",
            "BSD License",
            "GNU GPL v2",
            "GNU GPL v3",
            "GNU LGPL v2.1",
            "GNU LGPL v3",
        ]

        for license_format in special_licenses:
            with self.subTest(license=license_format):
                package_data = {"name": "test-package", "license": license_format}

                with patch.object(
                    self.license_service, "_lookup_license_in_db", return_value=None
                ):
                    result = self.license_service.validate_package_license(package_data)

                    # Should be treated as unknown license
                    self.assertEqual(result["score"], 0)
                    self.assertGreater(len(result["errors"]), 0)

    def test_license_array_with_mixed_types(self):
        """Test license array with mixed types"""
        package_data = {
            "name": "test-package",
            "license": [
                "MIT",
                {
                    "type": "Apache-2.0",
                    "url": "https://opensource.org/licenses/Apache-2.0",
                },
                "BSD",
            ],
        }

        with patch.object(
            self.license_service, "_lookup_license_in_db", return_value=self.mock_mit
        ):
            result = self.license_service.validate_package_license(package_data)

            # Should use the first license (MIT)
            self.assertEqual(result["score"], 100)
            self.assertEqual(len(result["errors"]), 0)

    def test_license_object_without_type(self):
        """Test license object without type field"""
        package_data = {
            "name": "test-package",
            "license": {"url": "https://opensource.org/licenses/MIT"},
        }

        with patch.object(
            self.license_service, "_lookup_license_in_db", return_value=None
        ):
            result = self.license_service.validate_package_license(package_data)

            # Should be treated as no license
            self.assertEqual(result["score"], 0)
            self.assertGreater(len(result["errors"]), 0)

    def test_license_object_with_empty_type(self):
        """Test license object with empty type field"""
        package_data = {
            "name": "test-package",
            "license": {"type": "", "url": "https://opensource.org/licenses/MIT"},
        }

        with patch.object(
            self.license_service, "_lookup_license_in_db", return_value=None
        ):
            result = self.license_service.validate_package_license(package_data)

            # Should be treated as no license
            self.assertEqual(result["score"], 0)
            self.assertGreater(len(result["errors"]), 0)


if __name__ == "__main__":
    # Run the tests
    unittest.main(verbosity=2)
