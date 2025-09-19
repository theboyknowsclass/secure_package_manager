"""
Lightweight session helper for database operations.

This provides a clean, minimal interface for database operations without
the overhead of the full CompositeOperations class.
"""

import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy.orm import Session

from .service import DatabaseService


class SessionHelper:
    """Lightweight helper for database session management.
    
    This provides a minimal interface for direct session operations,
    avoiding the overhead of creating all entity operation instances.
    """
    
    def __init__(self, session: Session):
        """Initialize with a database session.
        
        Args:
            session: SQLAlchemy session for database operations
        """
        self.session = session
    
    def add(self, entity):
        """Add an entity to the session."""
        return self.session.add(entity)
    
    def delete(self, entity):
        """Delete an entity from the session."""
        return self.session.delete(entity)
    
    def merge(self, entity):
        """Merge an entity into the session."""
        return self.session.merge(entity)
    
    def query(self, *args, **kwargs):
        """Query the session."""
        return self.session.query(*args, **kwargs)
    
    def commit(self) -> None:
        """Commit the current transaction."""
        self.session.commit()
    
    def rollback(self) -> None:
        """Rollback the current transaction."""
        self.session.rollback()
    
    def flush(self) -> None:
        """Flush pending changes to the database without committing."""
        self.session.flush()
    
    def close(self) -> None:
        """Close the session."""
        self.session.close()
    
    @classmethod
    @contextmanager
    def get_session(cls) -> Generator['SessionHelper', None, None]:
        """Get a database session with automatic cleanup.
        
        This is the lightweight alternative to CompositeOperations.get_operations().
        
        Usage:
            with SessionHelper.get_session() as db:
                user = User(name="admin")
                db.add(user)
                db.commit()
                
                # Or use with entity operations:
                from database.operations import UserOperations
                user_ops = UserOperations(db.session)
                user = user_ops.get_by_username("admin")
        """
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is required")

        db_service = DatabaseService(database_url)
        with db_service.get_session() as session:
            session_helper = cls(session)
            try:
                yield session_helper
            finally:
                # Session cleanup is handled by DatabaseService.get_session()
                pass
