"""Package Cache Service.

Handles local package cache operations including storage, retrieval, and management
of downloaded packages in the local cache directory.
"""

import logging
import os
import tarfile
from typing import Optional

logger = logging.getLogger(__name__)


class PackageCacheService:
    """Service for managing local package cache operations."""

    def __init__(self):
        self.package_cache_dir = os.getenv(
            "PACKAGE_CACHE_DIR", "/app/package_cache"
        )
        
        # Ensure package cache directory exists
        os.makedirs(self.package_cache_dir, exist_ok=True)

    def store_package_from_tarball(self, package, tarball_content: bytes) -> Optional[str]:
        """Store a package in the cache from tarball content.

        Args:
            package: Package object with name, version
            tarball_content: Raw tarball content as bytes

        Returns:
            Path to the stored package directory if successful, None otherwise
        """
        try:
            # Create package cache directory
            package_dir = self._get_package_cache_path(package)
            os.makedirs(package_dir, exist_ok=True)

            # Extract tarball to package cache directory
            tarball_buffer = tarfile.open(fileobj=tarfile.io.BytesIO(tarball_content), mode="r:gz")
            tarball_buffer.extractall(package_dir)
            tarball_buffer.close()

            # Return the actual path to the package directory
            return package_dir

        except tarfile.TarError as e:
            logger.error(
                f"Error extracting tarball for {package.name}@{package.version}: {str(e)}"
            )
            return None
        except Exception as e:
            logger.error(
                f"Unexpected error storing package {package.name}@{package.version}: {str(e)}"
            )
            return None

    def is_package_cached(self, package) -> bool:
        """Check if package is already cached locally.

        Args:
            package: Package object

        Returns:
            True if package exists in cache, False otherwise
        """
        package_dir = self._get_package_cache_path(package)
        return os.path.exists(package_dir) and os.path.isdir(package_dir)

    def get_package_path(self, package) -> Optional[str]:
        """Get the local path to cached package.

        Args:
            package: Package object

        Returns:
            Path to package directory or None if not cached
        """
        if self.is_package_cached(package):
            package_dir = self._get_package_cache_path(package)
            
            # All npm tarballs extract to a "package" directory
            # Both scoped and regular packages use the same structure
            return os.path.join(package_dir, "package")
        return None

    def remove_package(self, package) -> bool:
        """Remove a package from the cache.

        Args:
            package: Package object

        Returns:
            True if removal successful, False otherwise
        """
        try:
            package_dir = self._get_package_cache_path(package)
            if os.path.exists(package_dir):
                import shutil
                shutil.rmtree(package_dir)
                logger.info(f"Removed package {package.name}@{package.version} from cache")
                return True
            return True  # Already removed
        except Exception as e:
            logger.error(
                f"Error removing package {package.name}@{package.version}: {str(e)}"
            )
            return False

    def get_cache_size(self) -> int:
        """Get the total size of the package cache in bytes.

        Returns:
            Total cache size in bytes
        """
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(self.package_cache_dir):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)
        except Exception as e:
            logger.error(f"Error calculating cache size: {str(e)}")
        return total_size

    def list_cached_packages(self) -> list:
        """List all packages currently in the cache.

        Returns:
            List of package info dictionaries
        """
        cached_packages = []
        try:
            for item in os.listdir(self.package_cache_dir):
                item_path = os.path.join(self.package_cache_dir, item)
                if os.path.isdir(item_path):
                    # Parse package name and version from directory name
                    # Format: package-name-version or @scope-package-version
                    if item.startswith("@"):
                        # Scoped package: @scope-package-version
                        parts = item.split("-")
                        if len(parts) >= 3:
                            scope = parts[0]
                            package_name = parts[1]
                            version = "-".join(parts[2:])
                            full_name = f"{scope}/{package_name}"
                        else:
                            continue
                    else:
                        # Regular package: package-name-version
                        parts = item.split("-")
                        if len(parts) >= 2:
                            package_name = parts[0]
                            version = "-".join(parts[1:])
                            full_name = package_name
                        else:
                            continue
                    
                    cached_packages.append({
                        "name": full_name,
                        "version": version,
                        "path": item_path
                    })
        except Exception as e:
            logger.error(f"Error listing cached packages: {str(e)}")
        return cached_packages

    def _get_package_cache_path(self, package) -> str:
        """Get the cache directory path for a package.

        Args:
            package: Package object

        Returns:
            Path to package cache directory
        """
        # For scoped packages, keep the @ but replace / with -
        # For regular packages, use the name as-is
        if package.name.startswith("@"):
            safe_package_name = package.name.replace("/", "-")
        else:
            safe_package_name = package.name
            
        return os.path.join(
            self.package_cache_dir, f"{safe_package_name}-{package.version}"
        )
