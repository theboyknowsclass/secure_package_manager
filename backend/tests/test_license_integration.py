#!/usr/bin/env python3
"""
Integration tests for license validation in package processing.
Tests the complete workflow from package data to license score storage.
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch

# Add the parent directory to the path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database.models import Package, SupportedLicense
from services.license_service import LicenseService
from services.package_service import PackageService


class TestLicenseIntegration(unittest.TestCase):
    """Integration tests for license validation in package processing"""

    def setUp(self):
        """Set up test fixtures"""
        self.license_service = LicenseService()
        self.package_service = PackageService()

        # Mock database models
        self.mock_package = Mock(spec=Package)
        self.mock_package.name = "test-package"
        self.mock_package.version = "1.0.0"
        self.mock_package.license_identifier = "MIT"
        self.mock_package.license_score = None
        self.mock_package.validation_errors = []

        # Mock supported licenses
        self.mock_mit_license = Mock(spec=SupportedLicense)
        self.mock_mit_license.identifier = "MIT"
        self.mock_mit_license.status = "always_allowed"

    def test_license_validation_in_package_processing(self):
        """Test that license validation is properly integrated in package processing"""
        # Mock the license service to return a known result
        mock_validation_result = {"score": 100, "errors": [], "warnings": []}

        with patch.object(
            self.license_service,
            "validate_package_license",
            return_value=mock_validation_result,
        ):
            # Mock the package service's license service
            self.package_service.license_service = self.license_service

            # Test the license validation method
            result = self.package_service._validate_package_license(self.mock_package)

            self.assertEqual(result, mock_validation_result)

    def test_license_score_storage_in_validation(self):
        """Test that license score is properly stored during package validation"""
        # Mock the license validation result
        mock_validation_result = {"score": 80, "errors": [], "warnings": []}

        with patch.object(
            self.package_service,
            "_validate_package_license",
            return_value=mock_validation_result,
        ):
            with patch.object(self.package_service, "_simulate_package_download", return_value=True):
                with patch.object(
                    self.package_service,
                    "_create_validation_records",
                    return_value=True,
                ):
                    # Mock database session
                    with patch("services.package_service.db") as mock_db:
                        mock_db.session.commit.return_value = None

                        # Test the validation process
                        result = self.package_service._validate_package_info(self.mock_package)

                        # Verify that license score was set
                        self.assertEqual(self.mock_package.license_score, 80)
                        self.assertTrue(result)

    def test_complex_license_expression_processing(self):
        """Test processing of complex license expressions in package validation"""
        # Set up package with complex license expression
        self.mock_package.license_identifier = "(MIT OR Apache-2.0)"

        # Mock license service to handle complex expressions
        mock_validation_result = {
            "score": 100,
            "errors": [],
            "warnings": ["Using best license from OR expression: (MIT OR Apache-2.0)"],
        }

        with patch.object(
            self.license_service,
            "validate_package_license",
            return_value=mock_validation_result,
        ):
            self.package_service.license_service = self.license_service

            result = self.package_service._validate_package_license(self.mock_package)

            self.assertEqual(result["score"], 100)
            self.assertGreater(len(result["warnings"]), 0)
            self.assertIn("OR expression", result["warnings"][0])

    def test_license_validation_error_handling(self):
        """Test error handling in license validation"""
        # Mock license validation to raise an exception
        with patch.object(
            self.license_service,
            "validate_package_license",
            side_effect=Exception("Database error"),
        ):
            self.package_service.license_service = self.license_service

            result = self.package_service._validate_package_license(self.mock_package)

            # Should return error result
            self.assertEqual(result["score"], 0)
            self.assertGreater(len(result["errors"]), 0)
            self.assertIn("License validation failed", result["errors"][0])

    def test_license_score_zero_handling(self):
        """Test handling of packages with license score 0"""
        # Mock license validation to return score 0
        mock_validation_result = {
            "score": 0,
            "errors": ["License is blocked by policy"],
            "warnings": [],
        }

        with patch.object(
            self.package_service,
            "_validate_package_license",
            return_value=mock_validation_result,
        ):
            with patch.object(self.package_service, "_simulate_package_download", return_value=True):
                with patch.object(
                    self.package_service,
                    "_create_validation_records",
                    return_value=True,
                ):
                    with patch("services.package_service.db") as mock_db:
                        mock_db.session.commit.return_value = None

                        # Test the validation process
                        result = self.package_service._validate_package_info(self.mock_package)

                        # Should still store the score and allow processing (for testing)
                        self.assertEqual(self.mock_package.license_score, 0)
                        self.assertTrue(result)  # Currently allows 0 score for testing

    def test_license_validation_with_missing_license(self):
        """Test validation of packages with missing license information"""
        # Set package with no license
        self.mock_package.license_identifier = None

        # Mock license validation to return no license result
        mock_validation_result = {
            "score": 0,
            "errors": ["No license information found"],
            "warnings": ["Package has no license specified"],
        }

        with patch.object(
            self.license_service,
            "validate_package_license",
            return_value=mock_validation_result,
        ):
            self.package_service.license_service = self.license_service

            result = self.package_service._validate_package_license(self.mock_package)

            self.assertEqual(result["score"], 0)
            self.assertIn("No license information found", result["errors"])

    def test_license_validation_with_unknown_license(self):
        """Test validation of packages with unknown license"""
        # Set package with unknown license
        self.mock_package.license_identifier = "UNKNOWN-LICENSE"

        # Mock license validation to return unknown license result
        mock_validation_result = {
            "score": 50,
            "errors": ['License "UNKNOWN-LICENSE" is not recognized'],
            "warnings": ['License "UNKNOWN-LICENSE" is not in the license database'],
        }

        with patch.object(
            self.license_service,
            "validate_package_license",
            return_value=mock_validation_result,
        ):
            self.package_service.license_service = self.license_service

            result = self.package_service._validate_package_license(self.mock_package)

            self.assertEqual(result["score"], 50)
            self.assertIn("not recognized", result["errors"][0])

    def test_license_validation_workflow_completeness(self):
        """Test the complete license validation workflow"""
        # Test data for various license scenarios
        test_cases = [
            {"license": "MIT", "expected_score": 100, "expected_errors": 0},
            {"license": "Apache-2.0", "expected_score": 100, "expected_errors": 0},
            {"license": "CC0-1.0", "expected_score": 80, "expected_errors": 0},
            {"license": "GPL-3.0", "expected_score": 30, "expected_errors": 0},
            {"license": "GPL", "expected_score": 50, "expected_errors": 1},
            {
                "license": "(MIT OR Apache-2.0)",
                "expected_score": 100,
                "expected_errors": 0,
            },
            {
                "license": "(MIT AND GPL-3.0)",
                "expected_score": 30,
                "expected_errors": 0,
            },
        ]

        for test_case in test_cases:
            with self.subTest(license=test_case["license"]):
                # Set up package with test license
                self.mock_package.license_identifier = test_case["license"]

                # Create package data for license service
                package_data = {
                    "name": self.mock_package.name,
                    "version": self.mock_package.version,
                    "license": test_case["license"],
                }

                # Mock license lookup based on license type
                def mock_lookup(license_id):
                    if license_id in ["MIT", "Apache-2.0"]:
                        return self.mock_mit_license
                    elif license_id == "CC0-1.0":
                        mock_cc0 = Mock(spec=SupportedLicense)
                        mock_cc0.identifier = "CC0-1.0"
                        mock_cc0.status = "allowed"
                        return mock_cc0
                    elif license_id == "GPL-3.0":
                        mock_gpl = Mock(spec=SupportedLicense)
                        mock_gpl.identifier = "GPL-3.0"
                        mock_gpl.status = "avoid"
                        return mock_gpl
                    elif license_id == "GPL":
                        mock_blocked = Mock(spec=SupportedLicense)
                        mock_blocked.identifier = "GPL"
                        mock_blocked.status = "blocked"
                        return mock_blocked
                    return None

                with patch.object(
                    self.license_service,
                    "_lookup_license_in_db",
                    side_effect=mock_lookup,
                ):
                    # Test license validation
                    result = self.license_service.validate_package_license(package_data)

                    self.assertEqual(result["score"], test_case["expected_score"])
                    self.assertEqual(len(result["errors"]), test_case["expected_errors"])


if __name__ == "__main__":
    # Run the tests
    unittest.main(verbosity=2)
