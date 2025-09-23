"""
Database Service - Pure SQLAlchemy implementation
No Flask dependencies, can be used by workers independently
"""

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service for managing database connections and sessions using pure
    SQLAlchemy."""

    def __init__(self, database_url: str, echo: bool = False):
        """Initialize the database service.

        Args:
            database_url: Database connection URL
            echo: Whether to echo SQL statements (for debugging)
        """
        self.database_url = database_url
        self.echo = echo
        self._engine = None
        self._SessionLocal = None
        self._initialize_engine()

    def _initialize_engine(self) -> None:
        """Initialize the SQLAlchemy engine and session factory."""
        try:
            # Create engine with appropriate configuration
            engine_kwargs = {
                "echo": self.echo,
                "pool_pre_ping": True,  # Verify connections before use
                "pool_recycle": 3600,  # Recycle connections every hour
                "pool_size": 5,  # Number of connections to maintain in pool
                "max_overflow": 10,  # Additional connections beyond pool_size
                "pool_timeout": 30,  # Seconds to wait for connection from pool
            }

            # Use StaticPool for SQLite, regular pool for PostgreSQL
            if self.database_url.startswith("sqlite"):
                engine_kwargs["poolclass"] = StaticPool
                engine_kwargs["connect_args"] = {"check_same_thread": False}

            self._engine = create_engine(self.database_url, **engine_kwargs)
            self._SessionLocal = sessionmaker(bind=self._engine)

            logger.debug(
                f"Database service initialized with URL: {self._mask_database_url()}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize database service: {str(e)}")
            raise

    def _mask_database_url(self) -> str:
        """Mask sensitive information in database URL for logging."""
        if "@" in self.database_url:
            # Mask password in URL like postgresql://user:password@host/db
            parts = self.database_url.split("@")
            if len(parts) == 2:
                user_part = parts[0]
                if ":" in user_part:
                    user, _ = user_part.rsplit(":", 1)
                    masked_url = f"{user}:***@{parts[1]}"
                    return masked_url
        return self.database_url

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session with automatic cleanup.

        Usage:
            with db_service.get_session() as session:
                result = session.query(Model).all()
                session.commit()
        """
        session = self._SessionLocal()
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {str(e)}")
            session.rollback()
            raise
        finally:
            session.close()

    def test_connection(self) -> bool:
        """Test the database connection.

        Returns:
            True if connection is successful, False otherwise
        """
        try:
            with self.get_session() as session:
                from sqlalchemy import text

                session.execute(text("SELECT 1"))
            logger.info("Database connection test successful")
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {str(e)}")
            return False

    def get_engine(self):
        """Get the SQLAlchemy engine (for advanced usage)"""
        return self._engine

    def close(self) -> None:
        """Close the database engine and cleanup resources."""
        if self._engine:
            self._engine.dispose()
            logger.info("Database service closed")
