"""Test cases for scoped package parsing from package-lock.json files.

This module tests the critical functionality of extracting package names
from package-lock.json paths, with special focus on scoped packages.
"""

import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
from services.package_lock_parsing_service import PackageLockParsingService

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestScopedPackageParsing:
    """Test cases for scoped package name extraction."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.package_service = PackageLockParsingService()

    def test_extract_regular_package_name(self) -> None:
        """Test extraction of regular (non-scoped) package names."""
        test_cases = [
            {
                "path": "node_modules/lodash",
                "info": {"version": "4.17.21"},
                "expected": "lodash",
            },
            {
                "path": "node_modules/express",
                "info": {"version": "4.18.2"},
                "expected": "express",
            },
            {
                "path": "node_modules/react",
                "info": {"version": "18.2.0"},
                "expected": "react",
            },
        ]

        for case in test_cases:
            result = self.package_service._extract_package_name(
                case["path"], case["info"]
            )
            assert (
                result == case["expected"]
            ), f"Failed for path: {case['path']}"

    def test_extract_scoped_package_name(self) -> None:
        """Test extraction of scoped package names."""
        test_cases = [
            {
                "path": "node_modules/@types/node",
                "info": {"version": "18.15.0"},
                "expected": "@types/node",
            },
            {
                "path": "node_modules/@babel/core",
                "info": {"version": "7.22.0"},
                "expected": "@babel/core",
            },
            {
                "path": "node_modules/@mui/material",
                "info": {"version": "5.14.0"},
                "expected": "@mui/material",
            },
            {
                "path": "node_modules/@typescript-eslint/parser",
                "info": {"version": "5.62.0"},
                "expected": "@typescript-eslint/parser",
            },
            {
                "path": "node_modules/@nodelib/fs.stat",
                "info": {"version": "2.0.5"},
                "expected": "@nodelib/fs.stat",
            },
        ]

        for case in test_cases:
            result = self.package_service._extract_package_name(
                case["path"], case["info"]
            )
            assert (
                result == case["expected"]
            ), f"Failed for path: {case['path']}"

    def test_extract_nested_scoped_package_name(self) -> None:
        """Test extraction of nested scoped package names."""
        test_cases = [
            {
                "path": "node_modules/express/node_modules/@types/express",
                "info": {"version": "4.17.17"},
                "expected": "@types/express",
            },
            {
                "path": "node_modules/react/node_modules/@types/react",
                "info": {"version": "18.0.28"},
                "expected": "@types/react",
            },
        ]

        for case in test_cases:
            result = self.package_service._extract_package_name(
                case["path"], case["info"]
            )
            assert (
                result == case["expected"]
            ), f"Failed for path: {case['path']}"

    def test_extract_package_name_with_explicit_name(self) -> None:
        """Test extraction when package info contains explicit name field."""
        test_cases = [
            {
                "path": "node_modules/@types/node",
                "info": {"name": "@types/node", "version": "18.15.0"},
                "expected": "@types/node",
            },
            {
                "path": "node_modules/lodash",
                "info": {"name": "lodash", "version": "4.17.21"},
                "expected": "lodash",
            },
        ]

        for case in test_cases:
            result = self.package_service._extract_package_name(
                case["path"], case["info"]
            )
            assert (
                result == case["expected"]
            ), f"Failed for path: {case['path']}"

    def test_extract_incomplete_scoped_package(self) -> None:
        """Test extraction of incomplete scoped package paths."""
        test_cases = [
            {
                "path": "node_modules/@types",
                "info": {"version": "1.0.0"},
                "expected": "@types",  # Should handle incomplete scope gracefully
            }
        ]

        for case in test_cases:
            result = self.package_service._extract_package_name(
                case["path"], case["info"]
            )
            assert (
                result == case["expected"]
            ), f"Failed for path: {case['path']}"

    def test_extract_invalid_paths(self) -> None:
        """Test extraction with invalid or malformed paths."""
        test_cases = [
            {
                "path": "not_node_modules/package",
                "info": {"version": "1.0.0"},
                "expected": None,
            },
            {
                "path": "node_modules",
                "info": {"version": "1.0.0"},
                "expected": None,
            },
            {"path": "", "info": {"version": "1.0.0"}, "expected": None},
        ]

        for case in test_cases:
            result = self.package_service._extract_package_name(
                case["path"], case["info"]
            )
            assert (
                result == case["expected"]
            ), f"Failed for path: {case['path']}"

    def test_extract_missing_version(self) -> None:
        """Test extraction when version is missing."""
        test_cases = [
            {
                "path": "node_modules/lodash",
                "info": {},  # No version
                "expected": "lodash",
            },
            {
                "path": "node_modules/@types/node",
                "info": {},  # No version
                "expected": "@types/node",
            },
        ]

        for case in test_cases:
            result = self.package_service._extract_package_name(
                case["path"], case["info"]
            )
            assert (
                result == case["expected"]
            ), f"Failed for path: {case['path']}"

    def test_real_world_scoped_packages(self) -> None:
        """Test with real-world scoped package examples."""
        real_world_cases = [
            # Common TypeScript packages
            ("node_modules/@types/node", "@types/node"),
            ("node_modules/@types/react", "@types/react"),
            ("node_modules/@types/lodash", "@types/lodash"),
            # Babel ecosystem
            ("node_modules/@babel/core", "@babel/core"),
            ("node_modules/@babel/preset-env", "@babel/preset-env"),
            (
                "node_modules/@babel/plugin-transform-runtime",
                "@babel/plugin-transform-runtime",
            ),
            # Material-UI ecosystem
            ("node_modules/@mui/material", "@mui/material"),
            ("node_modules/@mui/icons-material", "@mui/icons-material"),
            ("node_modules/@mui/system", "@mui/system"),
            # ESLint ecosystem
            (
                "node_modules/@typescript-eslint/parser",
                "@typescript-eslint/parser",
            ),
            (
                "node_modules/@typescript-eslint/eslint-plugin",
                "@typescript-eslint/eslint-plugin",
            ),
            # Node.js utilities
            ("node_modules/@nodelib/fs.stat", "@nodelib/fs.stat"),
            ("node_modules/@nodelib/fs.walk", "@nodelib/fs.walk"),
            # Vite ecosystem
            ("node_modules/@vitejs/plugin-react", "@vitejs/plugin-react"),
            ("node_modules/@vitejs/plugin-vue", "@vitejs/plugin-vue"),
        ]

        for path, expected in real_world_cases:
            result = self.package_service._extract_package_name(
                path, {"version": "1.0.0"}
            )
            assert (
                result == expected
            ), f"Failed for real-world case: {path} -> expected {expected}, got {result}"

    def test_edge_cases(self) -> None:
        """Test edge cases and boundary conditions."""
        edge_cases = [
            # Very long scoped package names
            {
                "path": "node_modules/@very-long-scope-name/very-long-package-name",
                "info": {"version": "1.0.0"},
                "expected": "@very-long-scope-name/very-long-package-name",
            },
            # Packages with hyphens and underscores
            {
                "path": "node_modules/@my-scope/my-package_name",
                "info": {"version": "1.0.0"},
                "expected": "@my-scope/my-package_name",
            },
            # Packages with numbers
            {
                "path": "node_modules/@scope123/package456",
                "info": {"version": "1.0.0"},
                "expected": "@scope123/package456",
            },
        ]

        for case in edge_cases:
            result = self.package_service._extract_package_name(
                case["path"], case["info"]
            )
            assert (
                result == case["expected"]
            ), f"Failed for edge case: {case['path']}"


class TestPackageLockProcessing:
    """Test cases for full package-lock.json processing."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.package_service = PackageLockParsingService()

    def test_extract_packages_from_json_with_scoped_packages(self) -> None:
        """Test extracting packages from package-lock.json with scoped packages."""
        package_lock_data = {
            "name": "test-project",
            "version": "1.0.0",
            "lockfileVersion": 3,
            "packages": {
                "": {
                    "name": "test-project",
                    "version": "1.0.0",
                    "dependencies": {
                        "@types/node": "^18.0.0",
                        "@babel/core": "^7.22.0",
                    },
                },
                "node_modules/@types/node": {
                    "version": "18.15.0",
                    "resolved": "https://registry.npmjs.org/@types/node/-/node-18.15.0.tgz",
                    "integrity": "sha512-...",
                },
                "node_modules/@babel/core": {
                    "version": "7.22.0",
                    "resolved": "https://registry.npmjs.org/@babel/core/-/core-7.22.0.tgz",
                    "integrity": "sha512-...",
                },
            },
        }

        # Extract packages
        packages = self.package_service._extract_packages_from_json(
            package_lock_data
        )

        # Verify scoped packages are correctly extracted
        assert (
            "node_modules/@types/node" in packages
        ), "Scoped package @types/node not found"
        assert (
            "node_modules/@babel/core" in packages
        ), "Scoped package @babel/core not found"

        # Verify versions are correct
        assert packages["node_modules/@types/node"]["version"] == "18.15.0"
        assert packages["node_modules/@babel/core"]["version"] == "7.22.0"


if __name__ == "__main__":
    pytest.main([__file__])
