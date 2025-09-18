"""
Security Scan Worker

Transitions packages from Downloaded to Security Scanned (via Security Scanning),
storing scan status/score.
"""

import logging
from datetime import datetime, timedelta

from models import Package, PackageStatus, db
from services.trivy_service import TrivyService
from workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class SecurityWorker(BaseWorker):
    def __init__(self, sleep_interval: int = 15):
        super().__init__("SecurityWorker", sleep_interval)
        self.max_packages_per_cycle = 10
        self.stuck_package_timeout = timedelta(minutes=45)
        self.trivy_service: TrivyService | None = None

    def initialize(self) -> None:
        logger.info("Initializing SecurityWorker...")
        self.trivy_service = TrivyService()

    def process_cycle(self) -> None:
        try:
            self._handle_stuck_packages()
            self._process_downloaded_packages()
        except Exception as e:
            logger.error(f"Security cycle error: {str(e)}", exc_info=True)

    def _handle_stuck_packages(self) -> None:
        try:
            stuck_threshold = datetime.utcnow() - self.stuck_package_timeout
            stuck_statuses = ["Security Scanning"]
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
            logger.warning(f"Found {len(stuck_packages)} stuck security scans; resetting to Downloaded")
            for package in stuck_packages:
                if package.package_status:
                    package.package_status.status = "Downloaded"
                    package.package_status.updated_at = datetime.utcnow()
            db.session.commit()
        except Exception:
            logger.exception("Error handling stuck security scans")
            db.session.rollback()

    def _process_downloaded_packages(self) -> None:
        packages = (
            db.session.query(Package)
            .join(PackageStatus)
            .filter(PackageStatus.status == "Downloaded")
            .limit(self.max_packages_per_cycle)
            .all()
        )
        if not packages:
            return

        logger.info(f"Security scanning {len(packages)} packages")
        for package in packages:
            try:
                self._scan_single(package)
            except Exception as e:
                logger.error(
                    f"Security scan failed for {package.name}@{package.version}: {str(e)}",
                    exc_info=True,
                )
                self._mark_failed(package)
        db.session.commit()

    def _scan_single(self, package: Package) -> None:
        if not self.trivy_service or not package.package_status:
            return

        package.package_status.status = "Security Scanning"
        package.package_status.security_scan_status = "running"
        package.package_status.updated_at = datetime.utcnow()
        db.session.flush()

        result = self.trivy_service.scan_package(package)

        if result.get("status") == "failed":
            package.package_status.status = "Security Scanned"
            package.package_status.security_scan_status = "failed"
        else:
            package.package_status.status = "Security Scanned"
            package.package_status.security_scan_status = "completed"
            if "security_score" in result:
                package.package_status.security_score = result["security_score"]

        package.package_status.updated_at = datetime.utcnow()
        db.session.flush()

    def _mark_failed(self, package: Package) -> None:
        try:
            if package.package_status:
                package.package_status.status = "Security Scanned"
                package.package_status.security_scan_status = "failed"
                package.package_status.updated_at = datetime.utcnow()
        except Exception:
            logger.exception("Error marking package as failed in SecurityWorker")


