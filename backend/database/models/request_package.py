"""
RequestPackage model for linking requests to packages
"""

from typing import Any

from sqlalchemy import Column, Integer, String, ForeignKey

from .base import Base


class RequestPackage(Base):
    __tablename__ = "request_packages"

    request_id = Column(Integer, ForeignKey("requests.id"), primary_key=True)
    package_id = Column(Integer, ForeignKey("packages.id"), primary_key=True)
    package_type = Column(String(20), default="new", nullable=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "package_id": self.package_id,
            "package_type": self.package_type,
        }
