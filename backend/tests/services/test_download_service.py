"""Tests for DownloadService."""

import os
import sys
import unittest
from unittest.mock import Mock, patch

# Add the backend directory to the Python path
sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ),
)

from services.download_service import DownloadService


class TestDownloadService(unittest.TestCase):
    """Test cases for DownloadService."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        # Mock environment variables
        with patch.dict(
            os.environ,
            {
                "SOURCE_REPOSITORY_URL": "https://registry.npmjs.org",
                "PACKAGE_CACHE_DIR": "/tmp/test_cache",
                "DOWNLOAD_TIMEOUT": "60",
            },
        ):
            self.download_service = DownloadService()

    def test_construct_download_url_regular_package(self) -> None:
        """Test URL construction for regular packages."""
        # Create a mock package
        package = Mock()
        package.name = "react"
        package.version = "18.2.0"
        package.npm_url = None  # Explicitly set to None to test custom logic

        url = self.download_service._construct_download_url(package)

        expected_url = "https://registry.npmjs.org/react/-/react-18.2.0.tgz"
        self.assertEqual(url, expected_url)

    def test_construct_download_url_scoped_package(self) -> None:
        """Test URL construction for scoped packages."""
        # Create a mock package
        package = Mock()
        package.name = "@babel/core"
        package.version = "7.22.0"
        package.npm_url = None  # Explicitly set to None to test custom logic

        url = self.download_service._construct_download_url(package)

        expected_url = (
            "https://registry.npmjs.org/@babel/core/-/core-7.22.0.tgz"
        )
        self.assertEqual(url, expected_url)

    def test_construct_download_url_scoped_package_complex(self) -> None:
        """Test URL construction for complex scoped packages."""
        # Create a mock package
        package = Mock()
        package.name = "@typescript-eslint/typescript-estree"
        package.version = "5.0.0"
        package.npm_url = None  # Explicitly set to None to test custom logic

        url = self.download_service._construct_download_url(package)

        expected_url = "https://registry.npmjs.org/@typescript-eslint/typescript-estree/-/typescript-estree-5.0.0.tgz"
        self.assertEqual(url, expected_url)

    def test_construct_download_url_custom_registry(self) -> None:
        """Test URL construction with custom registry URL."""
        # Create a mock package with custom registry
        with patch.dict(
            os.environ,
            {
                "SOURCE_REPOSITORY_URL": "https://custom-registry.com",
                "PACKAGE_CACHE_DIR": "/tmp/test_cache",
                "DOWNLOAD_TIMEOUT": "60",
            },
        ):
            download_service = DownloadService()

            package = Mock()
            package.name = "lodash"
            package.version = "4.17.21"
            package.npm_url = (
                None  # Explicitly set to None to test custom logic
            )

            url = download_service._construct_download_url(package)

            expected_url = (
                "https://custom-registry.com/lodash/-/lodash-4.17.21.tgz"
            )
            self.assertEqual(url, expected_url)

    def test_construct_download_url_scoped_package_custom_registry(self) -> None:
        """Test URL construction for scoped packages with custom registry."""
        # Create a mock package with custom registry
        with patch.dict(
            os.environ,
            {
                "SOURCE_REPOSITORY_URL": "https://custom-registry.com",
                "PACKAGE_CACHE_DIR": "/tmp/test_cache",
                "DOWNLOAD_TIMEOUT": "60",
            },
        ):
            download_service = DownloadService()

            package = Mock()
            package.name = "@vue/compiler-core"
            package.version = "3.3.0"
            package.npm_url = (
                None  # Explicitly set to None to test custom logic
            )

            url = download_service._construct_download_url(package)

            expected_url = "https://custom-registry.com/@vue/compiler-core/-/compiler-core-3.3.0.tgz"
            self.assertEqual(url, expected_url)

    def test_construct_download_url_edge_cases(self) -> None:
        """Test URL construction for edge cases."""
        # Test package with special characters in name
        package = Mock()
        package.name = "package-with-dashes"
        package.version = "1.0.0"
        package.npm_url = None  # Explicitly set to None to test custom logic

        url = self.download_service._construct_download_url(package)

        expected_url = "https://registry.npmjs.org/package-with-dashes/-/package-with-dashes-1.0.0.tgz"
        self.assertEqual(url, expected_url)

        # Test scoped package with special characters
        package.name = "@my-org/my-package"
        package.version = "2.0.0"
        package.npm_url = None  # Explicitly set to None to test custom logic

        url = self.download_service._construct_download_url(package)

        expected_url = "https://registry.npmjs.org/@my-org/my-package/-/my-package-2.0.0.tgz"
        self.assertEqual(url, expected_url)

    def test_construct_download_url_uses_existing_npm_url(self) -> None:
        """Test URL construction uses existing npm_url when it matches source repository."""
        # Create a mock package with npm_url that matches source repository
        package = Mock()
        package.name = "react"
        package.version = "18.2.0"
        package.npm_url = "https://registry.npmjs.org/react/-/react-18.2.0.tgz"

        url = self.download_service._construct_download_url(package)

        # Should return the existing npm_url directly
        self.assertEqual(
            url, "https://registry.npmjs.org/react/-/react-18.2.0.tgz"
        )

    def test_construct_download_url_ignores_npm_url_different_registry() -> (
        None
    ):
        """Test URL construction ignores npm_url when it doesn't match source repository."""
        # Create a mock package with npm_url from different registry
        package = Mock()
        package.name = "react"
        package.version = "18.2.0"
        package.npm_url = (
            "https://different-registry.com/react/-/react-18.2.0.tgz"
        )

        url = self.download_service._construct_download_url(package)

        # Should use custom logic instead of the npm_url
        expected_url = "https://registry.npmjs.org/react/-/react-18.2.0.tgz"
        self.assertEqual(url, expected_url)

    def test_construct_download_url_handles_none_npm_url(self) -> None:
        """Test URL construction handles None npm_url."""
        # Create a mock package with None npm_url
        package = Mock()
        package.name = "react"
        package.version = "18.2.0"
        package.npm_url = None

        url = self.download_service._construct_download_url(package)

        # Should use custom logic
        expected_url = "https://registry.npmjs.org/react/-/react-18.2.0.tgz"
        self.assertEqual(url, expected_url)

    def test_construct_download_url_uses_existing_npm_url_scoped_package() -> (
        None
    ):
        """Test URL construction uses existing npm_url for scoped packages."""
        # Create a mock scoped package with npm_url that matches source repository
        package = Mock()
        package.name = "@babel/core"
        package.version = "7.22.0"
        package.npm_url = (
            "https://registry.npmjs.org/@babel/core/-/core-7.22.0.tgz"
        )

        url = self.download_service._construct_download_url(package)

        # Should return the existing npm_url directly
        self.assertEqual(
            url, "https://registry.npmjs.org/@babel/core/-/core-7.22.0.tgz"
        )

    def test_construct_download_url_different_npm_and_source_registry() -> (
        None
    ):
        """Test URL construction when npm_url and source_repository_url are different."""
        # Create a mock package with npm_url from different registry
        package = Mock()
        package.name = "lodash"
        package.version = "4.17.21"
        package.npm_url = (
            "https://npm.pkg.github.com/lodash/-/lodash-4.17.21.tgz"
        )

        url = self.download_service._construct_download_url(package)

        # Should use custom logic with source_repository_url, not the npm_url
        expected_url = "https://registry.npmjs.org/lodash/-/lodash-4.17.21.tgz"
        self.assertEqual(url, expected_url)

    def test_construct_download_url_different_npm_and_source_registry_scoped() -> (
        None
    ):
        """Test URL construction for scoped packages when npm_url and source_repository_url are different."""
        # Create a mock scoped package with npm_url from different registry
        package = Mock()
        package.name = "@company/private-package"
        package.version = "1.0.0"
        package.npm_url = "https://npm.pkg.github.com/@company/private-package/-/private-package-1.0.0.tgz"

        url = self.download_service._construct_download_url(package)

        # Should use custom logic with source_repository_url, not the npm_url
        expected_url = "https://registry.npmjs.org/@company/private-package/-/private-package-1.0.0.tgz"
        self.assertEqual(url, expected_url)


if __name__ == "__main__":
    unittest.main()
