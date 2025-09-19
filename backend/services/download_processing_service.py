"""Download Processing Service.

Handles download processing for packages. This service is used
by both the API (for immediate processing) and workers (for background processing).

This service works with entity-based operations structure and focuses purely on business logic.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class DownloadProcessingService:
    """Service for handling package download processing.

    This service handles the business logic of package downloading and
    status management. It works with database operations passed in from the caller
    (worker or API) to maintain separation of concerns.
    """

    def __init__(self) -> None:
        """Initialize the download processing service."""
        self.logger = logger

    def process_package_batch(
        self, packages: List[Any], ops: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process a batch of packages for downloading.

        Args:
            packages: List of packages to process
            ops: Dictionary of database operations instances

        Returns:
            Dict with processing results
        """
        try:
            successful_downloads = 0
            failed_downloads = 0

            for package in packages:
                result = self.process_single_package(package, ops)
                if result["success"]:
                    successful_downloads += 1
                else:
                    failed_downloads += 1

            return {
                "success": True,
                "successful_downloads": successful_downloads,
                "failed_downloads": failed_downloads,
                "total_packages": len(packages)
            }
        except Exception as e:
            self.logger.error(f"Error processing download batch: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "successful_downloads": 0,
                "failed_downloads": 0,
                "total_packages": len(packages)
            }

    def process_single_package(
        self, package: Any, ops: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process a single package for downloading.

        Args:
            package: Package to process
            ops: Dictionary of database operations instances

        Returns:
            Dict with processing results
        """
        try:
            # Check if package is already downloaded
            if self._is_package_already_downloaded(package):
                self._mark_package_downloaded(package, ops)
                return {"success": True, "message": "Already downloaded"}

            # Mark package as downloading
            self._mark_package_downloading(package, ops)

            # Perform the actual download
            download_success = self._perform_download(package)

            if download_success:
                self._mark_package_downloaded(package, ops)
                return {"success": True, "message": "Download completed"}
            else:
                self._mark_package_rejected(package, ops)
                return {"success": False, "error": "Download failed"}

        except Exception as e:
            self.logger.error(
                f"Error processing package {package.name}@{package.version}: {str(e)}"
            )
            self._mark_package_rejected(package, ops)
            return {"success": False, "error": str(e)}

    def get_stuck_packages(
        self, stuck_threshold: datetime, ops: Dict[str, Any]
    ) -> List[Any]:
        """Get packages that have been stuck in Downloading state too long.

        Args:
            stuck_threshold: DateTime threshold for considering packages stuck
            ops: Dictionary of database operations instances

        Returns:
            List of stuck packages
        """
        try:
            # Use operations to get stuck packages
            stuck_packages = ops.package.get_stuck_packages_in_downloading(
                stuck_threshold
            )
            return stuck_packages
        except Exception as e:
            self.logger.error(f"Error getting stuck packages: {str(e)}")
            return []

    def reset_stuck_packages(
        self, stuck_packages: List[Any], ops: Dict[str, Any]
    ) -> None:
        """Reset stuck packages to Licence Checked status.

        Args:
            stuck_packages: List of stuck packages to reset
            ops: Dictionary of database operations instances
        """
        for package in stuck_packages:
            try:
                ops.package_status.update_status(
                    package.id, "Licence Checked"
                )
                self.logger.info(
                    f"Reset stuck package {package.name}@{package.version} to Licence Checked"
                )
            except Exception as e:
                self.logger.error(
                    f"Error resetting stuck package {package.name}@{package.version}: {str(e)}"
                )

    def _is_package_already_downloaded(self, package: Any) -> bool:
        """Check if package is already downloaded.

        Args:
            package: Package to check

        Returns:
            True if already downloaded, False otherwise
        """
        try:
            # Import here to avoid circular imports
            from services.download_service import DownloadService
            
            download_service = DownloadService()
            return download_service.is_package_downloaded(package)
        except Exception as e:
            self.logger.error(f"Error checking if package is downloaded: {str(e)}")
            return False

    def _perform_download(self, package: Any) -> bool:
        """Perform the actual download using DownloadService.

        Args:
            package: Package to download

        Returns:
            True if download successful, False otherwise
        """
        try:
            # Import here to avoid circular imports
            from services.download_service import DownloadService
            
            download_service = DownloadService()
            return download_service.download_package(package)
        except Exception as e:
            self.logger.error(f"Error performing download: {str(e)}")
            return False

    def _mark_package_downloading(self, package: Any, ops: Dict[str, Any]) -> None:
        """Mark package as downloading.

        Args:
            package: Package to update
            ops: Dictionary of database operations instances
        """
        if package.package_status:
            ops.package_status.update_status(
                package.id, "Downloading"
            )

    def _mark_package_downloaded(self, package: Any, ops: Dict[str, Any]) -> None:
        """Mark package as downloaded.

        Args:
            package: Package to update
            ops: Dictionary of database operations instances
        """
        if package.package_status:
            ops.package_status.update_status(
                package.id, "Downloaded"
            )

    def _mark_package_rejected(self, package: Any, ops: Dict[str, Any]) -> None:
        """Mark package as rejected.

        Args:
            package: Package to update
            ops: Dictionary of database operations instances
        """
        if package.package_status:
            ops.package_status.update_status(
                package.id, "Rejected"
            )
