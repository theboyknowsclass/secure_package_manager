"""
License Check Worker

Handles background license validation for packages.
Processes packages that need license checking and validation.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from models import Package, PackageStatus, db
from services.license_service import LicenseService
from workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class LicenseWorker(BaseWorker):
    """Background worker for license validation"""

    def __init__(self, sleep_interval: int = 15):
        super().__init__("LicenseChecker", sleep_interval)
        self.license_service = None
        self.max_packages_per_cycle = 10  # Process max 10 packages per cycle (license checks are fast)
        self.stuck_package_timeout = timedelta(minutes=15)  # Consider packages stuck after 15 minutes

    def initialize(self) -> None:
        """Initialize services"""
        logger.info("Initializing LicenseWorker services...")
        self.license_service = LicenseService()
        logger.info("LicenseWorker services initialized")

    def process_cycle(self) -> None:
        """Process one cycle of license checking"""
        try:
            # Check for stuck packages first
            self._handle_stuck_packages()
            
            # Process packages that need license checking
            self._process_pending_license_checks()
            
        except Exception as e:
            logger.error(f"Error in license checking cycle: {str(e)}", exc_info=True)

    def _handle_stuck_packages(self) -> None:
        """Handle packages that have been stuck in license checking state too long"""
        try:
            stuck_threshold = datetime.utcnow() - self.stuck_package_timeout
            stuck_statuses = ["Checking Licence", "License Check Failed"]
            
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
                logger.warning(f"Found {len(stuck_packages)} stuck packages in license checking, resetting to Requested")
                
                for package in stuck_packages:
                    if package.package_status:
                        package.package_status.status = "Requested"
                        package.package_status.updated_at = datetime.utcnow()
                        logger.info(f"Reset stuck package {package.name}@{package.version} to Requested")
                
                db.session.commit()
                
        except Exception as e:
            logger.error(f"Error handling stuck packages: {str(e)}", exc_info=True)
            db.session.rollback()

    def _process_pending_license_checks(self) -> None:
        """Process packages that need license checking"""
        try:
            # Get packages that need license checking
            # Look for packages in "Requested" status that haven't been license checked yet
            pending_packages = (
                db.session.query(Package)
                .join(PackageStatus)
                .filter(PackageStatus.status == "Requested")
                .limit(self.max_packages_per_cycle)
                .all()
            )
            
            if not pending_packages:
                return
            
            logger.info(f"Processing {len(pending_packages)} packages for license checking")
            
            for package in pending_packages:
                try:
                    self._check_single_package_license(package)
                except Exception as e:
                    logger.error(f"Error checking license for package {package.name}@{package.version}: {str(e)}", exc_info=True)
                    self._mark_package_license_failed(package, str(e))
            
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Error in _process_pending_license_checks: {str(e)}", exc_info=True)
            db.session.rollback()

    def _check_single_package_license(self, package: Package) -> None:
        """Check license for a single package"""
        logger.info(f"Checking license for package {package.name}@{package.version}")
        
        try:
            # Update status to checking license
            if package.package_status:
                package.package_status.status = "Checking Licence"
                package.package_status.updated_at = datetime.utcnow()
                db.session.commit()
            
            # Perform license validation
            license_validation = self._validate_package_license(package)
            
            # Get the license status from the validation result
            license_status = license_validation.get("license_status")
            
            # Store the license score and status
            if package.package_status:
                package.package_status.license_score = license_validation["score"]
                package.package_status.license_status = license_status
                package.package_status.updated_at = datetime.utcnow()
                db.session.commit()
            
            # Check if license validation passed
            if license_validation["score"] == 0:
                # License validation failed
                self._mark_package_license_failed(package, f"License validation failed: {', '.join(license_validation.get('errors', []))}")
                return
            
            # License validation passed, mark as license checked
            if package.package_status:
                package.package_status.status = "Licence Checked"
                package.package_status.updated_at = datetime.utcnow()
            
            logger.info(f"Successfully checked license for package {package.name}@{package.version} (Score: {license_validation['score']}, Status: {license_status})")
            
        except Exception as e:
            logger.error(f"Error checking license for package {package.name}@{package.version}: {str(e)}")
            self._mark_package_license_failed(package, str(e))

    def _validate_package_license(self, package: Package) -> Dict[str, Any]:
        """Validate package license information"""
        try:
            # Get package data for license validation
            package_data = {
                "name": package.name,
                "version": package.version,
                "license": package.license_identifier,  # This should be populated from package-lock.json
            }
            
            # Use license service to validate
            validation_result: Dict[str, Any] = self.license_service.validate_package_license(package_data)
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating package license for {package.name}@{package.version}: {str(e)}")
            return {
                "score": 0,
                "errors": [f"License validation failed: {str(e)}"],
                "warnings": [],
            }

    def _mark_package_license_failed(self, package: Package, error_message: str) -> None:
        """Mark a package as license check failed with error message"""
        try:
            if package.package_status:
                package.package_status.status = "License Check Failed"
                package.package_status.updated_at = datetime.utcnow()
            logger.error(f"Package {package.name}@{package.version} license check failed: {error_message}")
        except Exception as e:
            logger.error(f"Error marking package as license check failed: {str(e)}")

    def get_license_checking_stats(self) -> Dict[str, Any]:
        """Get current license checking statistics"""
        try:
            with self.app.app_context():
                # Count packages by status
                status_counts = {}
                for status in ["Requested", "Checking Licence", "Licence Checked", "License Check Failed"]:
                    count = db.session.query(Package).join(PackageStatus).filter(PackageStatus.status == status).count()
                    status_counts[status] = count
                
                return {
                    "worker_status": self.get_worker_status(),
                    "package_status_counts": status_counts,
                    "timestamp": datetime.utcnow().isoformat(),
                }
        except Exception as e:
            logger.error(f"Error getting license checking stats: {str(e)}")
            return {"error": str(e)}

    def retry_failed_license_checks(self) -> Dict[str, Any]:
        """Retry failed license check packages"""
        try:
            failed_packages = (
                db.session.query(Package)
                .join(PackageStatus)
                .filter(PackageStatus.status == "License Check Failed")
                .all()
            )
            
            if not failed_packages:
                return {"message": "No failed license check packages found", "retried": 0}
            
            retried_count = 0
            for package in failed_packages:
                if package.package_status:
                    package.package_status.status = "Requested"
                    package.package_status.updated_at = datetime.utcnow()
                    retried_count += 1
            
            db.session.commit()
            
            logger.info(f"Retried {retried_count} failed license check packages")
            return {"message": f"Retried {retried_count} packages", "retried": retried_count}
            
        except Exception as e:
            logger.error(f"Error retrying failed license check packages: {str(e)}")
            db.session.rollback()
            return {"error": str(e)}

    def force_license_check(self, package_ids: List[int]) -> Dict[str, Any]:
        """Force license check for specific packages"""
        try:
            packages = (
                db.session.query(Package)
                .join(PackageStatus)
                .filter(Package.id.in_(package_ids))
                .all()
            )
            
            if not packages:
                return {"message": "No packages found", "processed": 0}
            
            processed_count = 0
            for package in packages:
                if package.package_status:
                    package.package_status.status = "Requested"
                    package.package_status.updated_at = datetime.utcnow()
                    processed_count += 1
            
            db.session.commit()
            
            logger.info(f"Force queued {processed_count} packages for license checking")
            return {"message": f"Queued {processed_count} packages for license checking", "processed": processed_count}
            
        except Exception as e:
            logger.error(f"Error force queuing packages for license checking: {str(e)}")
            db.session.rollback()
            return {"error": str(e)}
