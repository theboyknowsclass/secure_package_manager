#!/usr/bin/env python3
"""
Package Processing Worker Entry Point

This is the main entry point for the background worker service.
It can be run as a standalone process or as a Docker container.
"""

import logging
import os
import sys
from typing import Optional

from workers.package_worker import PackageWorker

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
    logger.info("Starting Package Processing Worker...")
    
    # Get configuration from environment
    sleep_interval = int(os.getenv('WORKER_SLEEP_INTERVAL', '10'))
    max_packages_per_cycle = int(os.getenv('WORKER_MAX_PACKAGES_PER_CYCLE', '5'))
    
    logger.info(f"Worker configuration:")
    logger.info(f"  - Sleep interval: {sleep_interval} seconds")
    logger.info(f"  - Max packages per cycle: {max_packages_per_cycle}")
    
    try:
        # Create and start the worker
        worker = PackageWorker(sleep_interval=sleep_interval)
        worker.max_packages_per_cycle = max_packages_per_cycle
        
        # Start the worker (this will run until interrupted)
        worker.start()
        
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
    except Exception as e:
        logger.error(f"Worker failed with error: {str(e)}", exc_info=True)
        sys.exit(1)
    
    logger.info("Package Processing Worker stopped")


if __name__ == "__main__":
    main()
