#!/usr/bin/env python3
"""Background Worker Entry Point.

This is the main entry point for the background worker service. It can
run different types of workers based on the WORKER_TYPE environment
variable.
"""

import logging
import os
import sys
from pathlib import Path
from typing import cast

# Configure logging - minimal output for production
log_level = (
    logging.ERROR if os.getenv("FLASK_ENV") == "production" else logging.INFO
)
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        (
            logging.FileHandler("/app/logs/worker.log", mode="a")
            if Path("/app/logs").exists()
            else logging.StreamHandler(sys.stdout)
        ),
    ],
)

# Suppress noisy loggers
logging.getLogger("urllib3").setLevel(logging.ERROR)
logging.getLogger("requests").setLevel(logging.ERROR)
logging.getLogger("sqlalchemy.engine").setLevel(logging.ERROR)
logging.getLogger("sqlalchemy.pool").setLevel(logging.ERROR)

logger = logging.getLogger(__name__)


def get_worker_class_by_type(worker_type: str) -> type | None:
    """Get worker class by type using dynamic import - only load the specific worker needed."""
    # Define worker type to module mapping
    worker_modules = {
        "approval_worker": ("workers.approval_worker", "ApprovalWorker"),
        "download_worker": ("workers.download_worker", "DownloadWorker"),
        "license_worker": ("workers.license_worker", "LicenseWorker"),
        "parse_worker": ("workers.parse_worker", "ParseWorker"),
        "package_publisher": ("workers.publish_worker", "PublishWorker"),
        "security_worker": ("workers.security_worker", "SecurityWorker"),
    }

    if worker_type not in worker_modules:
        return None

    module_name, class_name = worker_modules[worker_type]
    try:
        module = __import__(module_name, fromlist=[class_name])
        return cast(type, getattr(module, class_name))
    except (ImportError, AttributeError) as e:
        logger.error(f"Failed to import {worker_type} from {module_name}: {e}")
        return None


def get_available_worker_types() -> list[str]:
    """Get list of all available worker types."""
    # Return the predefined worker types without importing all modules
    return [
        "approval_worker",
        "download_worker",
        "license_worker",
        "parse_worker",
        "package_publisher",
        "security_worker",
    ]


def main() -> None:
    """Main entry point for the worker."""
    # Get worker type from environment
    worker_type = os.getenv("WORKER_TYPE", "parse_worker")
    sleep_interval = int(os.getenv("WORKER_SLEEP_INTERVAL", "10"))
    max_packages_per_cycle = int(
        os.getenv("WORKER_MAX_PACKAGES_PER_CYCLE", "5")
    )
    max_license_groups_per_cycle = int(
        os.getenv("WORKER_MAX_LICENSE_GROUPS_PER_CYCLE", "20")
    )

    # Only log startup details in development
    if os.getenv("FLASK_ENV") != "production":
        logger.info(f"Starting {worker_type} worker...")
        logger.info("Worker configuration:")
        logger.info(f"  - Type: {worker_type}")
        logger.info(f"  - Sleep interval: {sleep_interval} seconds")
        logger.info(f"  - Max packages per cycle: {max_packages_per_cycle}")
        logger.info(
            f"  - Max license groups per cycle: {max_license_groups_per_cycle}"
        )
    else:
        # In production, only log essential startup info
        logger.info(f"Starting {worker_type} worker")

    try:
        # Get the worker class by type
        worker_class = get_worker_class_by_type(worker_type)
        if not worker_class:
            available_types = get_available_worker_types()

            logger.error(f"Unknown worker type: {worker_type}")
            logger.error(
                f"Supported worker types: {', '.join(available_types)}"
            )
            sys.exit(1)

        # Create the worker instance
        worker = worker_class(sleep_interval=sleep_interval)

        # Set worker-specific configuration
        if hasattr(worker, "max_license_groups_per_cycle"):
            worker.max_license_groups_per_cycle = max_license_groups_per_cycle
        if hasattr(worker, "max_packages_per_cycle"):
            worker.max_packages_per_cycle = max_packages_per_cycle

        # Start the worker (this will run until interrupted)
        worker.start()

    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
    except Exception as e:
        logger.error(f"Worker failed with error: {str(e)}", exc_info=True)
        sys.exit(1)

    # Only log shutdown in development
    if os.getenv("FLASK_ENV") != "production":
        logger.info(f"{worker_type} worker stopped")


if __name__ == "__main__":
    main()
