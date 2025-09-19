"""Parse Worker.

Processes raw request blobs to extract packages from package-lock.json
files. This worker delegates all business logic to PackageLockParsingService.
"""

import logging
from typing import List

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
        self.parsing_service = None

    def initialize(self) -> None:
        """Initialize the worker and its dependencies."""
        logger.info("Initializing ParseWorker...")

        # Initialize parsing service
        self.parsing_service = PackageLockParsingService()
        logger.info("ParseWorker parsing service initialized")

    def process_cycle(self) -> None:
        """Process one cycle of parsing work."""
        try:
            # Process requests that need parsing
            result = self.parsing_service.process_requests(self.max_requests_per_cycle)
            
            if result["success"]:
                if result.get("processed_count", 0) > 0:
                    logger.info(f"Parse cycle completed: {result.get('message', 'Success')}")
                else:
                    logger.info("ParseWorker heartbeat: No requests found for parsing")
            else:
                logger.error(f"Parse cycle failed: {result.get('error', 'Unknown error')}")

        except Exception as e:
            logger.error(f"Error in parse cycle: {str(e)}", exc_info=True)

    def get_required_env_vars(self) -> List[str]:
        """Get list of required environment variables."""
        return ["DATABASE_URL"]


