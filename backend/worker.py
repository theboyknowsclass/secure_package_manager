#!/usr/bin/env python3
"""
Background Worker Entry Point

This is the main entry point for the background worker service.
It can run different types of workers based on the WORKER_TYPE environment variable.
"""

import logging
import os
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/app/logs/worker.log", mode="a")
        if os.path.exists("/app/logs")
        else logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)


def main():
    """Main entry point for the worker"""
    # Get worker type from environment
    worker_type = os.getenv("WORKER_TYPE", "parse_worker")
    sleep_interval = int(os.getenv("WORKER_SLEEP_INTERVAL", "10"))
    max_packages_per_cycle = int(os.getenv("WORKER_MAX_PACKAGES_PER_CYCLE", "5"))
    max_license_groups_per_cycle = int(os.getenv("WORKER_MAX_LICENSE_GROUPS_PER_CYCLE", "20"))

    logger.info(f"Starting {worker_type} worker...")
    logger.info("Worker configuration:")
    logger.info(f"  - Type: {worker_type}")
    logger.info(f"  - Sleep interval: {sleep_interval} seconds")
    logger.info(f"  - Max packages per cycle: {max_packages_per_cycle}")
    logger.info(f"  - Max license groups per cycle: {max_license_groups_per_cycle}")

    try:
        # Import all worker classes
        from workers.license_worker import LicenseWorker
        from workers.publish_worker import PublishWorker
        from workers.parse_worker import ParseWorker
        from workers.download_worker import DownloadWorker
        from workers.security_worker import SecurityWorker
        from workers.approval_worker import ApprovalWorker

        # Create a registry of worker classes by their WORKER_TYPE
        worker_registry = {
            LicenseWorker.WORKER_TYPE: LicenseWorker,
            PublishWorker.WORKER_TYPE: PublishWorker,
            ParseWorker.WORKER_TYPE: ParseWorker,
            DownloadWorker.WORKER_TYPE: DownloadWorker,
            SecurityWorker.WORKER_TYPE: SecurityWorker,
            ApprovalWorker.WORKER_TYPE: ApprovalWorker,
        }

        # Get the worker class from the registry
        worker_class = worker_registry.get(worker_type)
        if not worker_class:
            logger.error(f"Unknown worker type: {worker_type}")
            logger.error(f"Supported worker types: {', '.join(worker_registry.keys())}")
            sys.exit(1)

        # Create the worker instance
        worker = worker_class(sleep_interval=sleep_interval)
        
        # Set worker-specific configuration
        if hasattr(worker, 'max_license_groups_per_cycle'):
            worker.max_license_groups_per_cycle = max_license_groups_per_cycle
        if hasattr(worker, 'max_packages_per_cycle'):
            worker.max_packages_per_cycle = max_packages_per_cycle

        # Start the worker (this will run until interrupted)
        worker.start()

    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
    except Exception as e:
        logger.error(f"Worker failed with error: {str(e)}", exc_info=True)
        sys.exit(1)

    logger.info(f"{worker_type} worker stopped")


if __name__ == "__main__":
    main()
