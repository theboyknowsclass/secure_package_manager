"""Tests for DownloadService."""

import os
import unittest
from unittest.mock import Mock, patch

from services.download_service import DownloadService


class TestDownloadService(unittest.TestCase):
    """Test cases for DownloadService."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock environment variables
        with patch.dict(os.environ, {
            'SOURCE_REPOSITORY_URL': 'https://registry.npmjs.org',
            'PACKAGE_CACHE_DIR': '/tmp/test_cache',
            'DOWNLOAD_TIMEOUT': '60'
        }):
            self.download_service = DownloadService()

    def test_construct_download_url_regular_package(self):
        """Test URL construction for regular packages."""
        # Create a mock package
        package = Mock()
        package.name = "react"
        package.version = "18.2.0"
        
        url = self.download_service._construct_download_url(package)
        
        expected_url = "https://registry.npmjs.org/react/-/react-18.2.0.tgz"
        self.assertEqual(url, expected_url)

    def test_construct_download_url_scoped_package(self):
        """Test URL construction for scoped packages."""
        # Create a mock package
        package = Mock()
        package.name = "@babel/core"
        package.version = "7.22.0"
        
        url = self.download_service._construct_download_url(package)
        
        expected_url = "https://registry.npmjs.org/@babel%2fcore/-/core-7.22.0.tgz"
        self.assertEqual(url, expected_url)

    def test_construct_download_url_scoped_package_complex(self):
        """Test URL construction for complex scoped packages."""
        # Create a mock package
        package = Mock()
        package.name = "@typescript-eslint/typescript-estree"
        package.version = "5.0.0"
        
        url = self.download_service._construct_download_url(package)
        
        expected_url = "https://registry.npmjs.org/@typescript-eslint%2ftypescript-estree/-/typescript-estree-5.0.0.tgz"
        self.assertEqual(url, expected_url)

    def test_construct_download_url_custom_registry(self):
        """Test URL construction with custom registry URL."""
        # Create a mock package with custom registry
        with patch.dict(os.environ, {
            'SOURCE_REPOSITORY_URL': 'https://custom-registry.com',
            'PACKAGE_CACHE_DIR': '/tmp/test_cache',
            'DOWNLOAD_TIMEOUT': '60'
        }):
            download_service = DownloadService()
            
            package = Mock()
            package.name = "lodash"
            package.version = "4.17.21"
            
            url = download_service._construct_download_url(package)
            
            expected_url = "https://custom-registry.com/lodash/-/lodash-4.17.21.tgz"
            self.assertEqual(url, expected_url)

    def test_construct_download_url_scoped_package_custom_registry(self):
        """Test URL construction for scoped packages with custom registry."""
        # Create a mock package with custom registry
        with patch.dict(os.environ, {
            'SOURCE_REPOSITORY_URL': 'https://custom-registry.com',
            'PACKAGE_CACHE_DIR': '/tmp/test_cache',
            'DOWNLOAD_TIMEOUT': '60'
        }):
            download_service = DownloadService()
            
            package = Mock()
            package.name = "@vue/compiler-core"
            package.version = "3.3.0"
            
            url = download_service._construct_download_url(package)
            
            expected_url = "https://custom-registry.com/@vue%2fcompiler-core/-/compiler-core-3.3.0.tgz"
            self.assertEqual(url, expected_url)

    def test_construct_download_url_edge_cases(self):
        """Test URL construction for edge cases."""
        # Test package with special characters in name
        package = Mock()
        package.name = "package-with-dashes"
        package.version = "1.0.0"
        
        url = self.download_service._construct_download_url(package)
        
        expected_url = "https://registry.npmjs.org/package-with-dashes/-/package-with-dashes-1.0.0.tgz"
        self.assertEqual(url, expected_url)

        # Test scoped package with special characters
        package.name = "@my-org/my-package"
        package.version = "2.0.0"
        
        url = self.download_service._construct_download_url(package)
        
        expected_url = "https://registry.npmjs.org/@my-org%2fmy-package/-/my-package-2.0.0.tgz"
        self.assertEqual(url, expected_url)


if __name__ == '__main__':
    unittest.main()
