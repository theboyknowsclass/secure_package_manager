"""License Check Worker.

Handles background license validation for packages. This worker delegates
all business logic to LicenseService.
"""

import logging
from typing import List

from services.license_service import LicenseService
from workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class LicenseWorker(BaseWorker):
    """Background worker for license validation.

    This worker coordinates the license validation process by:
    1. Delegating license validation logic to LicenseService
    2. Handling results and logging progress
    """

    WORKER_TYPE = "license_checker"

    def __init__(self, sleep_interval: int = 15):
        super().__init__("LicenseChecker", sleep_interval)
        self.license_service: LicenseService
        self.max_license_groups_per_cycle = 20  # Process max 20 unique license groups per cycle

    def initialize(self) -> None:
        """Initialize services."""
        logger.info("Initializing LicenseWorker services...")
        self.license_service = LicenseService()
        logger.info("LicenseWorker services initialized")

    def process_cycle(self) -> None:
        """Process one cycle of license checking."""
        try:
            # Process packages using the service (service manages its own database sessions)
            result = self.license_service.process_license_groups(self.max_license_groups_per_cycle)

            if result["success"]:
                if result["processed_count"] > 0:
                    logger.info(
                        f"License processing complete: {result['successful_packages']} successful, "
                        f"{result['failed_packages']} failed across {result['license_groups_processed']} license groups"
                    )
                else:
                    logger.info("LicenseWorker heartbeat: No packages found needing license checking")
            else:
                logger.error(f"Error in license processing: {result['error']}")

        except Exception as e:
            logger.error(
                f"Error in LicenseWorker process_cycle: {str(e)}",
                exc_info=True,
            )

    def get_required_env_vars(self) -> List[str]:
        """Get list of required environment variables."""
        return ["DATABASE_URL"]
