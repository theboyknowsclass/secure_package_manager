"""
Package model for managing npm packages
"""

from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship

from .base import Base


class Package(Base):
    __tablename__ = "packages"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    version = Column(String(100), nullable=False)
    npm_url = Column(String(500))
    local_path = Column(String(500))
    integrity = Column(String(255))
    license_identifier = Column(String(100))  # SPDX license identifier
    license_text = Column(Text)  # Full license text
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    request_packages = relationship("RequestPackage", backref="package", lazy=True)
    package_status = relationship("PackageStatus", backref="package", uselist=False, lazy=True)
    security_scans = relationship("SecurityScan", backref="package", lazy=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "npm_url": self.npm_url,
            "local_path": self.local_path,
            "integrity": self.integrity,
            "license_identifier": self.license_identifier,
            "license_text": self.license_text,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
