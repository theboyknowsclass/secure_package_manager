"""Parse Worker - Refactored.

Processes raw request blobs to extract packages from package-lock.json
files. Handles the Submitted -> Parsed transition by parsing the stored
JSON blob.

This refactored version uses entity-based operations and delegates
business logic to services while maintaining logging and coordination.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from database.operations import OperationsFactory
from database.service import DatabaseService
from services.package_lock_parsing_service_refactored import PackageLockParsingService
from workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class ParseWorker(BaseWorker):
    """Background worker for parsing package-lock.json blobs and extracting
    packages.
    
    This worker coordinates the parsing process by:
    1. Finding requests that need parsing
    2. Delegating parsing logic to PackageLockParsingService
    3. Handling results and logging progress
    """

    WORKER_TYPE = "parse_worker"

    def __init__(self, sleep_interval: int = 10):
        super().__init__("ParseWorker", sleep_interval)
        self.max_requests_per_cycle = 5  # Process max 5 requests per cycle
        self.stuck_request_timeout = timedelta(minutes=15)
        self.db_service = None
        self.parsing_service = None

    def initialize(self) -> None:
        """Initialize the worker and its dependencies."""
        logger.info("Initializing ParseWorker...")
        
        # Initialize database service
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is required")

        self.db_service = DatabaseService(database_url)
        logger.info("ParseWorker database service initialized")
        
        # Initialize parsing service
        self.parsing_service = PackageLockParsingService()
        logger.info("ParseWorker parsing service initialized")

    def process_cycle(self) -> None:
        """Process one cycle of parsing work."""
        try:
            with self.db_service.get_session() as session:
                ops = OperationsFactory.create_all_operations(session)
                
                # Handle stuck requests first
                self._handle_stuck_requests(ops)
                
                # Process requests that need parsing
                self._process_submitted_requests(ops)
                
        except Exception as e:
            logger.error(f"Error in parse cycle: {str(e)}", exc_info=True)

    def _handle_stuck_requests(self, ops: Dict[str, Any]) -> None:
        """Handle requests that have been stuck in processing too long."""
        try:
            stuck_threshold = datetime.utcnow() - self.stuck_request_timeout
            
            # Get all requests and check for stuck ones
            all_requests = ops['request'].get_all()
            stuck_requests = [
                r for r in all_requests 
                if r.created_at < stuck_threshold
            ]

            if stuck_requests:
                logger.warning(
                    f"Found {len(stuck_requests)} potentially stuck requests"
                )
                # In a real implementation, you might want to add retry logic
                # or error handling for stuck requests

        except Exception as e:
            logger.error(
                f"Error handling stuck requests: {str(e)}", exc_info=True
            )

    def _process_submitted_requests(self, ops: Dict[str, Any]) -> None:
        """Process requests that need package extraction."""
        try:
            # Find requests that need parsing
            requests_to_process = ops['request'].get_needing_parsing()
            
            # Limit the number of requests processed per cycle
            requests_to_process = requests_to_process[:self.max_requests_per_cycle]
            
            if not requests_to_process:
                logger.info("ParseWorker heartbeat: No requests found to parse")
                return

            logger.info(
                f"Processing {len(requests_to_process)} requests for package extraction"
            )

            for request in requests_to_process:
                try:
                    self._parse_request_blob(request, ops)
                except Exception as e:
                    logger.error(
                        f"Failed to parse request {request.id}: {str(e)}",
                        exc_info=True,
                    )
                    # Mark request as failed (could add a status field to Request model)

        except Exception as e:
            logger.error(
                f"Error processing submitted requests: {str(e)}", exc_info=True
            )

    def _parse_request_blob(self, request, ops: Dict[str, Any]) -> None:
        """Parse a request's raw blob and extract packages."""
        try:
            logger.info(f"Starting to parse request {request.id}")
            
            # Parse the JSON blob
            package_data = json.loads(request.raw_request_blob)
            
            # Delegate parsing logic to the service
            result = self.parsing_service.parse_package_lock(
                request.id, package_data, ops
            )
            
            # Handle the results
            self._handle_parsing_results(request, result, ops)
            
            logger.info(
                f"Successfully parsed request {request.id}: "
                f"Created {result.get('packages_to_process', 0)} new packages, "
                f"linked {result.get('existing_packages', 0)} existing packages"
            )

        except Exception as e:
            logger.error(f"Error parsing request {request.id} blob: {str(e)}")
            raise e

    def _handle_parsing_results(self, request, result: Dict[str, Any], ops: Dict[str, Any]) -> None:
        """Handle the results of parsing a request."""
        try:
            # Log the parsing results
            packages_created = result.get('packages_to_process', 0)
            existing_packages = result.get('existing_packages', 0)
            total_packages = result.get('total_packages', 0)
            
            logger.info(
                f"Request {request.id} parsing complete: "
                f"{packages_created} new packages, "
                f"{existing_packages} existing packages, "
                f"{total_packages} total packages"
            )
            
            # Update request status if needed (when Request model has status field)
            # For now, we just log the completion
            
        except Exception as e:
            logger.error(
                f"Error handling parsing results for request {request.id}: {str(e)}"
            )
            raise e

    def get_worker_stats(self) -> Dict[str, Any]:
        """Get current worker statistics."""
        try:
            with self.db_service.get_session() as session:
                ops = OperationsFactory.create_all_operations(session)
                
                # Get request statistics
                all_requests = ops['request'].get_all()
                requests_with_packages = len([
                    r for r in all_requests 
                    if ops['request_package'].get_by_request_id(r.id)
                ])
                
                # Get package statistics
                all_packages = ops['package'].get_all()
                
                return {
                    "worker_status": self.get_worker_status(),
                    "total_requests": len(all_requests),
                    "requests_with_packages": requests_with_packages,
                    "requests_needing_parsing": len(ops['request'].get_needing_parsing()),
                    "total_packages": len(all_packages),
                    "timestamp": datetime.utcnow().isoformat(),
                }
                
        except Exception as e:
            logger.error(f"Error getting worker stats: {str(e)}")
            return {"error": str(e)}
