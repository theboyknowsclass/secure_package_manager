"""Database operations for User entities."""

from typing import List, Optional, Type

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import User
from .base_operations import BaseOperations


class UserOperations(BaseOperations):
    """Database operations for User entities."""

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

    def get_all(self, model_class: Type[User]) -> List[User]:
        """Get all users.

        Returns:
            List of all users
        """
        return super().get_all(User)

    def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID.

        Args:
            user_id: The ID of the user

        Returns:
            The user if found, None otherwise
        """
        return super().get_by_id(User, user_id)

    def create_user(self, user_data: dict) -> User:
        """Create a new user.

        Args:
            user_data: Dictionary containing user data

        Returns:
            The created user
        """
        user = User(**user_data)
        return super().create(user)
