"""Package Cache Service.

Handles local package cache operations including storage, retrieval, and management
of downloaded packages in the local cache directory.
"""

import io
import logging
import os
import tarfile
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class PackageCacheService:
    """Service for managing local package cache operations."""

    def __init__(self) -> None:
        self.package_cache_dir = Path(os.getenv("PACKAGE_CACHE_DIR", "/app/package_cache"))

        # Ensure package cache directory exists
        self.package_cache_dir.mkdir(parents=True, exist_ok=True)

    def store_package_from_tarball(self, package: Any, tarball_content: bytes) -> Optional[str]:
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
            package_dir.mkdir(parents=True, exist_ok=True)

            # Extract tarball to package cache directory
            tarball_buffer = tarfile.open(fileobj=io.BytesIO(tarball_content), mode="r:gz")
            tarball_buffer.extractall(str(package_dir))
            tarball_buffer.close()

            # Return the actual path to the package directory
            return str(package_dir)

        except tarfile.TarError as e:
            logger.error(f"Error extracting tarball for {package.name}@{package.version}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error storing package {package.name}@{package.version}: {str(e)}")
            return None

    def is_package_cached(self, package: Any) -> bool:
        """Check if package is already cached locally.

        Args:
            package: Package object

        Returns:
            True if package exists in cache, False otherwise
        """
        package_dir = self._get_package_cache_path(package)
        return package_dir.exists() and package_dir.is_dir()

    def get_package_path(self, package: Any) -> Optional[str]:
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
            return str(package_dir / "package")
        return None

    def remove_package(self, package: Any) -> bool:
        """Remove a package from the cache.

        Args:
            package: Package object

        Returns:
            True if removal successful, False otherwise
        """
        try:
            package_dir = self._get_package_cache_path(package)
            if package_dir.exists():
                import shutil

                shutil.rmtree(str(package_dir))
                logger.info(f"Removed package {package.name}@{package.version} from cache")
                return True
            return True  # Already removed
        except Exception as e:
            logger.error(f"Error removing package {package.name}@{package.version}: {str(e)}")
            return False

    def get_cache_size(self) -> int:
        """Get the total size of the package cache in bytes.

        Returns:
            Total cache size in bytes
        """
        total_size = 0
        try:
            for filepath in self.package_cache_dir.rglob("*"):
                if filepath.is_file():
                    total_size += filepath.stat().st_size
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
            for item in self.package_cache_dir.iterdir():
                if item.is_dir():
                    # Parse package name and version from directory name
                    # Format: package-name-version or @scope-package-version
                    item_name = item.name
                    parts = item_name.split("-")

                    if item_name.startswith("@"):
                        formatted_package = self.format_scoped_package_name(parts)

                    else:
                        formatted_package = self.format_regular_package_name(parts)
                            
                    if not formatted_package:
                        continue

                    cached_packages.append(
                        {
                            "name": formatted_package[1],
                            "version": formatted_package[0],
                            "path": str(item),
                        }
                    )
        except Exception as e:
            logger.error(f"Error listing cached packages: {str(e)}")
        return cached_packages

    def _get_package_cache_path(self, package: Any) -> Path:
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

        return self.package_cache_dir / f"{safe_package_name}-{package.version}"


    def format_scoped_package_name(self, parts: str):
        # Scoped package: @scope-package-version
        if len(parts) >= 3:
            scope = parts[0]
            package_name = parts[1]
            version = "-".join(parts[2:])
            full_name = f"{scope}/{package_name}"

            return version, full_name
        else:
            return False
    
    def format_regular_package_name(self, parts: str):
        # Regular package: package-name-version
        if len(parts) >= 2:
            package_name = parts[0]
            version = "-".join(parts[1:])
            full_name = package_name

            return version, full_name
        else:
            return False
