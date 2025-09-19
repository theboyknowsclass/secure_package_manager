"""Approval Worker.

Transitions packages from Security Scanned to Pending Approval status.
This is a lightweight worker that delegates all business logic to ApprovalService.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

from database.session_helper import SessionHelper
from services.approval_service import ApprovalService
from workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class ApprovalWorker(BaseWorker):
    """Background worker for transitioning packages to pending approval.

    This worker coordinates the approval workflow by:
    1. Finding packages that need approval transitions
    2. Delegating approval logic to ApprovalService
    3. Handling results and logging progress
    """

    WORKER_TYPE = "approval_worker"

    def __init__(self, sleep_interval: int = 30):
        super().__init__("ApprovalWorker", sleep_interval)
        self.approval_service = None
        self.max_packages_per_cycle = (
            50  # Can handle many packages since it's just status updates
        )

    def initialize(self) -> None:
        """Initialize services."""
        logger.info("Initializing ApprovalWorker services...")
        self.approval_service = ApprovalService()
        logger.info("ApprovalWorker services initialized")

    def process_cycle(self) -> None:
        """Process one cycle of approval work."""
        try:
            with SessionHelper.get_session() as db:
                # Process packages using the service
                result = self.approval_service.process_security_scanned_packages(
                    self.max_packages_per_cycle
                )

                if result["success"]:
                    if result["processed_count"] > 0:
                        logger.info(
                            f"Successfully transitioned {result['processed_count']} packages to Pending Approval"
                        )
                    else:
                        logger.info(
                            "ApprovalWorker heartbeat: No packages found for approval transition"
                        )
                else:
                    logger.error(
                        f"Error processing security scanned packages: {result['error']}"
                    )

        except Exception as e:
            logger.error(f"Approval cycle error: {str(e)}", exc_info=True)

    def get_approval_stats(self) -> Dict[str, Any]:
        """Get current approval statistics."""
        try:
            with SessionHelper.get_session() as db:
                stats = self.approval_service.get_approval_statistics()
                stats["worker_status"] = self.get_worker_status()
                return stats
        except Exception as e:
            logger.error(f"Error getting approval stats: {str(e)}")
            return {"error": str(e)}

    def get_required_env_vars(self) -> List[str]:
        """Get list of required environment variables."""
        return ["DATABASE_URL"]