"""Tests for PackageCacheService."""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

# Add the backend directory to the Python path
sys.path.insert(
    0,
    str(Path(__file__).parent.parent.parent),
)

from services.package_cache_service import PackageCacheService


class TestPackageCacheService(unittest.TestCase):
    """Test cases for PackageCacheService."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        # Create a temporary directory for testing
        self.test_cache_dir = tempfile.mkdtemp()

        # Mock environment variables
        with patch.dict(
            os.environ, {"PACKAGE_CACHE_DIR": self.test_cache_dir}
        ):
            self.cache_service = PackageCacheService()

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        # Remove the temporary directory
        if Path(self.test_cache_dir).exists():
            shutil.rmtree(self.test_cache_dir)

    def test_get_package_cache_path_regular_package(self) -> None:
        """Test cache path generation for regular packages."""
        package = Mock()
        package.name = "react"
        package.version = "18.2.0"

        path = self.cache_service._get_package_cache_path(package)

        expected_path = Path(self.test_cache_dir) / "react-18.2.0"
        self.assertEqual(path, expected_path)

    def test_get_package_cache_path_scoped_package(self) -> None:
        """Test cache path generation for scoped packages."""
        package = Mock()
        package.name = "@babel/core"
        package.version = "7.22.0"

        path = self.cache_service._get_package_cache_path(package)

        expected_path = Path(self.test_cache_dir) / "@babel-core-7.22.0"
        self.assertEqual(path, expected_path)

    def test_get_package_cache_path_special_characters(self) -> None:
        """Test cache path generation for packages with special characters."""
        package = Mock()
        package.name = "package-with-dashes"
        package.version = "1.0.0"

        path = self.cache_service._get_package_cache_path(package)

        expected_path = Path(self.test_cache_dir) / "package-with-dashes-1.0.0"
        self.assertEqual(path, expected_path)

    def test_is_package_cached_not_cached(self) -> None:
        """Test checking if package is cached when it's not."""
        package = Mock()
        package.name = "nonexistent"
        package.version = "1.0.0"

        result = self.cache_service.is_package_cached(package)

        self.assertFalse(result)

    def test_is_package_cached_cached(self) -> None:
        """Test checking if package is cached when it is."""
        package = Mock()
        package.name = "test-package"
        package.version = "1.0.0"

        # Create the package directory structure
        package_dir = self.cache_service._get_package_cache_path(package)
        package_dir.mkdir(parents=True, exist_ok=True)
        (package_dir / "package").mkdir(parents=True, exist_ok=True)

        # Create a dummy package.json
        package_json_path = package_dir / "package" / "package.json"
        with open(package_json_path, "w") as f:
            f.write('{"name": "test-package", "version": "1.0.0"}')

        result = self.cache_service.is_package_cached(package)

        self.assertTrue(result)

    def test_get_package_path_not_cached(self) -> None:
        """Test getting package path when package is not cached."""
        package = Mock()
        package.name = "nonexistent"
        package.version = "1.0.0"

        result = self.cache_service.get_package_path(package)

        self.assertIsNone(result)

    def test_get_package_path_cached(self) -> None:
        """Test getting package path when package is cached."""
        package = Mock()
        package.name = "test-package"
        package.version = "1.0.0"

        # Create the package directory structure
        package_dir = self.cache_service._get_package_cache_path(package)
        package_dir.mkdir(parents=True, exist_ok=True)
        (package_dir / "package").mkdir(parents=True, exist_ok=True)

        # Create a dummy package.json
        package_json_path = package_dir / "package" / "package.json"
        with open(package_json_path, "w") as f:
            f.write('{"name": "test-package", "version": "1.0.0"}')

        result = self.cache_service.get_package_path(package)

        expected_path = package_dir / "package"
        self.assertEqual(result, expected_path)

    @patch("tarfile.open")
    def test_store_package_from_tarball_success(self) -> None:
        """Test storing package from tarball successfully."""
        package = Mock()
        package.name = "test-package"
        package.version = "1.0.0"

        # Mock tarball content
        tarball_content = b"fake tarball content"

        # Mock tarfile extraction
        mock_tar = Mock()
        mock_tarfile_open.return_value = mock_tar

        # Create the package directory and package.json after extraction
        package_dir = self.cache_service._get_package_cache_path(package)
        package_dir.mkdir(parents=True, exist_ok=True)
        (package_dir / "package").mkdir(parents=True, exist_ok=True)

        # Create a dummy package.json
        package_json_path = package_dir / "package" / "package.json"
        with open(package_json_path, "w") as f:
            f.write('{"name": "test-package", "version": "1.0.0"}')

        result = self.cache_service.store_package_from_tarball(
            package, tarball_content
        )

        self.assertTrue(result)
        mock_tar.extractall.assert_called_once()

    @patch("tarfile.open")
    def test_store_package_from_tarball_extraction_error(self) -> None:
        """Test storing package from tarball with extraction error."""
        package = Mock()
        package.name = "test-package"
        package.version = "1.0.0"

        # Mock tarball content
        tarball_content = b"fake tarball content"

        # Mock tarfile extraction error
        mock_tarfile_open.side_effect = Exception("Extraction failed")

        result = self.cache_service.store_package_from_tarball(
            package, tarball_content
        )

        self.assertFalse(result)

    def test_remove_package_success(self) -> None:
        """Test removing package successfully."""
        package = Mock()
        package.name = "test-package"
        package.version = "1.0.0"

        # Create the package directory
        package_dir = self.cache_service._get_package_cache_path(package)
        os.makedirs(package_dir, exist_ok=True)

        # Verify it exists
        self.assertTrue(package_dir.exists())

        result = self.cache_service.remove_package(package)

        self.assertTrue(result)
        self.assertFalse(package_dir.exists())

    def test_remove_package_not_exists(self) -> None:
        """Test removing package that doesn't exist."""
        package = Mock()
        package.name = "nonexistent"
        package.version = "1.0.0"

        result = self.cache_service.remove_package(package)

        self.assertTrue(
            result
        )  # Should return True even if package doesn't exist

    def test_get_cache_size_empty(self) -> None:
        """Test getting cache size when cache is empty."""
        size = self.cache_service.get_cache_size()

        self.assertEqual(size, 0)

    def test_get_cache_size_with_packages(self) -> None:
        """Test getting cache size with packages in cache."""
        package = Mock()
        package.name = "test-package"
        package.version = "1.0.0"

        # Create the package directory
        package_dir = self.cache_service._get_package_cache_path(package)
        os.makedirs(package_dir, exist_ok=True)

        # Create a file with known size
        test_file_path = package_dir / "test.txt"
        with open(test_file_path, "w") as f:
            f.write("test content")

        size = self.cache_service.get_cache_size()

        # Should be greater than 0
        self.assertGreater(size, 0)

    def test_list_cached_packages_empty(self) -> None:
        """Test listing cached packages when cache is empty."""
        packages = self.cache_service.list_cached_packages()

        self.assertEqual(len(packages), 0)

    def test_list_cached_packages_with_packages(self) -> None:
        """Test listing cached packages with packages in cache."""
        package = Mock()
        package.name = "test"
        package.version = "1.0.0"

        # Create the package directory
        package_dir = self.cache_service._get_package_cache_path(package)
        os.makedirs(package_dir, exist_ok=True)

        packages = self.cache_service.list_cached_packages()

        self.assertEqual(len(packages), 1)
        self.assertEqual(packages[0]["name"], "test")
        self.assertEqual(packages[0]["version"], "1.0.0")
        self.assertEqual(packages[0]["path"], package_dir)


if __name__ == "__main__":
    unittest.main()
