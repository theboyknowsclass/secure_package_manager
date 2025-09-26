"""RequestPackage model for linking requests to packages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, relationship

from .base import Base

if TYPE_CHECKING:
    from .package import Package
    from .request import Request


class RequestPackage(Base):
    __tablename__ = "request_packages"

    request_id = Column(Integer, ForeignKey("requests.id"), primary_key=True)
    package_id = Column(Integer, ForeignKey("packages.id"), primary_key=True)
    package_type = Column(String(20), default="new", nullable=False)

    # Relationships
    request: Mapped["Request"] = relationship("Request", back_populates="request_packages")
    package: Mapped["Package"] = relationship("Package", back_populates="request_packages")

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "package_id": self.package_id,
            "package_type": self.package_type,
        }
