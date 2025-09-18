"""
Pure SQLAlchemy models - no Flask-SQLAlchemy dependencies
Converted from existing Flask-SQLAlchemy models
"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

# Create a declarative base for pure SQLAlchemy models
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(20), default="user", nullable=False)  # "user", "approver", "admin"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    requests = relationship("Request", backref="requestor", lazy=True)
    audit_logs = relationship("AuditLog", backref="user", lazy=True)
    supported_licenses = relationship("SupportedLicense", backref="creator", lazy=True)

    # Role helper methods
    def is_user(self) -> bool:
        return str(self.role) == "user"

    def is_approver(self) -> bool:
        return str(self.role) == "approver"

    def is_admin(self) -> bool:
        return str(self.role) == "admin"

    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission based on role hierarchy"""
        role_hierarchy = {
            "user": ["view_packages", "request_packages"],
            "approver": [
                "view_packages",
                "request_packages",
                "approve_packages",
                "view_requests",
            ],
            "admin": [
                "view_packages",
                "request_packages",
                "approve_packages",
                "view_requests",
                "manage_licenses",
                "manage_users",
                "view_admin",
            ],
        }
        return permission in role_hierarchy.get(self.role, [])

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


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


class PackageStatus(Base):
    __tablename__ = "package_status"

    package_id = Column(Integer, ForeignKey("packages.id"), primary_key=True)
    status = Column(String(50), default="Submitted", nullable=False)
    file_size = Column(BigInteger)
    checksum = Column(String(255))
    license_score = Column(Integer)
    security_score = Column(Integer)
    security_scan_status = Column(
        String(50), default="pending", nullable=False
    )  # pending, running, completed, failed, skipped
    license_status = Column(String(20))  # Primary license status calculated from supported_licenses table
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # User who approved the package
    rejector_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # User who rejected the package
    published_at = Column(DateTime, nullable=True)  # Timestamp when package was successfully published
    publish_status = Column(
        String(20), default="pending", nullable=False
    )  # Publishing status: pending, publishing, published, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_id": self.package_id,
            "status": self.status,
            "file_size": self.file_size,
            "checksum": self.checksum,
            "license_score": self.license_score,
            "security_score": self.security_score,
            "security_scan_status": self.security_scan_status,
            "license_status": self.license_status,
            "approver_id": self.approver_id,
            "rejector_id": self.rejector_id,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "publish_status": self.publish_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def is_processing(self) -> bool:
        """Check if package is in a processing state"""
        processing_statuses = {
            "Submitted",
            "Parsed",
            "Checking Licence",
            "Downloading",
            "Security Scanning",
        }
        return self.status in processing_statuses

    def is_completed_processing(self) -> bool:
        """Check if package has completed all processing steps"""
        completed_statuses = {
            "Licence Checked",
            "Downloaded",
            "Security Scanned",
            "Pending Approval",
            "Approved",
            "Rejected",
        }
        return self.status in completed_statuses

    def is_final_status(self) -> bool:
        """Check if package is in a final status (approved or rejected)"""
        return self.status in {"Approved", "Rejected"}

    def get_processing_stage(self) -> str:
        """Get the current processing stage for display purposes"""
        stage_mapping = {
            "Submitted": "Submitted",
            "Parsed": "Parsed",
            "Checking Licence": "License Validation",
            "Licence Checked": "License Complete",
            "Downloading": "Downloading Package",
            "Downloaded": "Download Complete",
            "Security Scanning": "Security Scan",
            "Security Scanned": "Security Complete",
            "Pending Approval": "Awaiting Approval",
            "Approved": "Approved",
            "Rejected": "Rejected",
        }
        return stage_mapping.get(self.status, "Unknown")


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


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(Integer)
    details = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "details": self.details,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
