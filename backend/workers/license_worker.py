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
        self.max_license_groups_per_cycle = 20  # Process max 20 unique license groups per cycle
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
        """Process packages that need license checking using license-based grouping"""
        try:
            # Get packages grouped by license string for efficient batch processing
            license_groups = self._get_packages_grouped_by_license()
            
            if not license_groups:
                return
            
            total_packages = sum(len(packages) for packages in license_groups.values())
            logger.info(f"Processing {total_packages} packages across {len(license_groups)} unique license groups")
            
            # Process each license group as a batch
            self._check_license_groups_batch(license_groups)
            
        except Exception as e:
            logger.error(f"Error in _process_pending_license_checks: {str(e)}", exc_info=True)
            db.session.rollback()

    def _get_packages_grouped_by_license(self) -> Dict[str, List[Package]]:
        """Get packages grouped by their license string for efficient batch processing"""
        try:
            # Get all packages that need license checking
            pending_packages = (
                db.session.query(Package)
                .join(PackageStatus)
                .filter(PackageStatus.status == "Requested")
                .all()
            )
            
            if not pending_packages:
                return {}
            
            # Group packages by license string
            license_groups = {}
            for package in pending_packages:
                # Use license_identifier or "NO_LICENSE" for packages without license info
                license_key = package.license_identifier or "NO_LICENSE"
                
                if license_key not in license_groups:
                    license_groups[license_key] = []
                license_groups[license_key].append(package)
            
            # Limit the number of license groups processed per cycle
            # Take the groups with the most packages first for maximum efficiency
            sorted_groups = sorted(license_groups.items(), key=lambda x: len(x[1]), reverse=True)
            limited_groups = dict(sorted_groups[:self.max_license_groups_per_cycle])
            
            logger.debug(f"Grouped {len(pending_packages)} packages into {len(license_groups)} license groups, processing {len(limited_groups)} groups")
            
            return limited_groups
            
        except Exception as e:
            logger.error(f"Error grouping packages by license: {str(e)}")
            return {}

    def _check_license_groups_batch(self, license_groups: Dict[str, List[Package]]) -> None:
        """Check licenses for multiple license groups in batch for improved performance"""
        try:
            # Prepare unique license data for batch validation
            unique_licenses = []
            license_to_packages = {}  # Map license string to list of packages
            
            for license_string, packages in license_groups.items():
                # Create a representative package data for this license group
                if license_string == "NO_LICENSE":
                    package_data = {
                        "name": "LICENSE_GROUP",
                        "version": "1.0.0", 
                        "license": None,
                    }
                else:
                    package_data = {
                        "name": "LICENSE_GROUP",
                        "version": "1.0.0",
                        "license": license_string,
                    }
                
                unique_licenses.append(package_data)
                license_to_packages[license_string] = packages
            
            # Update all packages to "Checking Licence" status in batch
            all_packages = [pkg for packages in license_groups.values() for pkg in packages]
            self._update_packages_status_batch(all_packages, "Checking Licence")
            
            # Perform batch license validation for unique licenses
            validation_results = self.license_service.validate_packages_batch(unique_licenses)
            
            # Process results and update package statuses in batch
            self._process_license_group_results(license_groups, unique_licenses, validation_results)
            
            # Commit all changes at once
            db.session.commit()
            
            total_packages = sum(len(packages) for packages in license_groups.values())
            logger.info(f"Successfully processed {total_packages} packages across {len(license_groups)} license groups")
            
        except Exception as e:
            logger.error(f"Error in batch license group checking: {str(e)}", exc_info=True)
            db.session.rollback()
            # Fallback to individual processing
            self._fallback_to_individual_processing([pkg for packages in license_groups.values() for pkg in packages])

    def _process_license_group_results(
        self, 
        license_groups: Dict[str, List[Package]], 
        unique_licenses: List[Dict[str, Any]], 
        validation_results: List[Dict[str, Any]]
    ) -> None:
        """Process batch validation results for license groups and update package statuses"""
        try:
            successful_packages = []
            failed_packages = []
            
            for i, (license_string, packages) in enumerate(license_groups.items()):
                if i >= len(validation_results):
                    logger.error(f"No validation result for license group {i}: {license_string}")
                    continue
                    
                result = validation_results[i]
                
                try:
                    # Apply the same result to all packages in this license group
                    for package in packages:
                        if package.package_status:
                            package.package_status.license_score = result["score"]
                            package.package_status.license_status = result.get("license_status")
                            package.package_status.updated_at = datetime.utcnow()
                        
                        # Determine final status based on validation result
                        if result["score"] == 0:
                            # License validation failed
                            failed_packages.append((package, f"License validation failed: {', '.join(result.get('errors', []))}"))
                        else:
                            # License validation passed
                            successful_packages.append(package)
                            if package.package_status:
                                package.package_status.status = "Licence Checked"
                        
                        logger.debug(f"Package {package.name}@{package.version} (license: {license_string}): Score={result['score']}, Status={result.get('license_status')}")
                    
                except Exception as e:
                    logger.error(f"Error processing result for license group {license_string}: {str(e)}")
                    for package in packages:
                        failed_packages.append((package, str(e)))
            
            # Update failed packages status in batch
            if failed_packages:
                failed_package_ids = [pkg.id for pkg, _ in failed_packages]
                db.session.query(PackageStatus).filter(
                    PackageStatus.package_id.in_(failed_package_ids)
                ).update({
                    PackageStatus.status: "License Check Failed",
                    PackageStatus.updated_at: datetime.utcnow()
                }, synchronize_session=False)
                
                for package, error_msg in failed_packages:
                    logger.error(f"Package {package.name}@{package.version} license check failed: {error_msg}")
            
            logger.info(f"License group processing complete: {len(successful_packages)} successful, {len(failed_packages)} failed")
            
        except Exception as e:
            logger.error(f"Error processing license group validation results: {str(e)}")
            raise

    def _check_packages_batch(self, packages: List[Package]) -> None:
        """Check licenses for multiple packages in batch for improved performance"""
        try:
            # Prepare package data for batch validation
            packages_data = []
            package_mapping = {}  # Map package data to Package objects
            
            for package in packages:
                package_data = {
                    "name": package.name,
                    "version": package.version,
                    "license": package.license_identifier,
                }
                packages_data.append(package_data)
                package_mapping[id(package_data)] = package
            
            # Update all packages to "Checking Licence" status in batch
            self._update_packages_status_batch(packages, "Checking Licence")
            
            # Perform batch license validation
            validation_results = self.license_service.validate_packages_batch(packages_data)
            
            # Process results and update package statuses in batch
            self._process_batch_validation_results(packages, packages_data, validation_results)
            
            # Commit all changes at once
            db.session.commit()
            
            logger.info(f"Successfully processed {len(packages)} packages in batch")
            
        except Exception as e:
            logger.error(f"Error in batch license checking: {str(e)}", exc_info=True)
            db.session.rollback()
            # Fallback to individual processing
            self._fallback_to_individual_processing(packages)

    def _update_packages_status_batch(self, packages: List[Package], status: str) -> None:
        """Update status for multiple packages in a single database operation"""
        try:
            package_ids = [pkg.id for pkg in packages]
            
            # Bulk update package statuses
            db.session.query(PackageStatus).filter(
                PackageStatus.package_id.in_(package_ids)
            ).update({
                PackageStatus.status: status,
                PackageStatus.updated_at: datetime.utcnow()
            }, synchronize_session=False)
            
            logger.debug(f"Updated {len(packages)} packages to status: {status}")
            
        except Exception as e:
            logger.error(f"Error updating package statuses in batch: {str(e)}")
            raise

    def _process_batch_validation_results(
        self, 
        packages: List[Package], 
        packages_data: List[Dict[str, Any]], 
        validation_results: List[Dict[str, Any]]
    ) -> None:
        """Process batch validation results and update package statuses"""
        try:
            successful_packages = []
            failed_packages = []
            
            for i, (package, package_data, result) in enumerate(zip(packages, packages_data, validation_results)):
                try:
                    # Update license score and status
                    if package.package_status:
                        package.package_status.license_score = result["score"]
                        package.package_status.license_status = result.get("license_status")
                        package.package_status.updated_at = datetime.utcnow()
                    
                    # Determine final status based on validation result
                    if result["score"] == 0:
                        # License validation failed
                        failed_packages.append((package, f"License validation failed: {', '.join(result.get('errors', []))}"))
                    else:
                        # License validation passed
                        successful_packages.append(package)
                        if package.package_status:
                            package.package_status.status = "Licence Checked"
                    
                    logger.debug(f"Package {package.name}@{package.version}: Score={result['score']}, Status={result.get('license_status')}")
                    
                except Exception as e:
                    logger.error(f"Error processing result for package {package.name}@{package.version}: {str(e)}")
                    failed_packages.append((package, str(e)))
            
            # Update failed packages status in batch
            if failed_packages:
                failed_package_ids = [pkg.id for pkg, _ in failed_packages]
                db.session.query(PackageStatus).filter(
                    PackageStatus.package_id.in_(failed_package_ids)
                ).update({
                    PackageStatus.status: "License Check Failed",
                    PackageStatus.updated_at: datetime.utcnow()
                }, synchronize_session=False)
                
                for package, error_msg in failed_packages:
                    logger.error(f"Package {package.name}@{package.version} license check failed: {error_msg}")
            
            logger.info(f"Batch processing complete: {len(successful_packages)} successful, {len(failed_packages)} failed")
            
        except Exception as e:
            logger.error(f"Error processing batch validation results: {str(e)}")
            raise

    def _fallback_to_individual_processing(self, packages: List[Package]) -> None:
        """Fallback to individual package processing if batch processing fails"""
        logger.warning("Falling back to individual package processing")
        
        for package in packages:
            try:
                self._check_single_package_license(package)
            except Exception as e:
                logger.error(f"Error in fallback processing for package {package.name}@{package.version}: {str(e)}")
                self._mark_package_license_failed(package, str(e))
        
        try:
            db.session.commit()
        except Exception as e:
            logger.error(f"Error committing fallback processing: {str(e)}")
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
