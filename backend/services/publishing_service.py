"""Publishing Service.

Handles publishing packages to the secure repository. This service manages its own database sessions
and operations, following the service-first architecture pattern.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from database.operations.package_operations import PackageOperations
from database.operations.package_status_operations import PackageStatusOperations
from database.session_helper import SessionHelper

logger = logging.getLogger(__name__)


class PublishingService:
    """Service for publishing packages to secure repository.

    This service manages its own database sessions and operations,
    following the service-first architecture pattern.
    """

    def __init__(self) -> None:
        """Initialize the publishing service."""
        self.logger = logger

    def process_package_batch(
        self, max_packages: int = 3
    ) -> Dict[str, Any]:
        """Process a batch of packages for publishing.

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
                
                # Find packages that need publishing
                pending_packages = package_ops.get_packages_needing_publishing(max_packages)

                if not pending_packages:
                    return {
                        "success": True,
                        "processed_count": 0,
                        "successful_packages": 0,
                        "failed_packages": 0
                    }

                successful_packages = []
                failed_packages = []

                for package in pending_packages:
                    try:
                        result = self.process_single_package(package, status_ops)
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

                db.commit()

                return {
                    "success": True,
                    "processed_count": len(successful_packages) + len(failed_packages),
                    "successful_packages": len(successful_packages),
                    "failed_packages": len(failed_packages)
                }
        except Exception as e:
            self.logger.error(f"Error processing publishing batch: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "processed_count": 0,
                "successful_packages": 0,
                "failed_packages": 0
            }

    def process_single_package(
        self, package: Any, status_ops: PackageStatusOperations
    ) -> Dict[str, Any]:
        """Process a single package for publishing.

        Args:
            package: Package to process
            status_ops: Package status operations instance

        Returns:
            Dict with success status and any error message
        """
        try:
            # Update package status to "publishing"
            self._update_package_publish_status(
                package, "publishing", status_ops
            )

            # Attempt to publish the package
            # Note: This would call the actual publishing service
            # For now, we'll simulate the publishing logic
            success = self._publish_package_to_repository(package)

            if success:
                # Mark as published successfully
                self._mark_package_published(package, status_ops)
                return {"success": True, "error": None}
            else:
                # Mark as publish failed
                self._mark_package_publish_failed(package, "Publishing failed", status_ops)
                return {"success": False, "error": "Publishing failed"}

        except Exception as e:
            self.logger.error(
                f"Error processing package {package.name}@{package.version}: {str(e)}"
            )
            self._mark_package_publish_failed(package, str(e), status_ops)
            return {"success": False, "error": str(e)}

    def get_publishing_statistics(self) -> Dict[str, Any]:
        """Get current publishing statistics.

        Returns:
            Dict with publishing statistics
        """
        try:
            with SessionHelper.get_session() as db:
                package_ops = PackageOperations(db.session)
                
                # Get package counts by status
                approved_count = package_ops.count_packages_by_status("Approved")
                publishing_count = package_ops.count_packages_by_status("Publishing")
                published_count = package_ops.count_packages_by_status("Published")
                publish_failed_count = package_ops.count_packages_by_status("Publish Failed")

                return {
                    "approved_packages": approved_count,
                    "publishing_packages": publishing_count,
                    "published_packages": published_count,
                    "publish_failed_packages": publish_failed_count,
                    "timestamp": datetime.utcnow().isoformat(),
                }
        except Exception as e:
            self.logger.error(f"Error getting publishing statistics: {str(e)}")
            return {"error": str(e)}

    def retry_failed_packages(self) -> Dict[str, Any]:
        """Retry failed publishing packages.

        Returns:
            Dict with retry results
        """
        try:
            with SessionHelper.get_session() as db:
                package_ops = PackageOperations(db.session)
                status_ops = PackageStatusOperations(db.session)
                
                # Find packages that failed publishing
                failed_packages = package_ops.get_by_status("Publish Failed")
                
                if not failed_packages:
                    return {
                        "success": True,
                        "retried": 0,
                        "message": "No failed packages to retry"
                    }

                retried_count = 0
                for package in failed_packages:
                    try:
                        # Reset status to Approved to allow retry
                        status_ops.update_status(package.id, "Approved")
                        retried_count += 1
                    except Exception as e:
                        self.logger.error(
                            f"Error retrying package {package.name}@{package.version}: {str(e)}"
                        )

                db.commit()

                return {
                    "success": True,
                    "retried": retried_count,
                    "message": f"Retried {retried_count} failed packages"
                }
        except Exception as e:
            self.logger.error(f"Error retrying failed packages: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "retried": 0
            }

    def get_stuck_packages(
        self, stuck_threshold: datetime, package_ops: PackageOperations
    ) -> List[Any]:
        """Get packages that have been stuck in publishing state too long.

        Args:
            stuck_threshold: DateTime threshold for considering packages stuck
            package_ops: Package operations instance

        Returns:
            List of stuck packages
        """
        try:
            # Use operations to get stuck packages
            stuck_packages = package_ops.get_stuck_packages_in_publishing(
                stuck_threshold
            )
            return stuck_packages
        except Exception as e:
            self.logger.error(f"Error getting stuck packages: {str(e)}")
            return []

    def reset_stuck_packages(
        self, stuck_packages: List[Any], status_ops: PackageStatusOperations
    ) -> None:
        """Reset stuck packages to pending status.

        Args:
            stuck_packages: List of stuck packages to reset
            status_ops: Package status operations instance
        """
        for package in stuck_packages:
            try:
                self._update_package_publish_status(
                    package, "pending", status_ops
                )
                self.logger.info(
                    f"Reset stuck package {package.name}@{package.version} publish status to pending"
                )
            except Exception as e:
                self.logger.error(
                    f"Error resetting stuck package {package.name}@{package.version}: {str(e)}"
                )

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
        self, package: Any, status: str, status_ops: PackageStatusOperations
    ) -> None:
        """Update package publish status.

        Args:
            package: Package to update
            status: New publish status
            status_ops: Package status operations instance
        """
        if package.package_status:
            status_ops.update_status(package.id, status)

    def _mark_package_published(self, package: Any, status_ops: PackageStatusOperations) -> None:
        """Mark package as published successfully.

        Args:
            package: Package to mark as published
            status_ops: Package status operations instance
        """
        if package.package_status:
            status_ops.go_to_next_stage(package.id)

    def _mark_package_publish_failed(
        self, package: Any, error_message: str, status_ops: PackageStatusOperations
    ) -> None:
        """Mark package as publish failed.

        Args:
            package: Package to mark as failed
            error_message: Error message
            status_ops: Package status operations instance
        """
        if package.package_status:
            status_ops.update_status(package.id, "Publish Failed")
