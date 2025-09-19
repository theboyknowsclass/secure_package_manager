"""Package Publishing Worker.

Handles background publishing of approved packages to the secure
repository. This worker delegates all business logic to PublishingService.
"""

import logging
from typing import Any, Dict, List

from database.session_helper import SessionHelper
from services.publishing_service import PublishingService
from workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class PublishWorker(BaseWorker):
    """Background worker for publishing approved packages.

    This worker coordinates the package publishing process by:
    1. Delegating publishing logic to PublishingService
    2. Handling results and logging progress
    """

    WORKER_TYPE = "package_publisher"

    # Extend base environment variables with publish-specific ones
    required_env_vars = BaseWorker.required_env_vars + [
        "TARGET_REPOSITORY_URL"
    ]

    def __init__(self, sleep_interval: int = 30):
        super().__init__("PackagePublisher", sleep_interval)
        self.publishing_service = None
        self.max_packages_per_cycle = (
            3  # Process max 3 packages per cycle (publishing is slow)
        )

    def initialize(self) -> None:
        """Initialize services."""
        logger.info("Initializing PublishWorker services...")
        self.publishing_service = PublishingService()
        logger.info("PublishWorker services initialized")

    def process_cycle(self) -> None:
        """Process one cycle of package publishing."""
        try:
            with SessionHelper.get_session() as db:
                # Process packages using the service
                result = self.publishing_service.process_package_batch(
                    self.max_packages_per_cycle
                )

                if result["success"]:
                    if result["processed_count"] > 0:
                        logger.info(
                            f"Publishing complete: {result['successful_packages']} successful, "
                            f"{result['failed_packages']} failed"
                        )
                    else:
                        logger.info(
                            "PublishWorker heartbeat: No packages found for publishing"
                        )
                else:
                    logger.error(
                        f"Error in publishing batch: {result['error']}"
                    )

        except Exception as e:
            logger.error(
                f"Error in PublishWorker process_cycle: {str(e)}",
                exc_info=True,
            )

    def get_publishing_stats(self) -> Dict[str, Any]:
        """Get current publishing statistics."""
        try:
            with SessionHelper.get_session() as db:
                stats = self.publishing_service.get_publishing_statistics()
                stats["worker_status"] = self.get_worker_status()
                return stats
        except Exception as e:
            logger.error(f"Error getting publishing stats: {str(e)}")
            return {"error": str(e)}

    def retry_failed_publishing(self) -> Dict[str, Any]:
        """Retry failed publishing packages."""
        try:
            with SessionHelper.get_session() as db:
                result = self.publishing_service.retry_failed_packages()
                
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