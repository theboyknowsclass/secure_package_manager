"""Parse Worker.

Processes raw request blobs to extract packages from package-lock.json
files. This worker delegates all business logic to PackageLockParsingService.
"""

import logging
from typing import Optional, List, Optional

from services.package_lock_parsing_service import PackageLockParsingService
from workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class ParseWorker(BaseWorker):
    """Background worker for parsing package-lock.json blobs and extracting
    packages.

    This worker coordinates the parsing process by:
    1. Delegating parsing logic to PackageLockParsingService
    2. Handling results and logging progress
    """

    WORKER_TYPE = "parse_worker"

    def __init__(self, sleep_interval: int = 10):
        super().__init__("ParseWorker", sleep_interval)
        self.max_requests_per_cycle = 5  # Process max 5 requests per cycle
        self.parsing_service: Optional[PackageLockParsingService] = None

    def initialize(self) -> None:
        """Initialize the worker and its dependencies."""
        logger.info("Initializing ParseWorker...")

        # Initialize parsing service
        self.parsing_service = PackageLockParsingService()
        logger.info("ParseWorker parsing service initialized")

    def process_cycle(self) -> None:
        """Process one cycle of package lock parsing."""
        try:
            # Service now manages its own database sessions
            if self.parsing_service is None:
                logger.error(
                    "ParseWorker not initialized - parsing service is None"
                )
                return
            result = self.parsing_service.process_requests(
                self.max_requests_per_cycle
            )

            if result["success"]:
                if result.get("processed_requests", 0) > 0:
                    logger.info(
                        f"Parse processing complete: {result.get('successful_parsing', 0)} successful, "
                        f"{result.get('failed_parsing', 0)} failed across {result.get('processed_requests', 0)} requests"
                    )
                else:
                    logger.info(
                        "ParseWorker heartbeat: No requests found for parsing"
                    )
            else:
                logger.error(
                    f"Parse processing failed: {result.get('error', 'Unknown error')}"
                )

        except Exception as e:
            logger.error(
                f"Error in parse worker cycle: {str(e)}", exc_info=True
            )

    def get_required_env_vars(self) -> List[str]:
        """Get list of required environment variables."""
        return ["DATABASE_URL"]
