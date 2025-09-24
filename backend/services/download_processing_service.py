"""Download Service.

Handles downloading packages from external npm registries and managing their local cache.
This service manages its own database sessions and operations, following the service-first architecture pattern.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from database.models import Package
from database.operations.package_operations import PackageOperations
from database.operations.package_status_operations import (
    PackageStatusOperations,
)
from database.service import DatabaseService

logger = logging.getLogger(__name__)


class DownloadService:
    """Service for downloading packages from external npm registries and managing local cache.

    This service manages its own database sessions and operations,
    following the service-first architecture pattern.
    """

    def __init__(self) -> None:
        """Initialize the download service."""
        self.logger = logger
        # Operations instances (set up in _setup_operations)
        self._session: Optional[Any] = None
        self._package_ops: Optional[PackageOperations] = None
        self._status_ops: Optional[PackageStatusOperations] = None
        self.database_url = os.getenv("DATABASE_URL", "")
        self.db_service = DatabaseService(self.database_url)

        # Download configuration
        self.download_timeout = int(os.getenv("DOWNLOAD_TIMEOUT", "60"))
        self.source_repository_url = os.getenv(
            "SOURCE_REPOSITORY_URL", "https://registry.npmjs.org"
        )

    def _setup_operations(self, session: Any) -> None:
        """Set up operations instances for the current session."""
        self._session = session
        self._package_ops = PackageOperations(session)
        self._status_ops = PackageStatusOperations(session)

    def process_package_batch(self, max_packages: int = 5) -> Dict[str, Any]:
        """Process a batch of packages for downloading.

        Args:
            max_packages: Maximum number of packages to process (reduced for better performance)

        Returns:
            Dict with processing results
        """
        try:
            with self.db_service.get_session() as session:
                # Set up operations
                self._setup_operations(session)
                
                # MyPy assertion - operations are guaranteed to be set after _setup_operations
                assert self._package_ops is not None
                assert self._status_ops is not None

                # Find packages that need downloading
                ready_packages = self._package_ops.get_by_status(
                    "Licence Checked"
                )

                # Limit the number of packages processed (smaller batches)
                limited_packages = ready_packages[:max_packages]

                if not limited_packages:
                    return {
                        "success": True,
                        "processed_count": 0,
                        "successful_downloads": 0,
                        "failed_downloads": 0,
                        "total_packages": 0,
                    }

                successful_downloads = 0
                failed_downloads = 0

                for package in limited_packages:
                    result = self.process_single_package(package)
                    if result["success"]:
                        successful_downloads += 1
                    else:
                        failed_downloads += 1

                session.commit()

                return {
                    "success": True,
                    "processed_count": len(limited_packages),
                    "successful_downloads": successful_downloads,
                    "failed_downloads": failed_downloads,
                    "total_packages": len(limited_packages),
                }
        except Exception as e:
            self.logger.error(f"Error processing download batch: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "processed_count": 0,
                "successful_downloads": 0,
                "failed_downloads": 0,
                "total_packages": 0,
            }

    def process_single_package(self, package: Any) -> Dict[str, Any]:
        """Process a single package for downloading.

        Args:
            package: Package to process

        Returns:
            Dict with processing results
        """
        try:
            # Check if package is already downloaded
            if self._is_package_already_downloaded(package):
                self._mark_package_downloaded(package)
                return {"success": True, "message": "Already downloaded"}

            # Mark package as downloading
            self._mark_package_downloading(package)

            # Perform the actual download
            download_success = self._perform_download(package)

            if download_success:
                # Double-check that the package is actually in the cache before marking as downloaded
                if self._is_package_already_downloaded(package):
                    self._mark_package_downloaded(package)
                    return {"success": True, "message": "Download completed"}
                else:
                    self.logger.error(
                        f"Download reported success but package not found in cache: {package.name}@{package.version}"
                    )
                    self._mark_package_download_failed(package)
                    return {
                        "success": False,
                        "error": "Download completed but file not found in cache",
                    }
            else:
                self._mark_package_download_failed(package)
                return {"success": False, "error": "Download failed"}

        except Exception as e:
            self.logger.error(
                f"Error processing package {package.name}@{package.version}: {str(e)}"
            )
            self._mark_package_download_failed(package)
            return {"success": False, "error": str(e)}

    def _is_package_already_downloaded(self, package: Any) -> bool:
        """Check if package is already downloaded.

        Args:
            package: Package to check

        Returns:
            True if already downloaded, False otherwise
        """
        try:
            # Import here to avoid circular imports
            from services.package_cache_service import PackageCacheService

            cache_service = PackageCacheService()
            return cache_service.is_package_cached(package)
        except Exception as e:
            self.logger.error(
                f"Error checking if package is downloaded: {str(e)}"
            )
            return False

    def _perform_download(self, package: Any) -> bool:
        """Perform the actual download from external registry and store in cache.

        Args:
            package: Package to download

        Returns:
            True if download successful, False otherwise
        """
        try:
            # Import here to avoid circular imports
            from services.package_cache_service import PackageCacheService

            # Download tarball from external registry
            tarball_content = self._download_package_tarball(package)

            if tarball_content is None:
                return False

            # Store tarball in local cache
            cache_service = PackageCacheService()
            cache_path = cache_service.store_package_from_tarball(
                package, tarball_content
            )

            if cache_path is None:
                return False

            # Update package with download information (cache_path, size, checksum)
            with self.db_service.get_session() as session:
                from database.operations.package_status_operations import (
                    PackageStatusOperations,
                )

                status_ops = PackageStatusOperations(session)

                # Calculate file size and checksum
                file_size = None
                checksum = None
                try:
                    # Calculate size of the extracted package directory
                    package_dir = Path(cache_path) / "package"
                    if package_dir.exists():
                        file_size = sum(
                            filepath.stat().st_size
                            for filepath in package_dir.rglob("*")
                            if filepath.is_file()
                        )

                    # Calculate checksum of the original tarball content
                    if tarball_content:
                        import hashlib

                        checksum = hashlib.sha256(tarball_content).hexdigest()
                except Exception as e:
                    self.logger.warning(
                        f"Could not calculate file size/checksum for {package.name}@{package.version}: {str(e)}"
                    )

                if status_ops.update_download_info(
                    package.id, cache_path, file_size, checksum
                ):
                    session.commit()
                    self.logger.info(
                        f"Updated download info for {package.name}@{package.version}: cache_path={cache_path}, size={file_size}, checksum={checksum[:16] if checksum else 'None'}..."
                    )
                    return True
                else:
                    self.logger.error(
                        f"Failed to update download info for {package.name}@{package.version}"
                    )
                    return False

        except Exception as e:
            self.logger.error(f"Error performing download: {str(e)}")
            return False

    def _download_package_tarball(self, package: Any) -> Optional[bytes]:
        """Download package tarball from npm registry.

        Args:
            package: Package object with name, version

        Returns:
            Tarball content as bytes if successful, None otherwise
        """
        try:
            # Construct download URL using SOURCE_REPOSITORY_URL
            download_url = self._construct_download_url(package)

            self.logger.info(
                f"Downloading package {package.name}@{package.version} from {download_url}"
            )

            # Download tarball
            response = requests.get(
                download_url, timeout=self.download_timeout
            )

            if response.status_code != 200:
                self.logger.error(
                    f"Failed to download package tarball: HTTP {response.status_code}"
                )
                return None

            self.logger.info(
                f"Successfully downloaded tarball for {package.name}@{package.version}"
            )
            return bytes(response.content)

        except requests.exceptions.RequestException as e:
            self.logger.error(
                f"Network error downloading package {package.name}@{package.version}: {str(e)}"
            )
            return None
        except Exception as e:
            self.logger.error(
                f"Unexpected error downloading package {package.name}@{package.version}: {str(e)}"
            )
            return None

    def _construct_download_url(self, package: Package) -> str:
        """Construct download URL using SOURCE_REPOSITORY_URL.

        Args:
            package: Package object with name and version

        Returns:
            Constructed download URL
        """
        # If package has an npm_url that starts with the same base as source_repository_url, use it directly
        if package.npm_url and package.npm_url.startswith(
            self.source_repository_url
        ):
            return package.npm_url

        # Otherwise, use custom logic to construct the URL
        # Handle scoped packages (e.g., @babel/core)
        package_name = package.name
        if package_name.startswith("@"):
            # For scoped packages: @scope/package -> @scope/package (no URL encoding needed)
            return f"{self.source_repository_url}/{package_name}/-/{package_name.split('/')[-1]}-{package.version}.tgz"
        else:
            # For regular packages: package -> package
            return f"{self.source_repository_url}/{package_name}/-/{package_name}-{package.version}.tgz"

    def _mark_package_downloading(self, package: Any) -> None:
        """Mark package as downloading.

        Args:
            package: Package to update
        """
        assert self._status_ops is not None
        if package.package_status:
            self._status_ops.go_to_next_stage(package.id)

    def _mark_package_downloaded(self, package: Any) -> None:
        """Mark package as downloaded.

        Args:
            package: Package to update
        """
        assert self._status_ops is not None
        if package.package_status:
            self._status_ops.go_to_next_stage(package.id)

    def _mark_package_download_failed(self, package: Any) -> None:
        """Mark package as download failed.

        Args:
            package: Package to update
        """
        assert self._status_ops is not None
        if package.package_status:
            self._status_ops.update_status(package.id, "Download Failed")
