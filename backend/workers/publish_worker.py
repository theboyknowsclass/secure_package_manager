"""
Package Publishing Worker

Handles background publishing of approved packages to the secure repository.
Processes packages that are approved but not yet published.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from models import Package, PackageStatus, db
from services.package_service import PackageService
from workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class PublishWorker(BaseWorker):
    """Background worker for publishing approved packages"""

    def __init__(self, sleep_interval: int = 30):
        super().__init__("PackagePublisher", sleep_interval)
        self.package_service = None
        self.max_packages_per_cycle = 3  # Process max 3 packages per cycle (publishing is slow)
        self.stuck_package_timeout = timedelta(hours=2)  # Consider packages stuck after 2 hours

    def initialize(self) -> None:
        """Initialize services"""
        logger.info("Initializing PublishWorker services...")
        self.package_service = PackageService()
        logger.info("PublishWorker services initialized")

    def process_cycle(self) -> None:
        """Process one cycle of package publishing"""
        try:
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
            stuck_statuses = ["Publishing", "Publish Failed"]
            
            stuck_packages = (
                db.session.query(Package)
                .join(PackageStatus)
                .filter(
                    PackageStatus.status.in_(stuck_statuses),
                    PackageStatus.updated_at < stuck_threshold
                )
                .all()
            )
            
            if stuck_packages:
                logger.warning(f"Found {len(stuck_packages)} stuck packages in publishing, resetting to Approved")
                
                for package in stuck_packages:
                    if package.package_status:
                        package.package_status.status = "Approved"
                        package.package_status.updated_at = datetime.utcnow()
                        logger.info(f"Reset stuck package {package.name}@{package.version} to Approved")
                
                db.session.commit()
                
        except Exception as e:
            logger.error(f"Error handling stuck packages: {str(e)}", exc_info=True)
            db.session.rollback()

    def _process_pending_publishing(self) -> None:
        """Process packages that are approved and ready for publishing"""
        try:
            # Get packages that need publishing
            # For now, we'll look for packages that are "Approved" and don't have a publishing status
            # In the future, we could add a separate "publishing_status" field
            pending_packages = (
                db.session.query(Package)
                .join(PackageStatus)
                .filter(PackageStatus.status == "Approved")
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
                    logger.error(f"Error publishing package {package.name}@{package.version}: {str(e)}", exc_info=True)
                    self._mark_package_publish_failed(package, str(e))
            
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Error in _process_pending_publishing: {str(e)}", exc_info=True)
            db.session.rollback()

    def _publish_single_package(self, package: Package) -> None:
        """Publish a single package to the secure repository"""
        logger.info(f"Publishing package {package.name}@{package.version}")
        
        try:
            # Update status to publishing
            if package.package_status:
                package.package_status.status = "Publishing"
                package.package_status.updated_at = datetime.utcnow()
                db.session.commit()
            
            # Attempt to publish the package
            success = self.package_service.publish_to_secure_repo(package)
            
            if success:
                # Mark as published successfully
                if package.package_status:
                    package.package_status.status = "Published"
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
                package.package_status.status = "Publish Failed"
                package.package_status.updated_at = datetime.utcnow()
            logger.error(f"Package {package.name}@{package.version} publish failed: {error_message}")
        except Exception as e:
            logger.error(f"Error marking package as publish failed: {str(e)}")

    def get_publishing_stats(self) -> Dict[str, Any]:
        """Get current publishing statistics"""
        try:
            with self.app.app_context():
                # Count packages by status
                status_counts = {}
                for status in ["Approved", "Publishing", "Published", "Publish Failed"]:
                    count = db.session.query(Package).join(PackageStatus).filter(PackageStatus.status == status).count()
                    status_counts[status] = count
                
                return {
                    "worker_status": self.get_worker_status(),
                    "package_status_counts": status_counts,
                    "timestamp": datetime.utcnow().isoformat(),
                }
        except Exception as e:
            logger.error(f"Error getting publishing stats: {str(e)}")
            return {"error": str(e)}

    def retry_failed_publishing(self) -> Dict[str, Any]:
        """Retry failed publishing packages"""
        try:
            failed_packages = (
                db.session.query(Package)
                .join(PackageStatus)
                .filter(PackageStatus.status == "Publish Failed")
                .all()
            )
            
            if not failed_packages:
                return {"message": "No failed publishing packages found", "retried": 0}
            
            retried_count = 0
            for package in failed_packages:
                if package.package_status:
                    package.package_status.status = "Approved"
                    package.package_status.updated_at = datetime.utcnow()
                    retried_count += 1
            
            db.session.commit()
            
            logger.info(f"Retried {retried_count} failed publishing packages")
            return {"message": f"Retried {retried_count} packages", "retried": retried_count}
            
        except Exception as e:
            logger.error(f"Error retrying failed publishing packages: {str(e)}")
            db.session.rollback()
            return {"error": str(e)}
