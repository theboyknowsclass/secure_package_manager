"""
Request model for managing package requests
"""

from datetime import datetime
from typing import Any

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base


class Request(Base):
    __tablename__ = "requests"

    id = Column(Integer, primary_key=True)
    application_name = Column(String(255), nullable=False)
    version = Column(String(100), nullable=False)
    requestor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    raw_request_blob = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    request_packages = relationship("RequestPackage", backref="request", lazy=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "application_name": self.application_name,
            "version": self.version,
            "requestor_id": self.requestor_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
