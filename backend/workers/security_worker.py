"""
Security Scan Worker

Transitions packages from Downloaded to Security Scanned (via Security Scanning),
storing scan status/score.
"""

import logging
import os
from datetime import datetime, timedelta

from database.service import DatabaseService
from database.operations import DatabaseOperations
from database.models import Package, PackageStatus
from services.trivy_service import TrivyService
from workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class SecurityWorker(BaseWorker):
    """Background worker for security scanning packages"""

    WORKER_TYPE = "security_worker"

    # Extend base environment variables with Trivy-specific ones
    required_env_vars = BaseWorker.required_env_vars + [
        "TRIVY_URL",
        "TRIVY_TIMEOUT",
        "TRIVY_MAX_RETRIES"
    ]

    def __init__(self, sleep_interval: int = 15):
        super().__init__("SecurityWorker", sleep_interval)
        self.max_packages_per_cycle = 10
        self.stuck_package_timeout = timedelta(minutes=45)
        self.trivy_service: TrivyService | None = None
        self.db_service = None
        self.ops = None

    def initialize(self) -> None:
        logger.info("Initializing SecurityWorker...")
        self.trivy_service = TrivyService()
        
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
                self._process_downloaded_packages()
        except Exception as e:
            logger.error(f"Security cycle error: {str(e)}", exc_info=True)

    def _handle_stuck_packages(self) -> None:
        try:
            stuck_threshold = datetime.utcnow() - self.stuck_package_timeout
            stuck_statuses = ["Security Scanning"]
            stuck_packages = self.ops.get_packages_by_statuses(stuck_statuses, Package, PackageStatus)
            stuck_packages = [p for p in stuck_packages if p.package_status and p.package_status.updated_at < stuck_threshold]
            if not stuck_packages:
                return
            logger.warning(f"Found {len(stuck_packages)} stuck security scans; resetting to Downloaded")
            for package in stuck_packages:
                if package.package_status:
                    self.ops.update_package_status(package.id, "Downloaded", PackageStatus)
        except Exception:
            logger.exception("Error handling stuck security scans")

    def _process_downloaded_packages(self) -> None:
        packages = self.ops.get_packages_by_status("Downloaded", Package, PackageStatus)
        packages = packages[:self.max_packages_per_cycle]
        if not packages:
            logger.info("SecurityWorker heartbeat: No packages found for security scanning")
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


