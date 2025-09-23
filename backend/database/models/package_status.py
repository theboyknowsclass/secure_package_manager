"""PackageStatus model for tracking package processing status."""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)

from .base import Base


class PackageStatus(Base):
    __tablename__ = "package_status"

    package_id = Column(Integer, ForeignKey("packages.id"), primary_key=True)
    status = Column(String(50), default="Checking Licence", nullable=False)
    file_size = Column(BigInteger)
    checksum = Column(String(255))
    cache_path = Column(
        String(500)
    )  # Actual cache directory path where package is stored
    license_score = Column(Integer)
    security_score = Column(Integer)
    security_scan_status = Column(
        String(50), default="pending", nullable=False
    )  # pending, running, completed, failed, skipped
    license_status = Column(
        String(20)
    )  # Primary license status calculated from supported_licenses table
    approver_id = Column(
        Integer, ForeignKey("users.id"), nullable=True
    )  # User who approved the package
    rejector_id = Column(
        Integer, ForeignKey("users.id"), nullable=True
    )  # User who rejected the package
    published_at = Column(
        DateTime, nullable=True
    )  # Timestamp when package was successfully published
    publish_status = Column(
        String(20), default="pending", nullable=False
    )  # Publishing status: pending, publishing, published, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

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
            "published_at": (
                self.published_at.isoformat() if self.published_at else None
            ),
            "publish_status": self.publish_status,
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
            "updated_at": (
                self.updated_at.isoformat() if self.updated_at else None
            ),
        }

    def is_processing(self) -> bool:
        """Check if package is in a processing state."""
        processing_statuses = {
            "Checking Licence",
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
            "Parse Failed",
            "Licence Check Failed",
            "Download Failed",
            "Security Scan Failed",
        }
        return self.status in completed_statuses

    def is_final_status(self) -> bool:
        """Check if package is in a final status (approved, rejected, or failed)"""
        return self.status in {
            "Approved",
            "Rejected",
            "Parse Failed",
            "Licence Check Failed",
            "Download Failed",
            "Security Scan Failed",
        }

    def get_processing_stage(self) -> str:
        """Get the current processing stage for display purposes."""
        stage_mapping = {
            "Checking Licence": "License Validation",
            "Licence Checked": "License Complete",
            "Downloading": "Downloading Package",
            "Downloaded": "Download Complete",
            "Security Scanning": "Security Scan",
            "Security Scanned": "Security Complete",
            "Pending Approval": "Awaiting Approval",
            "Approved": "Approved",
            "Rejected": "Rejected",
            # Failed states
            "Parse Failed": "Parse Failed",
            "Licence Check Failed": "License Check Failed",
            "Download Failed": "Download Failed",
            "Security Scan Failed": "Security Scan Failed",
        }
        return stage_mapping.get(self.status, "Unknown")
