"""Flask-specific database utilities.

Provides Flask context managers and utilities for using pure SQLAlchemy
with Flask applications.
"""

import os
from contextlib import contextmanager
from typing import Generator

from .operations import OperationsFactory
from .service import DatabaseService


@contextmanager
def get_db_operations() -> Generator[dict, None, None]:
    """Context manager to get database operations for Flask requests.

    Usage:
        with get_db_operations() as ops:
            user = ops['user'].get_user_by_username("admin")
            ops['user'].create_user(...)
    """
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")

    db_service = DatabaseService(database_url)
    with db_service.get_session() as session:
        ops = OperationsFactory.create_all_operations(session)
        yield ops


def get_db_service() -> DatabaseService:
    """Get a DatabaseService instance for Flask requests."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")

    return DatabaseService(database_url)
