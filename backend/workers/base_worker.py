"""
Base Worker Class

Provides common functionality for all background workers including
database connection management, logging, and error handling.
"""

import logging
import signal
import time
from abc import ABC, abstractmethod
from typing import Any, Dict

from app import create_app

logger = logging.getLogger(__name__)


class BaseWorker(ABC):
    """Base class for all background workers"""

    def __init__(self, worker_name: str, sleep_interval: int = 5):
        """
        Initialize the worker

        Args:
            worker_name: Name of the worker for logging
            sleep_interval: Seconds to sleep between processing cycles
        """
        self.worker_name = worker_name
        self.sleep_interval = sleep_interval
        self.running = False
        self.app = None
        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals"""
        logger.info(f"{self.worker_name} received signal {signum}, shutting down gracefully...")
        self.running = False

    def start(self) -> None:
        """Start the worker"""
        logger.info(f"Starting {self.worker_name} worker...")

        # Create Flask app context
        self.app = create_app()

        with self.app.app_context():
            self.running = True

            # Initialize worker
            self.initialize()

            logger.info(f"{self.worker_name} worker started successfully")

            # Main processing loop
            while self.running:
                try:
                    self.process_cycle()
                except Exception as e:
                    logger.error(
                        f"Error in {self.worker_name} processing cycle: {str(e)}",
                        exc_info=True,
                    )

                if self.running:
                    time.sleep(self.sleep_interval)

            # Cleanup
            self.cleanup()
            logger.info(f"{self.worker_name} worker stopped")

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the worker - called once at startup"""

    @abstractmethod
    def process_cycle(self) -> None:
        """Process one cycle of work - called repeatedly"""

    def cleanup(self) -> None:
        """Cleanup resources - called on shutdown"""

    def get_worker_status(self) -> Dict[str, Any]:
        """Get current worker status"""
        return {
            "worker_name": self.worker_name,
            "running": self.running,
            "sleep_interval": self.sleep_interval,
        }
