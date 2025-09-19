"""User model for managing application users."""

from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from .base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(
        String(20), default="user", nullable=False
    )  # "user", "approver", "admin"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    requests = relationship("Request", backref="requestor", lazy=True)
    audit_logs = relationship("AuditLog", backref="user", lazy=True)
    supported_licenses = relationship(
        "SupportedLicense", backref="creator", lazy=True
    )

    # Role helper methods
    def is_user(self) -> bool:
        return str(self.role) == "user"

    def is_approver(self) -> bool:
        return str(self.role) == "approver"

    def is_admin(self) -> bool:
        return str(self.role) == "admin"

    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission based on role hierarchy."""
        role_hierarchy = {
            "user": ["view_packages", "request_packages"],
            "approver": [
                "view_packages",
                "request_packages",
                "approve_packages",
                "view_requests",
            ],
            "admin": [
                "view_packages",
                "request_packages",
                "approve_packages",
                "view_requests",
                "manage_licenses",
                "manage_users",
                "view_admin",
            ],
        }
        return permission in role_hierarchy.get(self.role, [])

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
            "updated_at": (
                self.updated_at.isoformat() if self.updated_at else None
            ),
        }
