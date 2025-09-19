"""Package Publishing Worker.

Handles background publishing of approved packages to the secure
repository. Processes packages that are approved but not yet published using
entity-based operations and delegates business logic to services while maintaining logging and coordination.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List

from database.operations import OperationsFactory
from database.service import DatabaseService
from services.publishing_service import PublishingService
from workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class PublishWorker(BaseWorker):
    """Background worker for publishing approved packages.

    This worker coordinates the package publishing process by:
    1. Finding packages that need publishing
    2. Handling stuck packages
    3. Delegating publishing logic to PublishingService
    4. Handling results and logging progress
    """

    WORKER_TYPE = "package_publisher"

    # Extend base environment variables with publish-specific ones
    required_env_vars = BaseWorker.required_env_vars + [
        "TARGET_REPOSITORY_URL"
    ]

    def __init__(self, sleep_interval: int = 30):
        super().__init__("PackagePublisher", sleep_interval)
        self.publishing_service = None
        self.db_service = None
        self.max_packages_per_cycle = (
            3  # Process max 3 packages per cycle (publishing is slow)
        )
        self.stuck_package_timeout = timedelta(
            hours=2
        )  # Consider packages stuck after 2 hours

    def initialize(self) -> None:
        """Initialize services."""
        logger.info("Initializing PublishWorker services...")
        self.publishing_service = PublishingService()

        # Initialize database service
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is required")

        self.db_service = DatabaseService(database_url)
        logger.info("PublishWorker services initialized")

    def process_cycle(self) -> None:
        """Process one cycle of package publishing."""
        try:
            with self.db_service.get_session() as session:
                ops = OperationsFactory.create_all_operations(session)

                # Handle stuck packages first
                self._handle_stuck_packages(ops)

                # Find packages that need publishing
                pending_packages = ops["package"].get_packages_needing_publishing(
                    self.max_packages_per_cycle
                )

                if not pending_packages:
                    logger.info(
                        "PublishWorker heartbeat: No packages found for publishing"
                    )
                    return

                logger.info(
                    f"Processing {len(pending_packages)} packages for publishing"
                )

                # Process packages using the service
                successful_packages, failed_packages = (
                    self.publishing_service.process_package_batch(
                        pending_packages, ops
                    )
                )

                # Log results
                total_packages = len(successful_packages) + len(failed_packages)
                logger.info(
                    f"Publishing complete: {len(successful_packages)} successful, "
                    f"{len(failed_packages)} failed"
                )

                # Handle failed packages
                if failed_packages:
                    self._handle_failed_packages(failed_packages)

                # Commit the session
                session.commit()
                logger.info(
                    f"Successfully processed {total_packages} packages for publishing"
                )

        except Exception as e:
            logger.error(
                f"Error in PublishWorker process_cycle: {str(e)}",
                exc_info=True,
            )

    def _handle_stuck_packages(self, ops: Dict[str, Any]) -> None:
        """Handle packages that have been stuck in publishing state too long."""
        try:
            stuck_threshold = datetime.utcnow() - self.stuck_package_timeout
            stuck_packages = self.publishing_service.get_stuck_packages(
                stuck_threshold, ops
            )

            if stuck_packages:
                logger.warning(
                    f"Found {len(stuck_packages)} stuck packages in publishing, resetting publish status"
                )
                self.publishing_service.reset_stuck_packages(stuck_packages, ops)

        except Exception as e:
            logger.error(
                f"Error handling stuck packages: {str(e)}", exc_info=True
            )

    def _handle_failed_packages(self, failed_packages: List[Dict[str, Any]]) -> None:
        """Handle packages that failed publishing."""
        for failed_item in failed_packages:
            package = failed_item["package"]
            error = failed_item["error"]

            logger.warning(
                f"Package {package.name}@{package.version} failed publishing: {error}"
            )

    def get_publishing_stats(self) -> Dict[str, Any]:
        """Get current publishing statistics."""
        try:
            with self.db_service.get_session() as session:
                ops = OperationsFactory.create_all_operations(session)
                stats = self.publishing_service.get_publishing_statistics(ops)
                stats["worker_status"] = self.get_worker_status()
                return stats
        except Exception as e:
            logger.error(f"Error getting publishing stats: {str(e)}")
            return {"error": str(e)}

    def retry_failed_publishing(self) -> Dict[str, Any]:
        """Retry failed publishing packages."""
        try:
            with self.db_service.get_session() as session:
                ops = OperationsFactory.create_all_operations(session)
                result = self.publishing_service.retry_failed_packages(ops)
                
                if "retried" in result and result["retried"] > 0:
                    logger.info(
                        f"Retried {result['retried']} failed publishing packages"
                    )
                
                return result
        except Exception as e:
            logger.error(
                f"Error retrying failed publishing packages: {str(e)}"
            )
            return {"error": str(e)}

    def get_required_env_vars(self) -> List[str]:
        """Get list of required environment variables."""
        return ["DATABASE_URL", "TARGET_REPOSITORY_URL"]