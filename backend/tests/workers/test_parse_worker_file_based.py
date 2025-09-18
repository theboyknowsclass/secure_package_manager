#!/usr/bin/env python3
"""
File-based tests for ParseWorker validation and extraction logic.
Uses real package-lock.json files from test_data directory.
"""

import json
import os
import sys
import unittest

# Add the parent directory to the path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


def load_test_package_lock(filename):
    """Load a test package-lock.json file and return as JSON data"""
    if not filename.endswith('.json'):
        filename += '.json'
    
    file_path = os.path.join(os.path.dirname(__file__), "..", "test_data", "package_locks", filename)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


class ParseWorkerValidation:
    """Standalone validation logic extracted from ParseWorker for testing"""
    
    @staticmethod
    def validate_package_lock_file(package_data):
        """Validate that the package data is a valid package-lock.json file"""
        if "lockfileVersion" not in package_data:
            raise ValueError(
                "This file does not appear to be a package-lock.json file. Missing 'lockfileVersion' field."
            )

        lockfile_version = package_data.get("lockfileVersion")
        if lockfile_version is None or lockfile_version < 3:
            raise ValueError(
                f"Unsupported lockfile version: {lockfile_version}. "
                f"This system only supports package-lock.json files with lockfileVersion 3 or higher. "
                f"Please upgrade your npm version (npm 8+) and regenerate the lockfile."
            )

    @staticmethod
    def extract_packages_from_json(package_data):
        """Extract package information from package-lock.json data"""
        packages = package_data.get("packages", {})
        return dict(packages)

    @staticmethod
    def extract_package_name(package_path, package_info):
        """Extract package name from package info or infer from path"""
        package_name = package_info.get("name")

        # If name is not provided, try to extract it from the path
        if not package_name and package_path.startswith("node_modules/"):
            # Extract package name from path
            # For regular packages: "node_modules/lodash" -> "lodash"
            # For scoped packages: "node_modules/@nodelib/package_name" -> "@nodelib/package_name"
            path_parts = package_path.split("/")
            if len(path_parts) >= 2:
                if path_parts[1].startswith("@"):
                    # Scoped package: take both scope and package name
                    if len(path_parts) >= 3:
                        package_name = f"{path_parts[1]}/{path_parts[2]}"
                    else:
                        package_name = path_parts[1]
                else:
                    # Regular package: take just the package name
                    package_name = path_parts[1]

        return package_name


class TestParseWorkerFileBased(unittest.TestCase):
    """Test suite for ParseWorker using real package-lock.json files"""

    def test_validate_simple_app(self):
        """Test validation of simple app package-lock.json"""
        package_data = load_test_package_lock("simple_app")
        
        # Should not raise any exception
        ParseWorkerValidation.validate_package_lock_file(package_data)
        
        # Verify basic structure
        self.assertEqual(package_data["name"], "simple-app")
        self.assertEqual(package_data["version"], "1.0.0")
        self.assertEqual(package_data["lockfileVersion"], 3)

    def test_validate_scoped_packages(self):
        """Test validation of scoped packages app"""
        package_data = load_test_package_lock("scoped_packages")
        
        # Should not raise any exception
        ParseWorkerValidation.validate_package_lock_file(package_data)
        
        # Verify structure
        self.assertEqual(package_data["name"], "scoped-packages-app")
        self.assertEqual(package_data["lockfileVersion"], 3)

    def test_validate_invalid_version_fails(self):
        """Test that invalid lockfile version fails validation"""
        package_data = load_test_package_lock("invalid_version")
        
        with self.assertRaises(ValueError) as context:
            ParseWorkerValidation.validate_package_lock_file(package_data)
        
        self.assertIn("Unsupported lockfile version: 1", str(context.exception))

    def test_validate_missing_lockfile_version_fails(self):
        """Test that missing lockfile version fails validation"""
        package_data = load_test_package_lock("missing_lockfile_version")
        
        with self.assertRaises(ValueError) as context:
            ParseWorkerValidation.validate_package_lock_file(package_data)
        
        self.assertIn("Missing 'lockfileVersion' field", str(context.exception))

    def test_extract_packages_simple_app(self):
        """Test package extraction from simple app"""
        package_data = load_test_package_lock("simple_app")
        packages = ParseWorkerValidation.extract_packages_from_json(package_data)
        
        # Should have 2 packages: root + lodash
        self.assertEqual(len(packages), 2)
        self.assertIn("", packages)  # Root package
        self.assertIn("node_modules/lodash", packages)
        
        # Check lodash package details
        lodash_pkg = packages["node_modules/lodash"]
        self.assertEqual(lodash_pkg["version"], "4.17.21")
        self.assertEqual(lodash_pkg["license"], "MIT")
        self.assertIn("resolved", lodash_pkg)
        self.assertIn("integrity", lodash_pkg)

    def test_extract_packages_scoped_packages(self):
        """Test package extraction from scoped packages app"""
        package_data = load_test_package_lock("scoped_packages")
        packages = ParseWorkerValidation.extract_packages_from_json(package_data)
        
        # Should have 4 packages: root + 3 dependencies
        self.assertEqual(len(packages), 4)
        self.assertIn("", packages)  # Root package
        self.assertIn("node_modules/@angular/core", packages)
        self.assertIn("node_modules/@types/lodash", packages)
        self.assertIn("node_modules/tslib", packages)
        
        # Check scoped package details
        angular_pkg = packages["node_modules/@angular/core"]
        self.assertEqual(angular_pkg["version"], "15.0.0")
        self.assertEqual(angular_pkg["license"], "MIT")
        
        types_lodash_pkg = packages["node_modules/@types/lodash"]
        self.assertEqual(types_lodash_pkg["version"], "4.14.191")
        self.assertEqual(types_lodash_pkg["license"], "MIT")

    def test_extract_packages_duplicate_packages(self):
        """Test package extraction with duplicate packages"""
        package_data = load_test_package_lock("duplicate_packages")
        packages = ParseWorkerValidation.extract_packages_from_json(package_data)
        
        # Should have 4 packages: root + 3 unique packages (lodash appears twice)
        self.assertEqual(len(packages), 4)
        self.assertIn("", packages)  # Root package
        self.assertIn("node_modules/lodash", packages)
        self.assertIn("node_modules/some-package", packages)
        self.assertIn("node_modules/some-package/node_modules/lodash", packages)
        
        # Both lodash instances should have the same version
        lodash1 = packages["node_modules/lodash"]
        lodash2 = packages["node_modules/some-package/node_modules/lodash"]
        self.assertEqual(lodash1["version"], "4.17.21")
        self.assertEqual(lodash2["version"], "4.17.21")

    def test_extract_packages_empty_packages(self):
        """Test package extraction from app with no dependencies"""
        package_data = load_test_package_lock("empty_packages")
        packages = ParseWorkerValidation.extract_packages_from_json(package_data)
        
        # Should have only root package
        self.assertEqual(len(packages), 1)
        self.assertIn("", packages)  # Root package only

    def test_extract_package_name_from_real_files(self):
        """Test package name extraction using real package data"""
        # Test with simple app
        simple_data = load_test_package_lock("simple_app")
        packages = simple_data["packages"]
        
        # Test lodash package
        lodash_info = packages["node_modules/lodash"]
        # Note: This package has no explicit name field, so it should extract from path
        package_name = ParseWorkerValidation.extract_package_name("node_modules/lodash", lodash_info)
        self.assertEqual(package_name, "lodash")
        
        # Test with scoped packages
        scoped_data = load_test_package_lock("scoped_packages")
        scoped_packages = scoped_data["packages"]
        
        # Test @angular/core package
        angular_info = scoped_packages["node_modules/@angular/core"]
        package_name = ParseWorkerValidation.extract_package_name("node_modules/@angular/core", angular_info)
        self.assertEqual(package_name, "@angular/core")
        
        # Test @types/lodash package
        types_info = scoped_packages["node_modules/@types/lodash"]
        package_name = ParseWorkerValidation.extract_package_name("node_modules/@types/lodash", types_info)
        self.assertEqual(package_name, "@types/lodash")

    def test_all_available_test_files(self):
        """Test that all available test files can be loaded and validated"""
        expected_files = [
            "simple_app", "scoped_packages", "duplicate_packages", 
            "invalid_version", "missing_lockfile_version", "empty_packages"
        ]
        
        # Test that we can load all expected files
        for filename in expected_files:
            try:
                package_data = load_test_package_lock(filename)
                self.assertIsInstance(package_data, dict)
                self.assertIn("name", package_data)
                self.assertIn("version", package_data)
            except Exception as e:
                self.fail(f"Failed to load test file {filename}: {e}")


if __name__ == "__main__":
    unittest.main()