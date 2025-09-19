"""Download Worker.

Transitions packages from Licence Checked to Downloaded (via
Downloading) using entity-based operations and delegates business logic to services while maintaining logging and coordination.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List

from database.operations.composite_operations import CompositeOperations
from database.service import DatabaseService
from services.download_processing_service import DownloadProcessingService
from workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class DownloadWorker(BaseWorker):
    """Background worker for downloading packages.

    This worker coordinates the download process by:
    1. Finding packages that need downloading
    2. Handling stuck packages
    3. Delegating download logic to DownloadProcessingService
    4. Handling results and logging progress
    """

    WORKER_TYPE = "download_worker"

    # Extend base environment variables with download-specific ones
    required_env_vars = BaseWorker.required_env_vars + [
        "SOURCE_REPOSITORY_URL"
    ]

    def __init__(self, sleep_interval: int = 10):
        super().__init__("DownloadWorker", sleep_interval)
        self.download_service = None
        self.db_service = None
        self.max_packages_per_cycle = 10
        self.stuck_package_timeout = timedelta(minutes=30)

    def initialize(self) -> None:
        """Initialize services."""
        logger.info("Initializing DownloadWorker services...")
        self.download_service = DownloadProcessingService()

        # Initialize database service
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is required")

        self.db_service = DatabaseService(database_url)
        logger.info("DownloadWorker services initialized")

    def process_cycle(self) -> None:
        """Process one cycle of downloading."""
        try:
            with CompositeOperations.get_operations() as ops:
                # Handle stuck packages first
                self._handle_stuck_packages(ops)

                # Find packages that need downloading
                ready_packages = ops.package.get_by_status("Licence Checked")
                
                # Limit the number of packages processed per cycle
                limited_packages = ready_packages[:self.max_packages_per_cycle]

                if not limited_packages:
                    logger.info(
                        "DownloadWorker heartbeat: No packages found for downloading"
                    )
                    return

                logger.info(f"Downloading {len(limited_packages)} packages")

                # Process packages using the service
                result = self.download_service.process_package_batch(
                    limited_packages, ops
                )

                if result["success"]:
                    logger.info(
                        f"Download complete: {result['successful_downloads']} successful, "
                        f"{result['failed_downloads']} failed"
                    )
                else:
                    logger.error(
                        f"Error in download batch: {result['error']}"
                    )

        except Exception as e:
            logger.error(f"Download cycle error: {str(e)}", exc_info=True)

    def _handle_stuck_packages(self, ops: Dict[str, Any]) -> None:
        """Handle packages that have been stuck in Downloading state too long."""
        try:
            stuck_threshold = datetime.utcnow() - self.stuck_package_timeout
            stuck_packages = self.download_service.get_stuck_packages(
                stuck_threshold, ops
            )

            if stuck_packages:
                logger.warning(
                    f"Found {len(stuck_packages)} stuck downloads; resetting to Licence Checked"
                )
                self.download_service.reset_stuck_packages(stuck_packages, ops)

        except Exception as e:
            logger.error(
                f"Error handling stuck packages: {str(e)}", exc_info=True
            )

    def get_required_env_vars(self) -> List[str]:
        """Get list of required environment variables."""
        return ["DATABASE_URL", "SOURCE_REPOSITORY_URL"]