"""Download Service.

Handles downloading packages from npm registry to the package cache.
"""

import io
import logging
import os
import tarfile
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class DownloadService:
    """Service for downloading packages from npm registry."""

    def __init__(self):
        self.package_cache_dir = os.getenv(
            "PACKAGE_CACHE_DIR", "/app/package_cache"
        )
        self.download_timeout = int(os.getenv("DOWNLOAD_TIMEOUT", "60"))
        self.source_repository_url = os.getenv("SOURCE_REPOSITORY_URL", "https://registry.npmjs.org")

        # Ensure package cache directory exists
        os.makedirs(self.package_cache_dir, exist_ok=True)

    def download_package(self, package) -> bool:
        """Download package from npm registry to package cache.

        Args:
            package: Package object with name, version

        Returns:
            True if download successful, False otherwise
        """
        try:
            # Construct download URL using SOURCE_REPOSITORY_URL
            download_url = self._construct_download_url(package)
            
            logger.info(f"Downloading package {package.name}@{package.version} from {download_url}")

            # Create package cache directory
            package_dir = self._get_package_cache_path(package)
            os.makedirs(package_dir, exist_ok=True)

            # Download tarball
            response = requests.get(
                download_url, timeout=self.download_timeout
            )

            if response.status_code != 200:
                logger.error(
                    f"Failed to download package tarball: HTTP {response.status_code}"
                )
                return False

            # Extract tarball to package cache directory
            tarball_buffer = io.BytesIO(response.content)
            with tarfile.open(fileobj=tarball_buffer, mode="r:gz") as tar:
                tar.extractall(package_dir)

            logger.info(
                f"Successfully downloaded and extracted {package.name}@{package.version} to {package_dir}"
            )
            return True

        except requests.exceptions.RequestException as e:
            logger.error(
                (
                    f"Network error downloading package "
                    f"{package.name}@{package.version}: {str(e)}"
                )
            )
            return False
        except tarfile.TarError as e:
            logger.error(
                (
                    f"Error extracting tarball for "
                    f"{package.name}@{package.version}: {str(e)}"
                )
            )
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error downloading package "
                f"{package.name}@{package.version}: {str(e)}"
            )
            return False

    def is_package_downloaded(self, package) -> bool:
        """Check if package is already downloaded in cache.

        Args:
            package: Package object

        Returns:
            True if package exists in cache, False otherwise
        """
        package_dir = self._get_package_cache_path(package)
        package_json_path = os.path.join(
            package_dir, "package", "package.json"
        )
        return os.path.exists(package_json_path)

    def get_package_path(self, package) -> Optional[str]:
        """Get the local path to downloaded package.

        Args:
            package: Package object

        Returns:
            Path to package directory or None if not downloaded
        """
        if self.is_package_downloaded(package):
            return os.path.join(
                self._get_package_cache_path(package), "package"
            )
        return None

    def _get_package_cache_path(self, package) -> str:
        """Get the cache directory path for a package.

        Args:
            package: Package object

        Returns:
            Path to package cache directory
        """
        # Sanitize package name for use in file paths
        safe_package_name = package.name.replace("/", "-").replace("@", "")
        return os.path.join(
            self.package_cache_dir, f"{safe_package_name}-{package.version}"
        )

    def _construct_download_url(self, package) -> str:
        """Construct download URL using SOURCE_REPOSITORY_URL.
        
        Args:
            package: Package object with name and version
            
        Returns:
            Constructed download URL
        """
        # Handle scoped packages (e.g., @babel/core)
        if package.name.startswith("@"):
            # For scoped packages: @scope/package -> @scope%2fpackage
            encoded_name = package.name.replace("/", "%2f")
            return f"{self.source_repository_url}/{encoded_name}/-/{package.name.split('/')[-1]}-{package.version}.tgz"
        else:
            # For regular packages: package -> package
            return f"{self.source_repository_url}/{package.name}/-/{package.name}-{package.version}.tgz"
