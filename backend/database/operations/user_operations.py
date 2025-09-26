"""Database operations for User entities."""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import User


class UserOperations:
    """Database operations for User entities."""

    def __init__(self, session: Session):
        """Initialize with a database session.

        Args:
            session: SQLAlchemy session for database operations
        """
        self.session = session

    def create(self, user: User) -> User:
        """Create a new user.

        Args:
            user: The user to create

        Returns:
            The created user (with ID populated)
        """
        self.session.add(user)
        self.session.flush()
        return user

    def update(self, user: User) -> User:
        """Update an existing user.

        Args:
            user: The user to update

        Returns:
            The updated user
        """
        self.session.flush()
        return user

    def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username.

        Args:
            username: The username to search for

        Returns:
            The user if found, None otherwise
        """
        stmt = select(User).where(User.username == username)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email.

        Args:
            email: The email to search for

        Returns:
            The user if found, None otherwise
        """
        stmt = select(User).where(User.email == email)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_role(self, role: str) -> List[User]:
        """Get users by role.

        Args:
            role: The role to filter by

        Returns:
            List of users with the specified role
        """
        stmt = select(User).where(User.role == role)
        return list(self.session.execute(stmt).scalars().all())

    def get_approvers(self) -> List[User]:
        """Get all users with approver or admin role.

        Returns:
            List of users who can approve packages
        """
        stmt = select(User).where(User.role.in_(["approver", "admin"]))
        return list(self.session.execute(stmt).scalars().all())

    def get_all(self) -> List[User]:
        """Get all users.

        Returns:
            List of all users
        """
        return list(self.session.query(User).all())

    def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID.

        Args:
            user_id: The ID of the user to retrieve

        Returns:
            The user if found, None otherwise
        """
        return self.session.get(User, user_id)

    def create_user(self, user_data: dict) -> User:
        """Create a new user.

        Args:
            user_data: Dictionary containing user data

        Returns:
            The created user
        """
        user = User(**user_data)
        self.session.add(user)
        self.session.flush()
        return user
