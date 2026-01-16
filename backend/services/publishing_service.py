"""Publishing Service.

Handles publishing packages to the secure repository. This service separates database operations
from I/O work for optimal performance.
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Tuple

from database.operations.package_operations import PackageOperations
from database.operations.package_status_operations import (
    PackageStatusOperations,
)
from database.service import DatabaseService

logger = logging.getLogger(__name__)

# define constants
PUBLISH_FAILED_STR = "Publish Failed"


class PublishingService:
    """Service for publishing packages to secure repository.

    This service separates database operations from I/O work to minimize database session time.
    """

    def __init__(self) -> None:
        """Initialize the publishing service."""
        self.logger = logger
        self.database_url = os.getenv("DATABASE_URL", "")
        self.db_service = DatabaseService(self.database_url)

    def process_package_batch(self, max_packages: int = 3) -> Dict[str, Any]:
        """Process a batch of packages for publishing.

        This method separates database operations from I/O work:
        1. Get packages that need publishing (short DB session)
        2. Perform publishing (no DB session)
        3. Update database with results (short DB session)

        Args:
            max_packages: Maximum number of packages to process

        Returns:
            Dict with processing results
        """
        try:
            # Phase 1: Get package data (short DB session)
            packages_to_process = self._get_packages_for_publishing(max_packages)
            if not packages_to_process:
                return {
                    "success": True,
                    "processed_count": 0,
                    "successful_packages": 0,
                    "failed_packages": 0,
                }

            # Phase 2: Perform publishing (no DB session)
            publish_results = self._perform_publish_batch(packages_to_process)

            # Phase 3: Update database (short DB session)
            return self._update_publish_results(publish_results)

        except Exception as e:
            self.logger.error(f"Error processing publishing batch: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "processed_count": 0,
                "successful_packages": 0,
                "failed_packages": 0,
            }

    def _get_packages_for_publishing(self, max_packages: int) -> List[Any]:
        """Get packages that need publishing (short DB session).

        Args:
            max_packages: Maximum number of packages to retrieve

        Returns:
            List of packages that need publishing
        """
        with self.db_service.get_session() as session:
            package_ops = PackageOperations(session)
            return package_ops.get_packages_needing_publishing(max_packages)

    def _perform_publish_batch(self, packages: List[Any]) -> List[Tuple[Any, Dict[str, Any]]]:
        """Perform publishing without database sessions.

        Args:
            packages: List of packages to publish

        Returns:
            List of tuples (package, result_dict)
        """
        results = []
        for package in packages:
            result = self._perform_publish_work(package)
            results.append((package, result))
        return results

    def _perform_publish_work(self, package: Any) -> Dict[str, Any]:
        """Pure I/O work - no database operations.

        Args:
            package: Package to publish

        Returns:
            Dict with publish result
        """
        try:
            # Attempt to publish the package
            success = self._publish_package_to_repository(package)

            if success:
                return {
                    "status": "success",
                    "message": "Published successfully",
                }
            else:
                return {"status": "failed", "error": "Publishing failed"}

        except Exception as e:
            self.logger.error(f"Error publishing package {package.name}@{package.version}: {str(e)}")
            return {"status": "failed", "error": str(e)}

    def _update_publish_results(self, publish_results: List[Tuple[Any, Dict[str, Any]]]) -> Dict[str, Any]:
        """Update database with publish results (short DB session).

        Args:
            publish_results: List of tuples (package, result_dict)

        Returns:
            Dict with processing results
        """
        successful_count = 0
        failed_count = 0

        with self.db_service.get_session() as session:
            package_ops = PackageOperations(session)
            status_ops = PackageStatusOperations(session)

            for package, result in publish_results:
                try:
                    # Verify package still needs processing (race condition protection)
                    current_package = package_ops.get_by_id(package.id)
                    if (
                        not current_package
                        or not current_package.package_status
                        or current_package.package_status.status != "Approved"
                    ):
                        continue  # Skip if status changed
                    
                    logger.info(f"The status of result is {result['status']} for package {package.name}@{package.version}")
                    if result["status"] == "success":
                        status_ops.update_status(package.id, "Published")
                        successful_count += 1
                    else:  # failed
                        status_ops.update_status(package.id, PUBLISH_FAILED_STR)
                        failed_count += 1

                    logger.info(f"The successful count is {successful_count} and failed count is {failed_count}")
                except Exception as e:
                    self.logger.error(f"Error updating package {package.name}@{package.version}: {str(e)}")
                    failed_count += 1
            logger.info(f"The final successful count is {successful_count} and failed count is {failed_count}")
            session.commit()

        # Log batch summary
        if successful_count > 0 or failed_count > 0:
            self.logger.info(f"Publishing batch complete: {successful_count} successful, {failed_count} failed")

        return {
            "success": True,
            "processed_count": len(publish_results),
            "successful_packages": successful_count,
            "failed_packages": failed_count,
        }

    def get_publishing_statistics(self) -> Dict[str, Any]:
        """Get current publishing statistics.

        Returns:
            Dict with publishing statistics
        """
        try:
            with self.db_service.get_session() as session:
                package_ops = PackageOperations(session)

                # Get package counts by status
                approved_count = package_ops.count_packages_by_status("Approved")
                publishing_count = package_ops.count_packages_by_status("Publishing")
                published_count = package_ops.count_packages_by_status("Published")
                publish_failed_count = package_ops.count_packages_by_status(PUBLISH_FAILED_STR)

                return {
                    "approved_packages": approved_count,
                    "publishing_packages": publishing_count,
                    "published_packages": published_count,
                    "publish_failed_packages": publish_failed_count,
                    "timestamp":datetime.now(timezone.utc).isoformat(),
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
            with self.db_service.get_session() as session:
                package_ops = PackageOperations(session)
                status_ops = PackageStatusOperations(session)

                # Find packages that failed publishing
                failed_packages = package_ops.get_by_status(PUBLISH_FAILED_STR)

                if not failed_packages:
                    return {
                        "success": True,
                        "retried": 0,
                        "message": "No failed packages to retry",
                    }

                retried_count = 0
                for package in failed_packages:
                    try:
                        # Reset status to Approved to allow retry
                        if package.id is not None:
                            status_ops.update_status(package.id, "Approved")
                            retried_count += 1
                    except Exception as e:
                        self.logger.error(f"Error retrying package {package.name}@{package.version}: {str(e)}")

                session.commit()

                return {
                    "success": True,
                    "retried": retried_count,
                    "message": f"Retried {retried_count} failed packages",
                }
        except Exception as e:
            self.logger.error(f"Error retrying failed packages: {str(e)}")
            return {"success": False, "error": str(e), "retried": 0}

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
            from services.npm_registry_publishing_service import (
                NpmRegistryPublishingService,
            )

            publishing_service = NpmRegistryPublishingService()
            return publishing_service.publish_to_secure_repo(package)
        except Exception as e:
            self.logger.error(f"Error publishing package to repository: {str(e)}")
            return False
