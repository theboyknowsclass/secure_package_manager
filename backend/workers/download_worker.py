"""
Download Worker

Transitions packages from Licence Checked to Downloaded (via Downloading).
"""

import logging
from datetime import datetime, timedelta

from models import Package, PackageStatus, db
from services.download_service import DownloadService
from services.queue_interface import QueueInterface
from workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class DownloadWorker(BaseWorker):
    def __init__(self, sleep_interval: int = 10):
        super().__init__("DownloadWorker", sleep_interval)
        self.max_packages_per_cycle = 10
        self.stuck_package_timeout = timedelta(minutes=30)
        self.download_service: DownloadService | None = None
        self.queue = QueueInterface()

    def initialize(self) -> None:
        logger.info("Initializing DownloadWorker...")
        self.download_service = DownloadService()

    def process_cycle(self) -> None:
        try:
            self._handle_stuck_packages()
            self._process_ready_packages()
        except Exception as e:
            logger.error(f"Download cycle error: {str(e)}", exc_info=True)

    def _handle_stuck_packages(self) -> None:
        try:
            stuck_threshold = datetime.utcnow() - self.stuck_package_timeout
            stuck_statuses = ["Downloading"]
            stuck_packages = (
                db.session.query(Package)
                .join(PackageStatus)
                .filter(
                    PackageStatus.status.in_(stuck_statuses),
                    PackageStatus.updated_at < stuck_threshold,
                )
                .all()
            )
            if not stuck_packages:
                return
            logger.warning(f"Found {len(stuck_packages)} stuck downloads; resetting to Licence Checked")
            for package in stuck_packages:
                if package.package_status:
                    package.package_status.status = "Licence Checked"
                    package.package_status.updated_at = datetime.utcnow()
            db.session.commit()
        except Exception:
            logger.exception("Error handling stuck downloads")
            db.session.rollback()

    def _process_ready_packages(self) -> None:
        packages = (
            db.session.query(Package)
            .join(PackageStatus)
            .filter(PackageStatus.status == "Licence Checked")
            .limit(self.max_packages_per_cycle)
            .all()
        )
        if not packages:
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
        db.session.commit()

    def _download_single(self, package: Package) -> None:
        if not self.download_service or not package.package_status:
            return

        # Already downloaded
        if self.download_service.is_package_downloaded(package):
            package.package_status.status = "Downloaded"
            package.package_status.updated_at = datetime.utcnow()
            db.session.flush()
            return

        # Mark downloading
        package.package_status.status = "Downloading"
        package.package_status.updated_at = datetime.utcnow()
        db.session.flush()

        if not self.download_service.download_package(package):
            raise RuntimeError("download failed")

        package.package_status.status = "Downloaded"
        package.package_status.updated_at = datetime.utcnow()
        db.session.flush()

    def _mark_failed(self, package: Package) -> None:
        try:
            if package.package_status:
                package.package_status.status = "Rejected"
                package.package_status.updated_at = datetime.utcnow()
        except Exception:
            logger.exception("Error marking package as rejected in DownloadWorker")


