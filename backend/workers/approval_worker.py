"""Approval Worker.

Transitions packages from Security Scanned to Pending Approval status using
entity-based operations and delegates business logic to services while maintaining logging and coordination.
This is a lightweight worker that can be extended for auto-approval logic in the future.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List

from database.operations.composite_operations import CompositeOperations
from database.service import DatabaseService
from services.approval_service import ApprovalService
from workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class ApprovalWorker(BaseWorker):
    """Background worker for transitioning packages to pending approval.

    This worker coordinates the approval workflow by:
    1. Finding packages that need approval transitions
    2. Handling stuck packages
    3. Delegating approval logic to ApprovalService
    4. Handling results and logging progress
    """

    WORKER_TYPE = "approval_worker"

    def __init__(self, sleep_interval: int = 30):
        super().__init__("ApprovalWorker", sleep_interval)
        self.approval_service = None
        self.db_service = None
        self.max_packages_per_cycle = (
            50  # Can handle many packages since it's just status updates
        )
        self.stuck_package_timeout = timedelta(
            minutes=10
        )  # Short timeout since this should be fast

    def initialize(self) -> None:
        """Initialize services."""
        logger.info("Initializing ApprovalWorker services...")
        self.approval_service = ApprovalService()

        # Initialize database service
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is required")

        self.db_service = DatabaseService(database_url)
        logger.info("ApprovalWorker services initialized")

    def process_cycle(self) -> None:
        """Process one cycle of approval work."""
        try:
            with CompositeOperations.get_operations() as ops:
                # Handle stuck packages first
                self._handle_stuck_packages(ops)

                # Find packages that need approval transitions
                security_scanned_packages = ops.package.get_by_status("Security Scanned")
                
                # Limit the number of packages processed per cycle
                limited_packages = security_scanned_packages[:self.max_packages_per_cycle]

                if not limited_packages:
                    logger.info(
                        "ApprovalWorker heartbeat: No packages found for approval transition"
                    )
                    return

                logger.info(
                    f"Transitioning {len(limited_packages)} packages from Security Scanned to Pending Approval"
                )

                # Process packages using the service
                result = self.approval_service.process_security_scanned_packages(
                    limited_packages, ops
                )

                if result["success"]:
                    logger.info(
                        f"Successfully transitioned {result['processed_count']} packages to Pending Approval"
                    )
                else:
                    logger.error(
                        f"Error processing security scanned packages: {result['error']}"
                    )

        except Exception as e:
            logger.error(f"Approval cycle error: {str(e)}", exc_info=True)

    def _handle_stuck_packages(self, ops) -> None:
        """Handle packages that have been stuck in Security Scanned state too long."""
        try:
            stuck_threshold = datetime.utcnow() - self.stuck_package_timeout
            stuck_packages = self.approval_service.get_stuck_packages(
                stuck_threshold, ops
            )

            if stuck_packages:
                logger.warning(
                    f"Found {len(stuck_packages)} packages stuck in Security Scanned state"
                )
                # Just refresh their timestamp to avoid constant reprocessing
                self.approval_service.refresh_stuck_packages(stuck_packages, ops)

        except Exception as e:
            logger.error(
                f"Error handling stuck packages: {str(e)}", exc_info=True
            )

    def get_approval_stats(self) -> Dict[str, Any]:
        """Get current approval statistics."""
        try:
            with CompositeOperations.get_operations() as ops:
                stats = self.approval_service.get_approval_statistics(ops)
                stats["worker_status"] = self.get_worker_status()
                return stats
        except Exception as e:
            logger.error(f"Error getting approval stats: {str(e)}")
            return {"error": str(e)}

    def get_required_env_vars(self) -> List[str]:
        """Get list of required environment variables."""
        return ["DATABASE_URL"]