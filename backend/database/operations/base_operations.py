"""Base operations class for all entity-specific database operations."""

from abc import ABC
from typing import Any, List, Optional, Type, TypeVar

from sqlalchemy.orm import Session

T = TypeVar("T")


class BaseOperations(ABC):
    """Base class for all entity-specific database operations.

    Provides common CRUD operations that can be used by all entity-
    specific operations classes. This ensures consistency across all
    database operations and reduces code duplication.
    """

    def __init__(self, session: Session):
        """Initialize with a database session.

        Args:
            session: SQLAlchemy session for database operations
        """
        self.session = session

    def get_by_id(self, model_class: Type[T], entity_id: int) -> Optional[T]:
        """Get entity by ID.

        Args:
            model_class: The SQLAlchemy model class
            entity_id: The ID of the entity to retrieve

        Returns:
            The entity if found, None otherwise
        """
        return self.session.get(model_class, entity_id)

    def get_all(self, model_class: Type[T]) -> List[T]:
        """Get all entities of a type.

        Args:
            model_class: The SQLAlchemy model class

        Returns:
            List of all entities of the specified type
        """
        return self.session.query(model_class).all()

    def create(self, entity: T) -> T:
        """Create a new entity.

        Args:
            entity: The entity to create

        Returns:
            The created entity (with ID populated)
        """
        self.session.add(entity)
        self.session.flush()  # Get the ID without committing
        return entity

    def update(self, entity: T) -> T:
        """Update an existing entity.

        Args:
            entity: The entity to update

        Returns:
            The updated entity
        """
        self.session.flush()
        return entity

    def delete(self, entity: T) -> None:
        """Delete an entity.

        Args:
            entity: The entity to delete
        """
        self.session.delete(entity)

    def commit(self) -> None:
        """Commit the current transaction."""
        self.session.commit()

    def rollback(self) -> None:
        """Rollback the current transaction."""
        self.session.rollback()

    def flush(self) -> None:
        """Flush pending changes to the database without committing."""
        self.session.flush()
