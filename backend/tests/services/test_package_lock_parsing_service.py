#!/usr/bin/env python3
"""Tests for PackageLockParsingService.

These tests focus on the business logic of the service without database
dependencies. The service can be tested with mocked operations, making
tests faster and more focused.
"""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

# Add the backend directory to the Python path
sys.path.insert(
    0,
    str(Path(__file__).parent.parent.parent),
)

from services.package_lock_parsing_service import (
    PackageLockParsingService,
)


def load_test_package_lock(filename: str) -> dict:
    """Load a test package-lock.json file and return as JSON data."""
    if not filename.endswith(".json"):
        filename += ".json"

    file_path = Path(__file__).parent / ".." / "test_data" / "package_locks" / filename

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


class TestPackageLockParsingService(unittest.TestCase):
    """Test suite for PackageLockParsingService business logic."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.service = PackageLockParsingService()
        self.mock_ops = self._create_mock_operations()

    def _create_mock_operations(self) -> Mock:
        """Create mock operations for testing."""
        mock_ops = Mock()

        # Mock package operations
        mock_ops.package.get_by_name_version.return_value = None  # No existing packages
        mock_ops.package.create_with_status.return_value = Mock(id=1, name="test", version="1.0.0")

        # Mock request_package operations
        mock_ops.request_package.link_exists.return_value = False
        mock_ops.request_package.create_link.return_value = Mock()

        return mock_ops

    def test_validate_simple_app(self) -> None:
        """Test validation of simple app package-lock.json."""
        package_data = load_test_package_lock("simple_app")

        # Should not raise any exception
        self.service._validate_package_lock_file(package_data)

        # Verify basic structure
        self.assertEqual(package_data["name"], "simple-app")
        self.assertEqual(package_data["version"], "1.0.0")
        self.assertEqual(package_data["lockfileVersion"], 3)

    def test_validate_invalid_version_fails(self) -> None:
        """Test that invalid lockfile version fails validation."""
        package_data = load_test_package_lock("invalid_version")

        with self.assertRaises(ValueError) as context:
            self.service._validate_package_lock_file(package_data)

        self.assertIn("Unsupported lockfile version: 1", str(context.exception))

    def test_extract_packages_from_json(self) -> None:
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

    def test_deduplicate_packages(self) -> None:
        """Test package deduplication logic."""
        package_data = load_test_package_lock("duplicate_packages")
        packages = self.service._extract_packages_from_json(package_data)
        unique_packages = self.service._deduplicate_packages(packages)

        # Should have 2 unique packages (excluding root, lodash is deduplicated)
        self.assertEqual(len(unique_packages), 2)

        # Check that lodash appears only once despite being in multiple paths
        lodash_keys = [key for key in unique_packages.keys() if "lodash" in key]
        self.assertEqual(len(lodash_keys), 1)

    def test_extract_package_name_from_path(self) -> None:
        """Test package name extraction from paths."""
        # Test regular package
        name = self.service._extract_package_name("node_modules/lodash", {})
        self.assertEqual(name, "lodash")

        # Test scoped package
        name = self.service._extract_package_name("node_modules/@angular/core", {})
        self.assertEqual(name, "@angular/core")

        # Test package with name in info
        name = self.service._extract_package_name("node_modules/some-path", {"name": "actual-name"})
        self.assertEqual(name, "actual-name")

    def test_extract_package_name_nested_packages(self) -> None:
        """Test package name extraction from nested package paths."""
        # Test nested regular package (the bug we fixed)
        name = self.service._extract_package_name("node_modules/test-exclude/node_modules/minimatch", {})
        self.assertEqual(name, "minimatch")

        # Test nested scoped package
        name = self.service._extract_package_name("node_modules/test-exclude/node_modules/@types/node", {})
        self.assertEqual(name, "@types/node")

        # Test deeply nested regular package
        name = self.service._extract_package_name(
            "node_modules/package1/node_modules/package2/node_modules/package3",
            {},
        )
        self.assertEqual(name, "package3")

        # Test deeply nested scoped package
        name = self.service._extract_package_name(
            "node_modules/package1/node_modules/package2/node_modules/@scope/package3",
            {},
        )
        self.assertEqual(name, "@scope/package3")

        # Test edge case: multiple node_modules in path
        name = self.service._extract_package_name(
            "node_modules/package1/node_modules/package2/node_modules/@babel/core",
            {},
        )
        self.assertEqual(name, "@babel/core")

    def test_parse_package_lock_validation_error(self) -> None:
        """Test that validation errors are properly raised."""
        invalid_data = {
            "name": "test",
            "version": "1.0.0",
        }  # Missing lockfileVersion

        with self.assertRaises(ValueError) as context:
            self.service._validate_package_lock_file(invalid_data)

        self.assertIn("Missing 'lockfileVersion' field", str(context.exception))

    def test_parse_package_lock_nested_packages(self) -> None:
        """Test parsing with nested packages to ensure correct name extraction."""
        package_data = load_test_package_lock("nested_packages")

        # Test the extraction and deduplication process
        packages = self.service._extract_packages_from_json(package_data)
        unique_packages = self.service._deduplicate_packages(packages)

        # Should have 6 unique packages (excluding root)
        self.assertEqual(len(unique_packages), 6)

        # Check that nested packages are correctly identified
        package_names = [data["name"] for data in unique_packages.values()]
        package_versions = [data["version"] for data in unique_packages.values()]
        package_urls = [data["info"].get("resolved") for data in unique_packages.values()]

        # Verify specific nested packages are correctly parsed
        self.assertIn("test-exclude", package_names)
        self.assertIn("minimatch", package_names)
        self.assertIn("brace-expansion", package_names)
        self.assertIn("@types/node", package_names)
        self.assertIn("glob", package_names)
        self.assertIn("@types/glob", package_names)

        # Verify versions are correct
        self.assertIn("7.0.1", package_versions)  # test-exclude
        self.assertIn("9.0.5", package_versions)  # minimatch (nested)
        self.assertIn("2.0.2", package_versions)  # brace-expansion (nested)
        self.assertIn("18.15.0", package_versions)  # @types/node (nested)
        self.assertIn("10.4.5", package_versions)  # glob
        self.assertIn("8.1.0", package_versions)  # @types/glob (nested)

        # Verify URLs are correct (not cross-contaminated)
        self.assertIn(
            "https://repo/repository/npm/test-exclude/-/test-exclude-7.0.1.tgz",
            package_urls,
        )
        self.assertIn(
            "https://repo/repository/npm/minimatch/-/minimatch-9.0.5.tgz",
            package_urls,
        )
        self.assertIn(
            "https://repo/repository/npm/brace-expansion/-/brace-expansion-2.0.2.tgz",
            package_urls,
        )
        self.assertIn(
            "https://repo/repository/npm/@types/node/-/node-18.15.0.tgz",
            package_urls,
        )
        self.assertIn("https://repo/repository/npm/glob/-/glob-10.4.5.tgz", package_urls)
        self.assertIn(
            "https://repo/repository/npm/@types/glob/-/glob-8.1.0.tgz",
            package_urls,
        )

        # Verify no cross-contamination (the bug we fixed)
        # None of the packages should have the wrong name/version/URL combination
        for key, data in unique_packages.items():
            name = data["name"]
            version = data["version"]
            url = data["info"].get("resolved", "")

            # Each package should have its own correct URL
            if name == "test-exclude" and version == "7.0.1":
                self.assertIn("test-exclude-7.0.1.tgz", url)
            elif name == "minimatch" and version == "9.0.5":
                self.assertIn("minimatch-9.0.5.tgz", url)
            elif name == "brace-expansion" and version == "2.0.2":
                self.assertIn("brace-expansion-2.0.2.tgz", url)
            elif name == "@types/node" and version == "18.15.0":
                self.assertIn("@types/node/-/node-18.15.0.tgz", url)
            elif name == "glob" and version == "10.4.5":
                self.assertIn("glob-10.4.5.tgz", url)
            elif name == "@types/glob" and version == "8.1.0":
                self.assertIn("@types/glob/-/glob-8.1.0.tgz", url)


if __name__ == "__main__":
    unittest.main()
