"""Download Service.

Handles downloading packages from external npm registries and managing their local cache.
This service separates database operations from I/O work for optimal performance.
"""

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

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

    This service separates database operations from I/O work to minimize database session time.
    """

    def __init__(self) -> None:
        """Initialize the download service."""
        self.logger = logger

        # Download configuration
        self.download_timeout = int(os.getenv("DOWNLOAD_TIMEOUT", "60"))
        self.source_repository_url = os.getenv("SOURCE_REPOSITORY_URL", "https://registry.npmjs.org")
        self.database_url = os.getenv("DATABASE_URL", "")
        self.db_service = DatabaseService(self.database_url)

    def process_package_batch(self, max_packages: int = 5) -> Dict[str, Any]:
        """Process a batch of packages for downloading.

        This method separates database operations from I/O work:
        1. Get packages that need downloading (short DB session)
        2. Perform downloads (no DB session)
        3. Update database with results (short DB session)

        Args:
            max_packages: Maximum number of packages to process

        Returns:
            Dict with processing results
        """
        try:
            # Phase 1: Get package data (short DB session)
            packages_to_process = self._get_packages_for_download(max_packages)
            if not packages_to_process:
                return {
                    "success": True,
                    "processed_count": 0,
                    "successful_downloads": 0,
                    "failed_downloads": 0,
                    "already_cached": 0,
                    "total_packages": 0,
                }

            # Phase 2: Perform downloads (no DB session)
            download_results = self._perform_download_batch(packages_to_process)

            # Phase 3: Update database (short DB session)
            return self._update_download_results(download_results)

        except (ValueError, TypeError, AttributeError) as e:
            self.logger.error(f"Error processing download batch: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "processed_count": 0,
                "successful_downloads": 0,
                "failed_downloads": 0,
                "already_cached": 0,
                "total_packages": 0,
            }

    def _get_packages_for_download(self, max_packages: int) -> List[Any]:
        """Get packages that need downloading (short DB session).

        Args:
            max_packages: Maximum number of packages to retrieve

        Returns:
            List of packages that need downloading
        """
        with self.db_service.get_session() as session:
            package_ops = PackageOperations(session)
            return package_ops.get_by_status("Licence Checked")[:max_packages]

    def _perform_download_batch(self, packages: List[Any]) -> List[Tuple[Any, Dict[str, Any]]]:
        """Perform downloads without database sessions.

        Args:
            packages: List of packages to download

        Returns:
            List of tuples (package, result_dict)
        """
        results = []
        for package in packages:
            result = self._perform_download_work(package)
            results.append((package, result))
        return results

    def _perform_download_work(self, package: Any) -> Dict[str, Any]:
        """Pure I/O work - no database operations.

        Args:
            package: Package to download

        Returns:
            Dict with download result
        """
        try:
            # Check if already cached
            if self._is_package_already_downloaded(package):
                return {
                    "status": "already_cached",
                    "message": "Already downloaded",
                }

            # Perform download
            download_success = self._perform_download(package)

            if download_success:
                # Verify download
                if self._is_package_already_downloaded(package):
                    return {
                        "status": "success",
                        "message": "Download completed",
                    }
                else:
                    return {
                        "status": "failed",
                        "error": "Download completed but file not found in cache",
                    }
            else:
                return {"status": "failed", "error": "Download failed"}

        except Exception as e:
            self.logger.error(f"Error downloading package {package.name}@{package.version}: {str(e)}")
            return {"status": "failed", "error": str(e)}

    def _update_download_results(self, download_results: List[Tuple[Any, Dict[str, Any]]]) -> Dict[str, Any]:
        """Update database with download results (short DB session).

        Args:
            download_results: List of tuples (package, result_dict)

        Returns:
            Dict with processing results
        """
        successful_count = 0
        failed_count = 0
        already_cached_count = 0

        with self.db_service.get_session() as session:
            package_ops = PackageOperations(session)
            status_ops = PackageStatusOperations(session)

            for package, result in download_results:
                try:
                    # Verify package still needs processing (race condition protection)
                    current_package = package_ops.get_by_id(package.id)
                    if (
                        not current_package
                        or not current_package.package_status
                        or current_package.package_status.status != "Licence Checked"
                    ):
                        continue  # Skip if status changed

                    if result["status"] == "already_cached":
                        status_ops.update_status(package.id, "Downloaded")
                        already_cached_count += 1
                    elif result["status"] == "success":
                        status_ops.update_status(package.id, "Downloaded")
                        successful_count += 1
                    else:  # failed
                        status_ops.update_status(package.id, "Download Failed")
                        failed_count += 1

                except Exception as e:
                    self.logger.error(f"Error updating package {package.name}@{package.version}: {str(e)}")
                    failed_count += 1

            session.commit()

        # Log batch summary
        if successful_count > 0 or failed_count > 0 or already_cached_count > 0:
            self.logger.info(
                f"Download batch complete: {successful_count} downloaded, "
                f"{already_cached_count} already cached, {failed_count} failed"
            )

        return {
            "success": True,
            "processed_count": len(download_results),
            "successful_downloads": successful_count,
            "failed_downloads": failed_count,
            "already_cached": already_cached_count,
            "total_packages": len(download_results),
        }

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
            self.logger.error(f"Error checking if package is downloaded: {str(e)}")
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
            result = cache_service.store_package_from_tarball(package, tarball_content)
            return result is not None

        except Exception as e:
            self.logger.error(f"Error performing download: {str(e)}")
            return False

    def _download_package_tarball(self, package: Package) -> Optional[bytes]:
        """Download package tarball from npm registry.

        Args:
            package: Package object with name, version

        Returns:
            Tarball content as bytes if successful, None otherwise
        """
        try:
            # Construct download URL using SOURCE_REPOSITORY_URL
            download_url = self._construct_download_url(package)

            self.logger.info(f"Downloading package {package.name}@{package.version} from {download_url}")

            # Download tarball
            response = requests.get(download_url, timeout=self.download_timeout)

            if response.status_code != 200:
                self.logger.error(f"Failed to download package tarball: HTTP {response.status_code}")
                return None

            self.logger.info(f"Successfully downloaded tarball for {package.name}@{package.version}")
            return bytes(response.content)

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Network error downloading package {package.name}@{package.version}: {str(e)}")
            return None
        except (OSError, IOError, ValueError) as e:
            self.logger.error(f"Unexpected error downloading package {package.name}@{package.version}: {str(e)}")
            return None

    def _construct_download_url(self, package: Package) -> str:
        """Construct download URL using SOURCE_REPOSITORY_URL.

        Args:
            package: Package object with name and version

        Returns:
            Constructed download URL
        """
        # If package has an npm_url that starts with the same base as source_repository_url, use it directly
        if package.npm_url and package.npm_url.startswith(self.source_repository_url):
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
