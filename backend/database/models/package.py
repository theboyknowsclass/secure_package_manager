"""Package model for managing npm packages."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .package_status import PackageStatus
    from .request_package import RequestPackage
    from .security_scan import SecurityScan


class Package(Base):
    __tablename__ = "packages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(100), nullable=False)
    npm_url: Mapped[Optional[str]] = mapped_column(String(500))  # URL from package-lock.json
    local_path: Mapped[Optional[str]] = mapped_column(String(500))  # Input field from package-lock.json (readonly)
    integrity: Mapped[Optional[str]] = mapped_column(String(255))  # Integrity hash from package-lock.json
    license_identifier: Mapped[Optional[str]] = mapped_column(String(100))  # SPDX license identifier from package-lock.json
    license_text: Mapped[Optional[str]] = mapped_column(Text)  # Full license text from package-lock.json
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    request_packages: Mapped[List["RequestPackage"]] = relationship("RequestPackage", back_populates="package", lazy=True)
    package_status: Mapped["PackageStatus"] = relationship("PackageStatus", backref="package", uselist=False, lazy=True)
    security_scans: Mapped[List["SecurityScan"]] = relationship("SecurityScan", backref="package", lazy=True)

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
            "created_at": (self.created_at.isoformat() if self.created_at else None),
        }
