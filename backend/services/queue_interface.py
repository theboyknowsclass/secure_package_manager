"""Queue Interface Shim.

Currently implements status advancement directly via the database.
Later, this can be swapped to enqueue Celery/Redis tasks without
changing callers.
"""

import logging
from datetime import datetime
from typing import Optional

from database.session_helper import SessionHelper
from database.operations.package_status_operations import PackageStatusOperations
from database.models import PackageStatus

logger = logging.getLogger(__name__)


class QueueInterface:
    """Thin queue abstraction for future Celery/Redis migration."""

    def advance_status(self, package_id: int, next_status: str) -> bool:
        try:
            with SessionHelper.get_session() as db:
                status_ops = PackageStatusOperations(db.session)
                status = status_ops.get_by_package_id(package_id)
                if not status:
                    logger.warning(
                        f"advance_status: no PackageStatus for package_id={package_id}"
                    )
                    return False

                prev_status = status.status
                success = status_ops.update_status(package_id, next_status)
                if success:
                    db.commit()
                    logger.info(
                        f"Status advanced: package_id={package_id} {prev_status} -> {next_status}"
                    )
                    return True
                return False
        except Exception as e:
            logger.error(
                f"advance_status failed for package_id={package_id}: {str(e)}",
                exc_info=True,
            )
            with SessionHelper.get_session() as db:
                db.rollback()
            return False
