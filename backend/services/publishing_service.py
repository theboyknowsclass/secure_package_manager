"""Publishing Service.

Handles publishing packages to the secure repository. This service is used
by both the API (for immediate publishing) and workers (for background publishing).

This service works with entity-based operations structure and focuses purely on business logic.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class PublishingService:
    """Service for publishing packages to secure repository.

    This service handles the business logic of package publishing and
    status management. It works with database operations passed in from the caller
    (worker or API) to maintain separation of concerns.
    """

    def __init__(self) -> None:
        """Initialize the publishing service."""
        self.logger = logger

    def process_package_batch(
        self, packages: List[Any], ops: Dict[str, Any]
    ) -> Tuple[List[Any], List[Any]]:
        """Process a batch of packages for publishing.

        Args:
            packages: List of packages to process
            ops: Dictionary of database operations instances

        Returns:
            Tuple of (successful_packages, failed_packages)
        """
        successful_packages = []
        failed_packages = []

        for package in packages:
            try:
                result = self.process_single_package(package, ops)
                if result["success"]:
                    successful_packages.append(package)
                else:
                    failed_packages.append({
                        "package": package,
                        "error": result["error"]
                    })
            except Exception as e:
                self.logger.error(
                    f"Error processing package {package.name}@{package.version}: {str(e)}"
                )
                failed_packages.append({
                    "package": package,
                    "error": str(e)
                })

        return successful_packages, failed_packages

    def process_single_package(
        self, package: Any, ops: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process a single package for publishing.

        Args:
            package: Package to process
            ops: Dictionary of database operations instances

        Returns:
            Dict with success status and any error message
        """
        try:
            # Update package status to "publishing"
            self._update_package_publish_status(
                package, "publishing", ops
            )

            # Attempt to publish the package
            # Note: This would call the actual publishing service
            # For now, we'll simulate the publishing logic
            success = self._publish_package_to_repository(package)

            if success:
                # Mark as published successfully
                self._mark_package_published(package, ops)
                return {"success": True, "error": None}
            else:
                # Mark as publish failed
                self._mark_package_publish_failed(package, "Publishing failed", ops)
                return {"success": False, "error": "Publishing failed"}

        except Exception as e:
            self.logger.error(
                f"Error processing package {package.name}@{package.version}: {str(e)}"
            )
            self._mark_package_publish_failed(package, str(e), ops)
            return {"success": False, "error": str(e)}

    def get_stuck_packages(
        self, stuck_threshold: datetime, ops: Dict[str, Any]
    ) -> List[Any]:
        """Get packages that have been stuck in publishing state too long.

        Args:
            stuck_threshold: DateTime threshold for considering packages stuck
            ops: Dictionary of database operations instances

        Returns:
            List of stuck packages
        """
        try:
            # Use operations to get stuck packages
            stuck_packages = ops.package.get_stuck_packages_in_publishing(
                stuck_threshold
            )
            return stuck_packages
        except Exception as e:
            self.logger.error(f"Error getting stuck packages: {str(e)}")
            return []

    def reset_stuck_packages(
        self, stuck_packages: List[Any], ops: Dict[str, Any]
    ) -> None:
        """Reset stuck packages to pending status.

        Args:
            stuck_packages: List of stuck packages to reset
            ops: Dictionary of database operations instances
        """
        for package in stuck_packages:
            try:
                self._update_package_publish_status(
                    package, "pending", ops
                )
                self.logger.info(
                    f"Reset stuck package {package.name}@{package.version} publish status to pending"
                )
            except Exception as e:
                self.logger.error(
                    f"Error resetting stuck package {package.name}@{package.version}: {str(e)}"
                )

    def get_publishing_statistics(self, ops: Dict[str, Any]) -> Dict[str, Any]:
        """Get current publishing statistics.

        Args:
            ops: Dictionary of database operations instances

        Returns:
            Dict with publishing statistics
        """
        try:
            # Get package counts by publish status
            publish_status_counts = {}
            for status in ["pending", "publishing", "published", "failed"]:
                count = ops.package.count_packages_by_publish_status(status)
                publish_status_counts[status] = count

            # Get approved packages count
            approved_count = ops.package.count_packages_by_status("Approved")

            return {
                "approved_packages": approved_count,
                "publish_status_counts": publish_status_counts,
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"Error getting publishing statistics: {str(e)}")
            return {"error": str(e)}

    def retry_failed_packages(self, ops: Dict[str, Any]) -> Dict[str, Any]:
        """Retry failed publishing packages.

        Args:
            ops: Dictionary of database operations instances

        Returns:
            Dict with retry results
        """
        try:
            failed_packages = ops.package.get_packages_by_publish_status("failed")
            
            if not failed_packages:
                return {
                    "message": "No failed publishing packages found",
                    "retried": 0,
                }

            retried_count = 0
            for package in failed_packages:
                try:
                    self._update_package_publish_status(
                        package, "pending", ops
                    )
                    retried_count += 1
                except Exception as e:
                    self.logger.error(
                        f"Error retrying package {package.name}@{package.version}: {str(e)}"
                    )

            return {
                "message": f"Retried {retried_count} packages",
                "retried": retried_count,
            }
        except Exception as e:
            self.logger.error(f"Error retrying failed packages: {str(e)}")
            return {"error": str(e)}

    def _publish_package_to_repository(self, package: Any) -> bool:
        """Publish package to the secure repository.

        Args:
            package: Package to publish

        Returns:
            True if successful, False otherwise
        """
        # This would integrate with the existing NpmRegistryPublishingService
        # For now, we'll simulate the publishing logic
        try:
            # Import here to avoid circular imports
            from services.npm_registry_publishing_service import NpmRegistryPublishingService
            
            publishing_service = NpmRegistryPublishingService()
            return publishing_service.publish_to_secure_repo(package)
        except Exception as e:
            self.logger.error(f"Error publishing package to repository: {str(e)}")
            return False

    def _update_package_publish_status(
        self, package: Any, status: str, ops: Dict[str, Any]
    ) -> None:
        """Update package publish status.

        Args:
            package: Package to update
            status: New publish status
            ops: Dictionary of database operations instances
        """
        if package.package_status:
            ops.package_status.update_package_publish_status(
                package.id, status
            )

    def _mark_package_published(self, package: Any, ops: Dict[str, Any]) -> None:
        """Mark package as published successfully.

        Args:
            package: Package to mark as published
            ops: Dictionary of database operations instances
        """
        if package.package_status:
            ops.package_status.mark_package_published(package.id)

    def _mark_package_publish_failed(
        self, package: Any, error_message: str, ops: Dict[str, Any]
    ) -> None:
        """Mark package as publish failed.

        Args:
            package: Package to mark as failed
            error_message: Error message
            ops: Dictionary of database operations instances
        """
        if package.package_status:
            ops.package_status.mark_package_publish_failed(
                package.id, error_message
            )
