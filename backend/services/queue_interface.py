"""Queue Interface Shim.

Currently implements status advancement directly via the database.
Later, this can be swapped to enqueue Celery/Redis tasks without
changing callers.
"""

import logging
import os

from database.models import PackageStatus
from database.operations.package_status_operations import (
    PackageStatusOperations,
)
from database.service import DatabaseService

logger = logging.getLogger(__name__)


class QueueInterface:
    """Thin queue abstraction for future Celery/Redis migration."""

    def __init__(self) -> None:
        """Initialize the queue interface."""
        self.database_url = os.getenv("DATABASE_URL", "")
        self.db_service = DatabaseService(self.database_url)

    def advance_status(self, package_id: int, next_status: str) -> bool:
        try:
            with self.db_service.get_session() as session:
                status_ops = PackageStatusOperations(session)
                status = status_ops.get_by_package_id(package_id)
                if not status:
                    logger.warning(f"advance_status: no PackageStatus for package_id={package_id}")
                    return False

                prev_status = status.status
                success = status_ops.update_status(package_id, next_status)
                if success:
                    session.commit()
                    logger.info(f"Status advanced: package_id={package_id} {prev_status} -> {next_status}")
                    return True
                return False
        except Exception as e:
            logger.error(
                f"advance_status failed for package_id={package_id}: {str(e)}",
                exc_info=True,
            )
            with self.db_service.get_session() as session:
                session.rollback()
            return False
