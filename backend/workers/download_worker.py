"""Download Worker.

Transitions packages from Licence Checked to Downloaded.
This worker delegates all business logic to DownloadService.
"""

import logging
from typing import List

from services.download_service import DownloadService
from workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class DownloadWorker(BaseWorker):
    """Background worker for downloading packages.

    This worker coordinates the download process by:
    1. Delegating download logic to DownloadService
    2. Handling results and logging progress
    """

    WORKER_TYPE = "download_worker"

    # Extend base environment variables with download-specific ones
    required_env_vars = BaseWorker.required_env_vars + [
        "SOURCE_REPOSITORY_URL"
    ]

    def __init__(self, sleep_interval: int = 10):
        super().__init__("DownloadWorker", sleep_interval)
        self.download_service = None
        self.max_packages_per_cycle = 10

    def initialize(self) -> None:
        """Initialize services."""
        logger.info("Initializing DownloadWorker services...")
        self.download_service = DownloadService()
        logger.info("DownloadWorker services initialized")

    def process_cycle(self) -> None:
        """Process one cycle of downloading."""
        try:
            # Process packages using the service (service manages its own database sessions)
            result = self.download_service.process_package_batch(
                self.max_packages_per_cycle
            )

            if not result["success"]:
                logger.error(f"Error in download batch: {result['error']}")

        except Exception as e:
            logger.error(f"Download cycle error: {str(e)}", exc_info=True)

    def get_required_env_vars(self) -> List[str]:
        """Get list of required environment variables."""
        return ["DATABASE_URL", "SOURCE_REPOSITORY_URL"]
