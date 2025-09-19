"""Security Scan Worker.

Transitions packages from Downloaded to Security Scanned (via Security
Scanning), storing scan status/score using entity-based operations and delegates business logic to services while maintaining logging and coordination.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List

from database.operations import OperationsFactory
from database.service import DatabaseService
from services.security_service import SecurityService
from workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class SecurityWorker(BaseWorker):
    """Background worker for security scanning packages.

    This worker coordinates the security scanning process by:
    1. Finding packages that need security scanning
    2. Handling stuck packages
    3. Delegating security scanning logic to SecurityService
    4. Handling results and logging progress
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
        self.security_service = None
        self.db_service = None
        self.max_packages_per_cycle = 10
        self.stuck_package_timeout = timedelta(minutes=45)

    def initialize(self) -> None:
        """Initialize services."""
        logger.info("Initializing SecurityWorker services...")
        self.security_service = SecurityService()

        # Initialize database service
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is required")

        self.db_service = DatabaseService(database_url)
        logger.info("SecurityWorker services initialized")

    def process_cycle(self) -> None:
        """Process one cycle of security scanning."""
        try:
            with self.db_service.get_session() as session:
                ops = OperationsFactory.create_all_operations(session)

                # Handle stuck packages first
                self._handle_stuck_packages(ops)

                # Find packages that need security scanning
                downloaded_packages = ops["package"].get_by_status("Downloaded")
                
                # Limit the number of packages processed per cycle
                limited_packages = downloaded_packages[:self.max_packages_per_cycle]

                if not limited_packages:
                    logger.info(
                        "SecurityWorker heartbeat: No packages found for security scanning"
                    )
                    return

                logger.info(f"Security scanning {len(limited_packages)} packages")

                # Process packages using the service
                result = self.security_service.process_package_batch(
                    limited_packages, ops
                )

                if result["success"]:
                    logger.info(
                        f"Security scanning complete: {result['successful_scans']} successful, "
                        f"{result['failed_scans']} failed"
                    )
                else:
                    logger.error(
                        f"Error in security scanning batch: {result['error']}"
                    )

                # Commit the session
                session.commit()

        except Exception as e:
            logger.error(f"Security cycle error: {str(e)}", exc_info=True)

    def _handle_stuck_packages(self, ops: Dict[str, Any]) -> None:
        """Handle packages that have been stuck in Security Scanning state too long."""
        try:
            stuck_threshold = datetime.utcnow() - self.stuck_package_timeout
            stuck_packages = self.security_service.get_stuck_packages(
                stuck_threshold, ops
            )

            if stuck_packages:
                logger.warning(
                    f"Found {len(stuck_packages)} stuck security scans; resetting to Downloaded"
                )
                self.security_service.reset_stuck_packages(stuck_packages, ops)

        except Exception as e:
            logger.error(
                f"Error handling stuck packages: {str(e)}", exc_info=True
            )

    def get_required_env_vars(self) -> List[str]:
        """Get list of required environment variables."""
        return ["DATABASE_URL", "TRIVY_URL", "TRIVY_TIMEOUT", "TRIVY_MAX_RETRIES"]