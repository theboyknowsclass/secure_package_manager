"""Request model for managing package requests."""

from __future__ import annotations

from datetime import datetime
from typing import Any, List, TYPE_CHECKING

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, relationship

from .base import Base

if TYPE_CHECKING:
    from .request_package import RequestPackage
    from .user import User


class Request(Base):
    __tablename__ = "requests"

    id = Column(Integer, primary_key=True)
    application_name = Column(String(255), nullable=False)
    version = Column(String(100), nullable=False)
    requestor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    raw_request_blob = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    request_packages: Mapped[List["RequestPackage"]] = relationship(
        "RequestPackage", back_populates="request", lazy=True
    )
    requestor: Mapped["User"] = relationship("User", back_populates="requests", lazy=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "application_name": self.application_name,
            "version": self.version,
            "requestor_id": self.requestor_id,
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
        }
