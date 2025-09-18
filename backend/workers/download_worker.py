"""
Download Worker

Transitions packages from Licence Checked to Downloaded (via Downloading).
"""

import logging
import os
from datetime import datetime, timedelta

from database.models import Package, PackageStatus
from database.operations import DatabaseOperations
from database.service import DatabaseService
from services.download_service import DownloadService
from services.queue_interface import QueueInterface
from workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class DownloadWorker(BaseWorker):
    """Background worker for downloading packages"""

    WORKER_TYPE = "download_worker"

    # Extend base environment variables with download-specific ones
    required_env_vars = BaseWorker.required_env_vars + ["SOURCE_REPOSITORY_URL"]

    def __init__(self, sleep_interval: int = 10):
        super().__init__("DownloadWorker", sleep_interval)
        self.max_packages_per_cycle = 10
        self.stuck_package_timeout = timedelta(minutes=30)
        self.download_service: DownloadService | None = None
        self.db_service = None
        self.ops = None
        self.queue = QueueInterface()

    def initialize(self) -> None:
        logger.info("Initializing DownloadWorker...")
        self.download_service = DownloadService()

        # Initialize database service
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is required")

        self.db_service = DatabaseService(database_url)

    def process_cycle(self) -> None:
        try:
            with self.db_service.get_session() as session:
                self.ops = DatabaseOperations(session)
                self._handle_stuck_packages()
                self._process_ready_packages()
        except Exception as e:
            logger.error(f"Download cycle error: {str(e)}", exc_info=True)

    def _handle_stuck_packages(self) -> None:
        try:
            stuck_threshold = datetime.utcnow() - self.stuck_package_timeout
            stuck_statuses = ["Downloading"]
            stuck_packages = self.ops.get_packages_by_statuses(stuck_statuses, Package, PackageStatus)
            stuck_packages = [
                p for p in stuck_packages if p.package_status and p.package_status.updated_at < stuck_threshold
            ]

            if not stuck_packages:
                return
            logger.warning(f"Found {len(stuck_packages)} stuck downloads; resetting to Licence Checked")
            for package in stuck_packages:
                if package.package_status:
                    self.ops.update_package_status(package.id, "Licence Checked", PackageStatus)
        except Exception:
            logger.exception("Error handling stuck downloads")

    def _process_ready_packages(self) -> None:
        packages = self.ops.get_packages_by_status("Licence Checked", Package, PackageStatus)
        packages = packages[: self.max_packages_per_cycle]

        if not packages:
            logger.info("DownloadWorker heartbeat: No packages found for downloading")
            return

        logger.info(f"Downloading {len(packages)} packages")
        for package in packages:
            try:
                self._download_single(package)
            except Exception as e:
                logger.error(
                    f"Download failed for {package.name}@{package.version}: {str(e)}",
                    exc_info=True,
                )
                self._mark_failed(package)

    def _download_single(self, package: Package) -> None:
        if not self.download_service or not package.package_status:
            return

        # Already downloaded
        if self.download_service.is_package_downloaded(package):
            self.ops.update_package_status(package.id, "Downloaded", PackageStatus)
            return

        # Mark downloading
        self.ops.update_package_status(package.id, "Downloading", PackageStatus)

        if not self.download_service.download_package(package):
            raise RuntimeError("download failed")

        self.ops.update_package_status(package.id, "Downloaded", PackageStatus)

    def _mark_failed(self, package: Package) -> None:
        try:
            if package.package_status:
                self.ops.update_package_status(package.id, "Rejected", PackageStatus)
        except Exception:
            logger.exception("Error marking package as rejected in DownloadWorker")
