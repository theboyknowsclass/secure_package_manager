"""PackageStatus model for tracking package processing status."""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class PackageStatus(Base):
    __tablename__ = "package_status"

    CHECKING_LICENCE_STR = "Checking Licence"
    PARSE_FAILED_STR = "Parse Failed"
    LICENCE_CHECK_FAILED_STR = "Licence Check Failed"
    DOWNLOAD_FAILED_STR = "Download Failed"
    SECURITY_SCAN_FAILED_STR = "Security Scan Failed"

    package_id: Mapped[int] = mapped_column(Integer, ForeignKey("packages.id"), primary_key=True)
    status: Mapped[str] = mapped_column(String(50), default=CHECKING_LICENCE_STR, nullable=False)
    file_size: Mapped[Optional[int]] = mapped_column(BigInteger)
    checksum: Mapped[Optional[str]] = mapped_column(String(255))
    cache_path: Mapped[Optional[str]] = mapped_column(String(500))  # Actual cache directory path where package is stored
    license_score: Mapped[Optional[int]] = mapped_column(Integer)
    security_score: Mapped[Optional[int]] = mapped_column(Integer)
    security_scan_status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)  # pending, running, completed, failed, skipped
    license_status: Mapped[Optional[str]] = mapped_column(String(20))  # Primary license status calculated from supported_licenses table
    approver_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)  # User who approved the package
    rejector_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)  # User who rejected the package
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # Timestamp when package was successfully published
    publish_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)  # Publishing status: pending, publishing, published, failed
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_id": self.package_id,
            "status": self.status,
            "file_size": self.file_size,
            "checksum": self.checksum,
            "cache_path": self.cache_path,
            "license_score": self.license_score,
            "security_score": self.security_score,
            "security_scan_status": self.security_scan_status,
            "license_status": self.license_status,
            "approver_id": self.approver_id,
            "rejector_id": self.rejector_id,
            "published_at": (self.published_at.isoformat() if self.published_at else None),
            "publish_status": self.publish_status,
            "created_at": (self.created_at.isoformat() if self.created_at else None),
            "updated_at": (self.updated_at.isoformat() if self.updated_at else None),
        }

    def is_processing(self) -> bool:
        """Check if package is in a processing state."""
        processing_statuses = {
            self.CHECKING_LICENCE_STR,
            "Downloading",
            "Security Scanning",
        }
        return self.status in processing_statuses

    def is_completed_processing(self) -> bool:
        """Check if package has completed all processing steps."""
        completed_statuses = {
            "Licence Checked",
            "Downloaded",
            "Security Scanned",
            "Pending Approval",
            "Approved",
            "Rejected",
            # Failed states
            self.PARSE_FAILED_STR,
            self.LICENCE_CHECK_FAILED_STR,
            self.DOWNLOAD_FAILED_STR,
            self.SECURITY_SCAN_FAILED_STR,
        }
        return self.status in completed_statuses

    def is_final_status(self) -> bool:
        """Check if package is in a final status (approved, rejected, or failed)"""
        return self.status in {
            "Approved",
            "Rejected",
            self.PARSE_FAILED_STR,
            self.LICENCE_CHECK_FAILED_STR,
            self.DOWNLOAD_FAILED_STR,
            self.SECURITY_SCAN_FAILED_STR,
        }

    def get_processing_stage(self) -> str:
        """Get the current processing stage for display purposes."""
        stage_mapping = {
            self.CHECKING_LICENCE_STR: "License Validation",
            "Licence Checked": "License Complete",
            "Downloading": "Downloading Package",
            "Downloaded": "Download Complete",
            "Security Scanning": "Security Scan",
            "Security Scanned": "Security Complete",
            "Pending Approval": "Awaiting Approval",
            "Approved": "Approved",
            "Rejected": "Rejected",
            # Failed states
            self.PARSE_FAILED_STR: self.PARSE_FAILED_STR,
            self.LICENCE_CHECK_FAILED_STR: self.LICENCE_CHECK_FAILED_STR,
            self.DOWNLOAD_FAILED_STR: self.DOWNLOAD_FAILED_STR,
            self.SECURITY_SCAN_FAILED_STR: self.SECURITY_SCAN_FAILED_STR,
        }
        return stage_mapping.get(self.status or "", "Unknown")
