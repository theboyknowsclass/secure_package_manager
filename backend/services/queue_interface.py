"""
Queue Interface Shim

Currently implements status advancement directly via the database.
Later, this can be swapped to enqueue Celery/Redis tasks without changing callers.
"""

import logging
from datetime import datetime
from typing import Optional

from models import PackageStatus, db

logger = logging.getLogger(__name__)


class QueueInterface:
    """Thin queue abstraction for future Celery/Redis migration."""

    def advance_status(self, package_id: int, next_status: str) -> bool:
        try:
            status: Optional[PackageStatus] = (
                db.session.query(PackageStatus).filter_by(package_id=package_id).first()
            )
            if not status:
                logger.warning(f"advance_status: no PackageStatus for package_id={package_id}")
                return False

            prev_status = status.status
            status.status = next_status
            status.updated_at = datetime.utcnow()
            db.session.commit()

            logger.info(
                f"Status advanced: package_id={package_id} {prev_status} -> {next_status}"
            )
            return True
        except Exception as e:
            logger.error(f"advance_status failed for package_id={package_id}: {str(e)}", exc_info=True)
            db.session.rollback()
            return False


