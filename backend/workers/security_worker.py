"""Security Scan Worker.

Transitions packages from Downloaded to Security Scanned (via Security Scanning).
This worker delegates all business logic to SecurityService.
"""

import logging
from typing import List

from services.security_service import SecurityService
from workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class SecurityWorker(BaseWorker):
    """Background worker for security scanning packages.

    This worker coordinates the security scanning process by:
    1. Delegating security scanning logic to SecurityService
    2. Handling results and logging progress
    """

    WORKER_TYPE = "security_worker"

    # Extend base environment variables with Trivy-specific ones
    required_env_vars = BaseWorker.required_env_vars + [
        "TRIVY_URL",
        "TRIVY_TIMEOUT",
        "TRIVY_MAX_RETRIES",
    ]

    def __init__(self, sleep_interval: int = 15):
        super().__init__("SecurityWorker", sleep_interval)
        self.security_service: SecurityService
        self.max_packages_per_cycle = 10

    def initialize(self) -> None:
        """Initialize services."""
        logger.info("Initializing SecurityWorker services...")
        self.security_service = SecurityService()
        logger.info("SecurityWorker services initialized")

    def process_cycle(self) -> None:
        """Process one cycle of security scanning."""
        try:
            # Process packages using the service (service manages its own database sessions)
            result = self.security_service.process_package_batch(self.max_packages_per_cycle)

            if result["success"]:
                if result["processed_count"] > 0:
                    logger.info(
                        f"Security scanning complete: {result['successful_scans']} successful, "
                        f"{result['failed_scans']} failed"
                    )
                else:
                    logger.info("SecurityWorker heartbeat: No packages found for security scanning")
            else:
                logger.error(f"Error in security scanning batch: {result['error']}")

        except Exception as e:
            logger.error(f"Security cycle error: {str(e)}", exc_info=True)

    def get_required_env_vars(self) -> List[str]:
        """Get list of required environment variables."""
        return [
            "DATABASE_URL",
            "TRIVY_URL",
            "TRIVY_TIMEOUT",
            "TRIVY_MAX_RETRIES",
        ]
