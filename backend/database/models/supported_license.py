"""
SupportedLicense model for managing license policies
"""

from datetime import datetime
from typing import Any

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey

from .base import Base


class SupportedLicense(Base):
    __tablename__ = "supported_licenses"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    identifier = Column(String(100), unique=True, nullable=False)  # SPDX identifier
    status = Column(String(20), default="allowed")  # 'always_allowed', 'allowed', 'avoid', 'blocked'
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "identifier": self.identifier,
            "status": self.status,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
