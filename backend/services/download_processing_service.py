"""Download Processing Service.

Handles download processing for packages. This service manages its own database sessions
and operations, following the service-first architecture pattern.
"""

import logging
from typing import Any, Dict, List

from database.operations.package_operations import PackageOperations
from database.operations.package_status_operations import PackageStatusOperations
from database.session_helper import SessionHelper

logger = logging.getLogger(__name__)


class DownloadProcessingService:
    """Service for handling package download processing.

    This service manages its own database sessions and operations,
    following the service-first architecture pattern.
    """

    def __init__(self) -> None:
        """Initialize the download processing service."""
        self.logger = logger

    def process_package_batch(
        self, max_packages: int = 10
    ) -> Dict[str, Any]:
        """Process a batch of packages for downloading.

        Args:
            max_packages: Maximum number of packages to process

        Returns:
            Dict with processing results
        """
        try:
            with SessionHelper.get_session() as db:
                # Initialize operations
                package_ops = PackageOperations(db.session)
                status_ops = PackageStatusOperations(db.session)
                
                # Find packages that need downloading
                ready_packages = package_ops.get_by_status("Licence Checked")
                
                # Limit the number of packages processed
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

                for package in limited_packages:
                    result = self.process_single_package(package, status_ops)
                    if result["success"]:
                        successful_downloads += 1
                    else:
                        failed_downloads += 1

                db.commit()

                return {
                    "success": True,
                    "processed_count": len(limited_packages),
                    "successful_downloads": successful_downloads,
                    "failed_downloads": failed_downloads,
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

    def process_single_package(
        self, package: Any, status_ops: PackageStatusOperations
    ) -> Dict[str, Any]:
        """Process a single package for downloading.

        Args:
            package: Package to process
            status_ops: Package status operations instance

        Returns:
            Dict with processing results
        """
        try:
            # Check if package is already downloaded
            if self._is_package_already_downloaded(package):
                self._mark_package_downloaded(package, status_ops)
                return {"success": True, "message": "Already downloaded"}

            # Mark package as downloading
            self._mark_package_downloading(package, status_ops)

            # Perform the actual download
            download_success = self._perform_download(package)

            if download_success:
                self._mark_package_downloaded(package, status_ops)
                return {"success": True, "message": "Download completed"}
            else:
                self._mark_package_rejected(package, status_ops)
                return {"success": False, "error": "Download failed"}

        except Exception as e:
            self.logger.error(
                f"Error processing package {package.name}@{package.version}: {str(e)}"
            )
            self._mark_package_rejected(package, status_ops)
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

    def _mark_package_downloading(self, package: Any, status_ops: PackageStatusOperations) -> None:
        """Mark package as downloading.

        Args:
            package: Package to update
            status_ops: Package status operations instance
        """
        if package.package_status:
            status_ops.go_to_next_stage(package.id)

    def _mark_package_downloaded(self, package: Any, status_ops: PackageStatusOperations) -> None:
        """Mark package as downloaded.

        Args:
            package: Package to update
            status_ops: Package status operations instance
        """
        if package.package_status:
            status_ops.go_to_next_stage(package.id)

    def _mark_package_rejected(self, package: Any, status_ops: PackageStatusOperations) -> None:
        """Mark package as rejected.

        Args:
            package: Package to update
            status_ops: Package status operations instance
        """
        if package.package_status:
            status_ops.update_status(package.id, "Rejected")
