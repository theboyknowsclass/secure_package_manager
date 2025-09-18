"""
Package Publishing Worker

Handles background publishing of approved packages to the secure repository.
Processes packages that are approved but not yet published.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict

from database.service import DatabaseService
from database.operations import DatabaseOperations
from database.models import Package, PackageStatus
from services.package_service import PackageService
from workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class PublishWorker(BaseWorker):
    """Background worker for publishing approved packages"""
    
    # Extend base environment variables with publish-specific ones
    required_env_vars = BaseWorker.required_env_vars + [
        "TARGET_REPOSITORY_URL"
    ]

    def __init__(self, sleep_interval: int = 30):
        super().__init__("PackagePublisher", sleep_interval)
        self.package_service = None
        self.db_service = None
        self.ops = None
        self.max_packages_per_cycle = 3  # Process max 3 packages per cycle (publishing is slow)
        self.stuck_package_timeout = timedelta(hours=2)  # Consider packages stuck after 2 hours

    def initialize(self) -> None:
        """Initialize services"""
        logger.info("Initializing PublishWorker services...")
        self.package_service = PackageService()
        
        # Initialize database service
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is required")
        
        self.db_service = DatabaseService(database_url)
        logger.info("PublishWorker services initialized")

    def process_cycle(self) -> None:
        """Process one cycle of package publishing"""
        try:
            with self.db_service.get_session() as session:
                self.ops = DatabaseOperations(session)
                # Check for stuck packages first
                self._handle_stuck_packages()

                # Process packages ready for publishing
                self._process_pending_publishing()

        except Exception as e:
            logger.error(f"Error in package publishing cycle: {str(e)}", exc_info=True)

    def _handle_stuck_packages(self) -> None:
        """Handle packages that have been stuck in publishing state too long"""
        try:
            stuck_threshold = datetime.utcnow() - self.stuck_package_timeout
            stuck_publish_statuses = ["publishing", "failed"]

            # Get packages with stuck publish status
            stuck_packages = self.ops.get_packages_by_publish_statuses(stuck_publish_statuses, Package, PackageStatus)
            stuck_packages = [p for p in stuck_packages if p.package_status and p.package_status.updated_at < stuck_threshold]

            if stuck_packages:
                logger.warning(f"Found {len(stuck_packages)} stuck packages in publishing, resetting publish status")

                for package in stuck_packages:
                    if package.package_status:
                        package.package_status.publish_status = "pending"
                        package.package_status.updated_at = datetime.utcnow()
                        logger.info(f"Reset stuck package {package.name}@{package.version} publish status to pending")

        except Exception as e:
            logger.error(f"Error handling stuck packages: {str(e)}", exc_info=True)

    def _process_pending_publishing(self) -> None:
        """Process packages that are approved and ready for publishing"""
        try:
            # Get packages that need publishing - approved packages with pending publish status
            pending_packages = (
                db.session.query(Package)
                .join(PackageStatus)
                .filter(
                    PackageStatus.status == "Approved",
                    PackageStatus.publish_status == "pending",
                )
                .limit(self.max_packages_per_cycle)
                .all()
            )

            if not pending_packages:
                return

            logger.info(f"Processing {len(pending_packages)} packages for publishing")

            for package in pending_packages:
                try:
                    self._publish_single_package(package)
                except Exception as e:
                    logger.error(
                        f"Error publishing package {package.name}@{package.version}: {str(e)}",
                        exc_info=True,
                    )
                    self._mark_package_publish_failed(package, str(e))

            db.session.commit()

        except Exception as e:
            logger.error(f"Error in _process_pending_publishing: {str(e)}", exc_info=True)
            db.session.rollback()

    def _publish_single_package(self, package: Package) -> None:
        """Publish a single package to the secure repository"""
        logger.info(f"Publishing package {package.name}@{package.version}")

        try:
            # Update publish status to publishing (keep main status as Approved)
            if package.package_status:
                package.package_status.publish_status = "publishing"
                package.package_status.updated_at = datetime.utcnow()
                db.session.commit()

            # Attempt to publish the package
            success = self.package_service.publish_to_secure_repo(package)

            if success:
                # Mark as published successfully (keep status as Approved, set published_at and publish_status)
                if package.package_status:
                    package.package_status.published_at = datetime.utcnow()
                    package.package_status.publish_status = "published"
                    package.package_status.updated_at = datetime.utcnow()
                logger.info(f"Successfully published package {package.name}@{package.version}")
            else:
                # Mark as publish failed
                self._mark_package_publish_failed(package, "Publishing failed")

        except Exception as e:
            logger.error(f"Error publishing package {package.name}@{package.version}: {str(e)}")
            self._mark_package_publish_failed(package, str(e))

    def _mark_package_publish_failed(self, package: Package, error_message: str) -> None:
        """Mark a package as publish failed with error message"""
        try:
            if package.package_status:
                package.package_status.publish_status = "failed"
                package.package_status.updated_at = datetime.utcnow()
            logger.error(f"Package {package.name}@{package.version} publish failed: {error_message}")
        except Exception as e:
            logger.error(f"Error marking package as publish failed: {str(e)}")

    def get_publishing_stats(self) -> Dict[str, Any]:
        """Get current publishing statistics"""
        try:
            with self.app.app_context():
                # Count packages by publish status
                publish_status_counts = {}
                for status in ["pending", "publishing", "published", "failed"]:
                    count = (
                        db.session.query(Package)
                        .join(PackageStatus)
                        .filter(PackageStatus.publish_status == status)
                        .count()
                    )
                    publish_status_counts[status] = count

                # Count approved packages (main status)
                approved_count = (
                    db.session.query(Package).join(PackageStatus).filter(PackageStatus.status == "Approved").count()
                )

                return {
                    "worker_status": self.get_worker_status(),
                    "approved_packages": approved_count,
                    "publish_status_counts": publish_status_counts,
                    "timestamp": datetime.utcnow().isoformat(),
                }
        except Exception as e:
            logger.error(f"Error getting publishing stats: {str(e)}")
            return {"error": str(e)}

    def retry_failed_publishing(self) -> Dict[str, Any]:
        """Retry failed publishing packages"""
        try:
            failed_packages = (
                db.session.query(Package).join(PackageStatus).filter(PackageStatus.publish_status == "failed").all()
            )

            if not failed_packages:
                return {"message": "No failed publishing packages found", "retried": 0}

            retried_count = 0
            for package in failed_packages:
                if package.package_status:
                    package.package_status.publish_status = "pending"
                    package.package_status.updated_at = datetime.utcnow()
                    retried_count += 1

            db.session.commit()

            logger.info(f"Retried {retried_count} failed publishing packages")
            return {
                "message": f"Retried {retried_count} packages",
                "retried": retried_count,
            }

        except Exception as e:
            logger.error(f"Error retrying failed publishing packages: {str(e)}")
            db.session.rollback()
            return {"error": str(e)}
