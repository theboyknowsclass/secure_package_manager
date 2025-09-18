"""
Package Processing Worker

Handles background processing of packages through the validation pipeline.
Can resume processing from database state after service restarts.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from models import Package, PackageStatus, Request, RequestPackage, db
from services.download_service import DownloadService
from services.trivy_service import TrivyService
from workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class PackageWorker(BaseWorker):
    """Background worker for processing packages"""

    def __init__(self, sleep_interval: int = 10):
        super().__init__("PackageProcessor", sleep_interval)
        self.download_service = None
        self.trivy_service = None
        self.max_packages_per_cycle = 5  # Process max 5 packages per cycle
        self.stuck_package_timeout = timedelta(minutes=30)  # Consider packages stuck after 30 minutes

    def initialize(self) -> None:
        """Initialize services"""
        logger.info("Initializing PackageWorker services...")
        self.download_service = DownloadService()
        self.trivy_service = TrivyService()
        logger.info("PackageWorker services initialized")

    def process_cycle(self) -> None:
        """Process one cycle of package work"""
        try:
            # Check for stuck packages first
            self._handle_stuck_packages()

            # Process pending packages
            self._process_pending_packages()

        except Exception as e:
            logger.error(f"Error in package processing cycle: {str(e)}", exc_info=True)

    def _handle_stuck_packages(self) -> None:
        """Handle packages that have been stuck in processing state too long"""
        try:
            stuck_threshold = datetime.utcnow() - self.stuck_package_timeout
            stuck_statuses = ["Checking Licence", "Downloading", "Security Scanning"]

            stuck_packages = (
                db.session.query(Package)
                .join(PackageStatus)
                .filter(
                    PackageStatus.status.in_(stuck_statuses),
                    PackageStatus.updated_at < stuck_threshold,
                )
                .all()
            )

            if stuck_packages:
                logger.warning(f"Found {len(stuck_packages)} stuck packages, resetting to Requested status")

                for package in stuck_packages:
                    if package.package_status:
                        package.package_status.status = "Requested"
                        package.package_status.updated_at = datetime.utcnow()
                        logger.info(f"Reset stuck package {package.name}@{package.version} to Requested")

                db.session.commit()

        except Exception as e:
            logger.error(f"Error handling stuck packages: {str(e)}", exc_info=True)
            db.session.rollback()

    def _process_pending_packages(self) -> None:
        """Process packages that are in Licence Checked status (ready for next pipeline steps)"""
        try:
            # Get packages that need processing (after license checking is complete)
            pending_packages = (
                db.session.query(Package)
                .join(PackageStatus)
                .filter(PackageStatus.status == "Licence Checked")
                .limit(self.max_packages_per_cycle)
                .all()
            )

            if not pending_packages:
                return

            logger.info(f"Processing {len(pending_packages)} pending packages")

            for package in pending_packages:
                try:
                    self._process_single_package(package)
                except Exception as e:
                    logger.error(
                        f"Error processing package {package.name}@{package.version}: {str(e)}",
                        exc_info=True,
                    )
                    self._mark_package_failed(package, str(e))

            db.session.commit()

        except Exception as e:
            logger.error(f"Error in _process_pending_packages: {str(e)}", exc_info=True)
            db.session.rollback()

    def _process_single_package(self, package: Package) -> None:
        """Process a single package through the validation pipeline (after license checking)"""
        logger.info(f"Processing package {package.name}@{package.version} (license already checked)")

        # Step 1: Mark as downloaded (license check already done by LicenseWorker)
        if not self._mark_as_downloaded(package):
            self._mark_package_failed(package, "Failed to mark as downloaded")
            return

        # Step 2: Security scan
        if not self._perform_security_scan(package):
            self._mark_package_failed(package, "Security scan failed")
            return

        # Step 3: Mark as ready for approval
        if package.package_status:
            package.package_status.status = "Pending Approval"
            package.package_status.updated_at = datetime.utcnow()

        logger.info(f"Successfully processed package {package.name}@{package.version}")

    def _mark_as_downloaded(self, package: Package) -> bool:
        """Download package from npm registry and mark as downloaded"""
        try:
            if not package.package_status:
                return False

            # Check if package is already downloaded
            if self.download_service.is_package_downloaded(package):
                logger.info(f"Package {package.name}@{package.version} already downloaded, skipping download")
                package.package_status.status = "Downloaded"
                package.package_status.updated_at = datetime.utcnow()
                db.session.commit()
                return True

            # Update status to downloading
            package.package_status.status = "Downloading"
            package.package_status.updated_at = datetime.utcnow()
            db.session.commit()

            # Download package from npm registry
            if not self.download_service.download_package(package):
                logger.error(f"Failed to download package {package.name}@{package.version}")
                return False

            # Update status to downloaded
            package.package_status.status = "Downloaded"
            package.package_status.updated_at = datetime.utcnow()
            db.session.commit()

            logger.info(f"Successfully downloaded package {package.name}@{package.version}")
            return True

        except Exception as e:
            logger.error(f"Error downloading package {package.name}@{package.version}: {str(e)}")
            return False

    def _perform_security_scan(self, package: Package) -> bool:
        """Perform security scan for a package"""
        try:
            if not package.package_status:
                return False

            # Update status to security scanning
            package.package_status.status = "Security Scanning"
            package.package_status.security_scan_status = "running"
            package.package_status.updated_at = datetime.utcnow()
            db.session.commit()

            logger.info(f"Starting security scan for package {package.name}@{package.version}")
            scan_result = self.trivy_service.scan_package(package)

            if scan_result["status"] == "failed":
                logger.warning(
                    f"Security scan failed for {package.name}@{package.version}: {scan_result.get('error', 'Unknown error')}"
                )
                package.package_status.status = "Security Scanned"  # Still mark as scanned even if failed
                package.package_status.security_scan_status = "failed"
            else:
                logger.info(
                    f"Security scan completed for {package.name}@{package.version}: {scan_result.get('vulnerability_count', 0)} vulnerabilities found"
                )
                package.package_status.status = "Security Scanned"
                package.package_status.security_scan_status = "completed"
                package.package_status.security_score = scan_result.get("security_score", 100)

            package.package_status.updated_at = datetime.utcnow()
            db.session.commit()

            return True

        except Exception as e:
            logger.error(f"Security scan failed for {package.name}@{package.version}: {str(e)}")
            if package.package_status:
                package.package_status.status = "Security Scanned"  # Still mark as scanned even if failed
                package.package_status.security_scan_status = "failed"
                package.package_status.updated_at = datetime.utcnow()
            db.session.commit()
            return False

    def _mark_package_failed(self, package: Package, error_message: str) -> None:
        """Mark a package as failed with error message"""
        try:
            if package.package_status:
                package.package_status.status = "Rejected"
                package.package_status.updated_at = datetime.utcnow()
            logger.error(f"Package {package.name}@{package.version} failed: {error_message}")
        except Exception as e:
            logger.error(f"Error marking package as failed: {str(e)}")

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get current processing statistics"""
        try:
            with self.app.app_context():
                # Count packages by status
                status_counts = {}
                for status in [
                    "Requested",
                    "Checking Licence",
                    "Downloading",
                    "Security Scanning",
                    "Pending Approval",
                    "Rejected",
                ]:
                    count = db.session.query(Package).join(PackageStatus).filter(PackageStatus.status == status).count()
                    status_counts[status] = count

                # Count total requests
                total_requests = db.session.query(Request).count()

                return {
                    "worker_status": self.get_worker_status(),
                    "package_status_counts": status_counts,
                    "total_requests": total_requests,
                    "timestamp": datetime.utcnow().isoformat(),
                }
        except Exception as e:
            logger.error(f"Error getting processing stats: {str(e)}")
            return {"error": str(e)}

    def retry_failed_packages(self, request_id: Optional[int] = None) -> Dict[str, Any]:
        """Retry failed packages, optionally for a specific request"""
        try:
            query = db.session.query(Package).join(PackageStatus).filter(PackageStatus.status == "Rejected")

            if request_id:
                query = query.join(RequestPackage).filter(RequestPackage.request_id == request_id)

            failed_packages = query.all()

            if not failed_packages:
                return {"message": "No failed packages found", "retried": 0}

            retried_count = 0
            for package in failed_packages:
                if package.package_status:
                    package.package_status.status = "Requested"
                    package.package_status.updated_at = datetime.utcnow()
                    retried_count += 1

            db.session.commit()

            logger.info(f"Retried {retried_count} failed packages")
            return {
                "message": f"Retried {retried_count} packages",
                "retried": retried_count,
            }

        except Exception as e:
            logger.error(f"Error retrying failed packages: {str(e)}")
            db.session.rollback()
            return {"error": str(e)}
