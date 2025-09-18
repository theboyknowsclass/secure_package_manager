"""
SecurityScan model for storing security scan results
"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String

from .base import Base


class SecurityScan(Base):
    __tablename__ = "security_scans"

    id = Column(Integer, primary_key=True)
    package_id = Column(Integer, ForeignKey("packages.id", ondelete="CASCADE"), nullable=False)
    scan_type = Column(String(50), default="trivy", nullable=False)  # trivy, snyk, npm_audit
    scan_result = Column(JSON)  # Store the full Trivy scan result
    critical_count = Column(Integer, default=0)
    high_count = Column(Integer, default=0)
    medium_count = Column(Integer, default=0)
    low_count = Column(Integer, default=0)
    info_count = Column(Integer, default=0)
    scan_duration_ms = Column(Integer)  # Scan duration in milliseconds
    trivy_version = Column(String(50))  # Version of Trivy used for the scan
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

    def get_total_vulnerabilities(self) -> int:
        """Calculate total vulnerability count from granular counts"""
        return self.critical_count + self.high_count + self.medium_count + self.low_count + self.info_count

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "package_id": self.package_id,
            "scan_type": self.scan_type,
            "scan_result": self.scan_result,
            "vulnerability_count": self.get_total_vulnerabilities(),  # Calculate from granular counts
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
            "info_count": self.info_count,
            "scan_duration_ms": self.scan_duration_ms,
            "trivy_version": self.trivy_version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": (self.completed_at.isoformat() if self.completed_at else None),
        }
