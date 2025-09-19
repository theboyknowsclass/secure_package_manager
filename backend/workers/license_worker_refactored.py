"""License Check Worker - Refactored.

Handles background license validation for packages. Processes packages
that need license checking and validation.

This refactored version uses entity-based operations and delegates
business logic to services while maintaining logging and coordination.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List

from database.operations import OperationsFactory
from database.service import DatabaseService
from services.license_service_refactored import LicenseService
from workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class LicenseWorker(BaseWorker):
    """Background worker for license validation.

    This worker coordinates the license validation process by:
    1. Finding packages that need license checking
    2. Grouping packages by license for efficient processing
    3. Delegating license validation logic to LicenseService
    4. Handling results and logging progress
    """

    WORKER_TYPE = "license_checker"

    def __init__(self, sleep_interval: int = 15):
        super().__init__("LicenseChecker", sleep_interval)
        self.license_service = None
        self.db_service = None
        self.max_license_groups_per_cycle = (
            20  # Process max 20 unique license groups per cycle
        )
        self.stuck_package_timeout = timedelta(
            minutes=15
        )  # Consider packages stuck after 15 minutes

    def initialize(self) -> None:
        """Initialize services."""
        logger.info("Initializing LicenseWorker services...")
        self.license_service = LicenseService()

        # Initialize database service
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is required")

        self.db_service = DatabaseService(database_url)
        logger.info("LicenseWorker services initialized")

    def process_cycle(self) -> None:
        """Process one cycle of license checking."""
        try:
            with self.db_service.get_session() as session:
                ops = OperationsFactory.create_all_operations(session)

                # Handle stuck packages first
                self._handle_stuck_packages(ops)

                # Find packages that need license checking
                pending_packages = ops[
                    "package"
                ].get_packages_needing_license_check()

                if not pending_packages:
                    logger.info(
                        "LicenseWorker heartbeat: No packages found needing license checking"
                    )
                    return

                # Group packages by license for efficient processing
                license_groups = self._group_packages_by_license(
                    pending_packages
                )

                logger.info(
                    f"Grouped {len(pending_packages)} packages into {len(license_groups)} license groups, "
                    f"processing {min(len(license_groups), self.max_license_groups_per_cycle)} groups this cycle"
                )

                # Process license groups
                successful_packages = []
                failed_packages = []

                for i, (license_string, packages) in enumerate(
                    license_groups.items()
                ):
                    if i >= self.max_license_groups_per_cycle:
                        break

                    try:
                        group_successful, group_failed = (
                            self.license_service.process_license_group(
                                license_string, packages, ops
                            )
                        )
                        successful_packages.extend(group_successful)
                        failed_packages.extend(group_failed)

                    except Exception as e:
                        logger.error(
                            f"Error processing license group {license_string}: {str(e)}"
                        )
                        # Mark all packages in this group as failed
                        for package in packages:
                            failed_packages.append(
                                {
                                    "package": package,
                                    "error": f"License group processing failed: {str(e)}",
                                }
                            )

                # Handle fallback processing for any remaining packages
                if len(license_groups) > self.max_license_groups_per_cycle:
                    remaining_packages = []
                    for i, (license_string, packages) in enumerate(
                        license_groups.items()
                    ):
                        if i >= self.max_license_groups_per_cycle:
                            remaining_packages.extend(packages)

                    if remaining_packages:
                        logger.info(
                            f"Processing {len(remaining_packages)} remaining packages individually"
                        )
                        fallback_successful, fallback_failed = (
                            self.license_service.process_package_batch(
                                remaining_packages, ops
                            )
                        )
                        successful_packages.extend(fallback_successful)
                        failed_packages.extend(fallback_failed)

                # Log results
                total_packages = len(successful_packages) + len(
                    failed_packages
                )
                logger.info(
                    f"License group processing complete: {len(successful_packages)} successful, "
                    f"{len(failed_packages)} failed"
                )

                # Handle failed packages
                if failed_packages:
                    self._handle_failed_packages(failed_packages, ops)

                # Commit the session
                session.commit()
                logger.info(
                    f"Successfully processed {total_packages} packages across {min(len(license_groups), self.max_license_groups_per_cycle)} license groups"
                )

        except Exception as e:
            logger.error(
                f"Error in LicenseWorker process_cycle: {str(e)}",
                exc_info=True,
            )

    def _handle_stuck_packages(self, ops: Dict[str, Any]) -> None:
        """Handle packages that have been stuck in license checking for too
        long."""
        try:
            stuck_threshold = datetime.utcnow() - self.stuck_package_timeout
            stuck_packages = ops[
                "package"
            ].get_stuck_packages_in_license_checking(stuck_threshold)

            if stuck_packages:
                logger.warning(
                    f"Found {len(stuck_packages)} stuck packages in license checking, resetting to Submitted"
                )

                for package in stuck_packages:
                    if package.package_status:
                        ops["package_status"].update_package_status(
                            package.id,
                            "Submitted",
                            ops["package_status"].PackageStatus,
                        )

        except Exception as e:
            logger.error(
                f"Error handling stuck packages: {str(e)}", exc_info=True
            )

    def _group_packages_by_license(
        self, packages: List[Any]
    ) -> Dict[str, List[Any]]:
        """Group packages by their license string for efficient processing."""
        license_groups = {}

        for package in packages:
            license_string = package.license or "No License"
            if license_string not in license_groups:
                license_groups[license_string] = []
            license_groups[license_string].append(package)

        return license_groups

    def _handle_failed_packages(
        self, failed_packages: List[Dict[str, Any]], ops: Dict[str, Any]
    ) -> None:
        """Handle packages that failed license validation."""
        for failed_item in failed_packages:
            package = failed_item["package"]
            error = failed_item["error"]

            try:
                # Update package status to indicate failure
                ops["package_status"].update_package_status(
                    package.id,
                    "Licence Check Failed",
                    ops["package_status"].PackageStatus,
                )

                # Log the failure
                logger.warning(
                    f"Package {package.name}@{package.version} failed license validation: {error}"
                )

            except Exception as e:
                logger.error(
                    f"Error handling failed package {package.name}@{package.version}: {str(e)}"
                )

    def get_required_env_vars(self) -> List[str]:
        """Get list of required environment variables."""
        return ["DATABASE_URL"]
