#!/usr/bin/env python3
"""Tests for PackageLockParsingService.

These tests focus on the business logic of the service without database
dependencies. The service can be tested with mocked operations, making
tests faster and more focused.
"""

import json
import os
import unittest
from typing import Any, Dict
from unittest.mock import MagicMock, Mock

from services.package_lock_parsing_service import (
    PackageLockParsingService,
)


def load_test_package_lock(filename):
    """Load a test package-lock.json file and return as JSON data."""
    if not filename.endswith(".json"):
        filename += ".json"

    file_path = os.path.join(
        os.path.dirname(__file__), "..", "test_data", "package_locks", filename
    )

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


class TestPackageLockParsingService(unittest.TestCase):
    """Test suite for PackageLockParsingService business logic."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = PackageLockParsingService()
        self.mock_ops = self._create_mock_operations()

    def _create_mock_operations(self) -> Dict[str, Any]:
        """Create mock operations for testing."""
        mock_ops = {
            "package": Mock(),
            "request_package": Mock(),
        }

        # Mock package operations
        mock_ops.package.get_by_name_version.return_value = (
            None  # No existing packages
        )
        mock_ops.package.create_with_status.return_value = Mock(
            id=1, name="test", version="1.0.0"
        )

        # Mock request_package operations
        mock_ops.request_package.link_exists.return_value = False
        mock_ops.request_package.create_link.return_value = Mock()

        return mock_ops

    def test_validate_simple_app(self):
        """Test validation of simple app package-lock.json."""
        package_data = load_test_package_lock("simple_app")

        # Should not raise any exception
        self.service._validate_package_lock_file(package_data)

        # Verify basic structure
        self.assertEqual(package_data["name"], "simple-app")
        self.assertEqual(package_data["version"], "1.0.0")
        self.assertEqual(package_data["lockfileVersion"], 3)

    def test_validate_invalid_version_fails(self):
        """Test that invalid lockfile version fails validation."""
        package_data = load_test_package_lock("invalid_version")

        with self.assertRaises(ValueError) as context:
            self.service._validate_package_lock_file(package_data)

        self.assertIn(
            "Unsupported lockfile version: 1", str(context.exception)
        )

    def test_extract_packages_from_json(self):
        """Test package extraction from JSON data."""
        package_data = load_test_package_lock("simple_app")
        packages = self.service._extract_packages_from_json(package_data)

        # Should have 2 packages: root + lodash
        self.assertEqual(len(packages), 2)
        self.assertIn("", packages)  # Root package
        self.assertIn("node_modules/lodash", packages)

        # Check lodash package details
        lodash_pkg = packages["node_modules/lodash"]
        self.assertEqual(lodash_pkg["version"], "4.17.21")
        self.assertEqual(lodash_pkg["license"], "MIT")

    def test_deduplicate_packages(self):
        """Test package deduplication logic."""
        package_data = load_test_package_lock("duplicate_packages")
        packages = self.service._extract_packages_from_json(package_data)
        unique_packages = self.service._deduplicate_packages(packages)

        # Should have 3 unique packages (excluding root)
        self.assertEqual(len(unique_packages), 3)

        # Check that lodash appears only once despite being in multiple paths
        lodash_keys = [
            key for key in unique_packages.keys() if "lodash" in key
        ]
        self.assertEqual(len(lodash_keys), 1)

    def test_extract_package_name_from_path(self):
        """Test package name extraction from paths."""
        # Test regular package
        name = self.service._extract_package_name("node_modules/lodash", {})
        self.assertEqual(name, "lodash")

        # Test scoped package
        name = self.service._extract_package_name(
            "node_modules/@angular/core", {}
        )
        self.assertEqual(name, "@angular/core")

        # Test package with name in info
        name = self.service._extract_package_name(
            "node_modules/some-path", {"name": "actual-name"}
        )
        self.assertEqual(name, "actual-name")

    def test_parse_package_lock_with_new_packages(self):
        """Test parsing with all new packages."""
        package_data = load_test_package_lock("simple_app")

        result = self.service.parse_package_lock(
            1, package_data, self.mock_ops
        )

        # Should have created 1 new package (lodash)
        self.assertEqual(result["packages_to_process"], 1)
        self.assertEqual(result["existing_packages"], 0)
        self.assertEqual(result["total_packages"], 1)

        # Verify that package operations were called
        self.mock_ops.package.get_by_name_version.assert_called()
        self.mock_ops.package.create_with_status.assert_called()
        self.mock_ops.request_package.create_link.assert_called()

    def test_parse_package_lock_with_existing_packages(self):
        """Test parsing with existing packages."""
        package_data = load_test_package_lock("simple_app")

        # Mock existing package
        existing_package = Mock(id=1, name="lodash", version="4.17.21")
        self.mock_ops.package.get_by_name_version.return_value = (
            existing_package
        )

        result = self.service.parse_package_lock(
            1, package_data, self.mock_ops
        )

        # Should have found 1 existing package
        self.assertEqual(result["packages_to_process"], 0)
        self.assertEqual(result["existing_packages"], 1)
        self.assertEqual(result["total_packages"], 1)

        # Verify that link was created for existing package
        self.mock_ops.request_package.create_link.assert_called_with(
            1, 1, "existing"
        )

    def test_parse_package_lock_validation_error(self):
        """Test that validation errors are properly raised."""
        invalid_data = {
            "name": "test",
            "version": "1.0.0",
        }  # Missing lockfileVersion

        with self.assertRaises(ValueError) as context:
            self.service.parse_package_lock(1, invalid_data, self.mock_ops)

        self.assertIn(
            "Missing 'lockfileVersion' field", str(context.exception)
        )

    def test_parse_package_lock_with_scoped_packages(self):
        """Test parsing with scoped packages."""
        package_data = load_test_package_lock("scoped_packages")

        result = self.service.parse_package_lock(
            1, package_data, self.mock_ops
        )

        # Should have created 3 new packages
        self.assertEqual(result["packages_to_process"], 3)
        self.assertEqual(result["existing_packages"], 0)
        self.assertEqual(result["total_packages"], 3)

    def test_parse_package_lock_empty_packages(self):
        """Test parsing with no dependencies."""
        package_data = load_test_package_lock("empty_packages")

        result = self.service.parse_package_lock(
            1, package_data, self.mock_ops
        )

        # Should have no packages to process
        self.assertEqual(result["packages_to_process"], 0)
        self.assertEqual(result["existing_packages"], 0)
        self.assertEqual(result["total_packages"], 0)


if __name__ == "__main__":
    unittest.main()
