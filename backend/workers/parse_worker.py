"""
Parse Worker

Takes packages in Submitted status, validates basic metadata, computes checksum/file size
if available, and advances to Parsed.
"""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional

from models import Package, PackageStatus, db
from services.queue_interface import QueueInterface
from workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class ParseWorker(BaseWorker):
    """Background worker for parsing and preparing packages."""

    def __init__(self, sleep_interval: int = 10):
        super().__init__("ParseWorker", sleep_interval)
        self.max_packages_per_cycle = 20
        self.stuck_package_timeout = timedelta(minutes=15)
        self.queue = QueueInterface()

    def initialize(self) -> None:
        logger.info("Initializing ParseWorker...")

    def process_cycle(self) -> None:
        try:
            self._handle_stuck_packages()
            self._process_submitted_packages()
        except Exception as e:
            logger.error(f"Error in parse cycle: {str(e)}", exc_info=True)

    def _handle_stuck_packages(self) -> None:
        try:
            stuck_threshold = datetime.utcnow() - self.stuck_package_timeout
            stuck_statuses = ["Submitted"]
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
            logger.warning(f"Found {len(stuck_packages)} stuck submitted packages")
            for package in stuck_packages:
                # no status reset; just refresh updated_at to avoid constant reprocessing
                if package.package_status:
                    package.package_status.updated_at = datetime.utcnow()
            db.session.commit()
        except Exception as e:
            logger.error(f"Error handling stuck packages: {str(e)}", exc_info=True)
            db.session.rollback()

    def _process_submitted_packages(self) -> None:
        packages = (
            db.session.query(Package)
            .join(PackageStatus)
            .filter(PackageStatus.status == "Submitted")
            .limit(self.max_packages_per_cycle)
            .all()
        )
        if not packages:
            return
        logger.info(f"Parsing {len(packages)} packages")
        for package in packages:
            try:
                self._parse_single(package)
            except Exception as e:
                logger.error(
                    f"Parse failed for {package.name}@{package.version}: {str(e)}",
                    exc_info=True,
                )
                self._mark_failed(package)
        db.session.commit()

    def _parse_single(self, package: Package) -> None:
        if not package.package_status:
            return

        # If already parsed or beyond, skip
        if package.package_status.status in {"Parsed", "Checking Licence", "Licence Checked", "Downloading", "Downloaded", "Security Scanning", "Security Scanned", "Pending Approval", "Approved", "Rejected"}:
            return

        # Example checksum from npm_url/local_path if available (best-effort)
        checksum: Optional[str] = package.package_status.checksum
        file_size: Optional[int] = package.package_status.file_size

        if not checksum and package.local_path:
            try:
                sha256 = hashlib.sha256()
                with open(package.local_path, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        sha256.update(chunk)
                checksum = sha256.hexdigest()
                package.package_status.checksum = checksum
            except Exception:
                # ignore missing local file at this stage
                pass

        if not file_size and package.local_path:
            try:
                import os

                package.package_status.file_size = os.path.getsize(package.local_path)
            except Exception:
                pass

        package.package_status.updated_at = datetime.utcnow()
        db.session.flush()

        self.queue.advance_status(package.id, "Parsed")

    def _mark_failed(self, package: Package) -> None:
        try:
            if package.package_status:
                package.package_status.status = "Rejected"
                package.package_status.updated_at = datetime.utcnow()
        except Exception:
            logger.exception("Error marking package as rejected in ParseWorker")


