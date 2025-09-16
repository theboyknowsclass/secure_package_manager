#!/usr/bin/env python3
"""
Background Worker Entry Point

This is the main entry point for the background worker service.
It can run different types of workers based on the WORKER_TYPE environment variable.
"""

import logging
import os
import sys
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/app/logs/worker.log', mode='a') if os.path.exists('/app/logs') else logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Main entry point for the worker"""
    # Get worker type from environment
    worker_type = os.getenv('WORKER_TYPE', 'package_processor')
    sleep_interval = int(os.getenv('WORKER_SLEEP_INTERVAL', '10'))
    max_packages_per_cycle = int(os.getenv('WORKER_MAX_PACKAGES_PER_CYCLE', '5'))
    
    logger.info(f"Starting {worker_type} worker...")
    logger.info(f"Worker configuration:")
    logger.info(f"  - Type: {worker_type}")
    logger.info(f"  - Sleep interval: {sleep_interval} seconds")
    logger.info(f"  - Max packages per cycle: {max_packages_per_cycle}")
    
    try:
        # Import and create the appropriate worker based on type
        if worker_type == 'license_checker':
            from workers.license_worker import LicenseWorker
            worker = LicenseWorker(sleep_interval=sleep_interval)
            worker.max_packages_per_cycle = max_packages_per_cycle
            
        elif worker_type == 'package_processor':
            from workers.package_worker import PackageWorker
            worker = PackageWorker(sleep_interval=sleep_interval)
            worker.max_packages_per_cycle = max_packages_per_cycle
            
        elif worker_type == 'package_publisher':
            from workers.publish_worker import PublishWorker
            worker = PublishWorker(sleep_interval=sleep_interval)
            worker.max_packages_per_cycle = max_packages_per_cycle
            
        else:
            logger.error(f"Unknown worker type: {worker_type}")
            logger.error("Supported worker types: license_checker, package_processor, package_publisher")
            sys.exit(1)
        
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
