"""Download Service.

Handles downloading packages from external npm registries and managing their local cache.
This service manages its own database sessions and operations, following the service-first architecture pattern.
"""

import logging
import os
from typing import Any, Dict, List, Optional

import requests

from database.operations.package_operations import PackageOperations
from database.operations.package_status_operations import PackageStatusOperations
from database.session_helper import SessionHelper

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
        self._session = None
        self._package_ops = None
        self._status_ops = None
        
        # Download configuration
        self.download_timeout = int(os.getenv("DOWNLOAD_TIMEOUT", "60"))
        self.source_repository_url = os.getenv("SOURCE_REPOSITORY_URL", "https://registry.npmjs.org")

    def _setup_operations(self, session):
        """Set up operations instances for the current session."""
        self._session = session
        self._package_ops = PackageOperations(session)
        self._status_ops = PackageStatusOperations(session)

    def process_package_batch(
        self, max_packages: int = 5
    ) -> Dict[str, Any]:
        """Process a batch of packages for downloading.

        Args:
            max_packages: Maximum number of packages to process (reduced for better performance)

        Returns:
            Dict with processing results
        """
        try:
            with SessionHelper.get_session() as db:
                # Set up operations
                self._setup_operations(db.session)
                
                # Find packages that need downloading
                ready_packages = self._package_ops.get_by_status("Licence Checked")
                
                # Limit the number of packages processed (smaller batches)
                limited_packages = ready_packages[:max_packages]

                if not limited_packages:
                    return {
                        "success": True,
                        "processed_count": 0,
                        "successful_downloads": 0,
                        "failed_downloads": 0,
                        "total_packages": 0
                    }

                successful_downloads = 0
                failed_downloads = 0
                already_cached = 0

                for package in limited_packages:
                    result = self.process_single_package(package)
                    if result["success"]:
                        if result["message"] == "Already downloaded":
                            already_cached += 1
                        else:
                            successful_downloads += 1
                    else:
                        failed_downloads += 1

                db.commit()

                # Log batch summary
                if successful_downloads > 0 or failed_downloads > 0 or already_cached > 0:
                    self.logger.info(
                        f"Download batch complete: {successful_downloads} downloaded, "
                        f"{already_cached} already cached, {failed_downloads} failed"
                    )

                return {
                    "success": True,
                    "processed_count": len(limited_packages),
                    "successful_downloads": successful_downloads,
                    "failed_downloads": failed_downloads,
                    "already_cached": already_cached,
                    "total_packages": len(limited_packages)
                }
        except Exception as e:
            self.logger.error(f"Error processing download batch: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "processed_count": 0,
                "successful_downloads": 0,
                "failed_downloads": 0,
                "total_packages": 0
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
                    return {"success": False, "error": "Download completed but file not found in cache"}
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
            return cache_service.store_package_from_tarball(package, tarball_content)
            
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
            
            self.logger.info(f"Downloading package {package.name}@{package.version} from {download_url}")

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
            return response.content

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

    def _construct_download_url(self, package: Any) -> str:
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
        if package.name.startswith("@"):
            # For scoped packages: @scope/package -> @scope/package (no URL encoding needed)
            return f"{self.source_repository_url}/{package.name}/-/{package.name.split('/')[-1]}-{package.version}.tgz"
        else:
            # For regular packages: package -> package
            return f"{self.source_repository_url}/{package.name}/-/{package.name}-{package.version}.tgz"

    def _mark_package_downloading(self, package: Any) -> None:
        """Mark package as downloading.

        Args:
            package: Package to update
        """
        if package.package_status:
            self._status_ops.go_to_next_stage(package.id)

    def _mark_package_downloaded(self, package: Any) -> None:
        """Mark package as downloaded.

        Args:
            package: Package to update
        """
        try:
            if package.package_status:
                self._status_ops.go_to_next_stage(package.id)
            else:
                self.logger.warning(f"Package {package.name}@{package.version} has no package_status")
        except Exception as e:
            self.logger.error(f"Error updating status for package {package.name}@{package.version}: {str(e)}")

    def _mark_package_download_failed(self, package: Any) -> None:
        """Mark package as download failed.

        Args:
            package: Package to update
        """
        if package.package_status:
            self._status_ops.update_status(package.id, "Download Failed")
