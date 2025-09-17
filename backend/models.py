from datetime import datetime
from typing import Any

from flask_sqlalchemy import SQLAlchemy

# Create a SQLAlchemy instance that will be initialized by the app
db = SQLAlchemy()


class User(db.Model):  # type: ignore[misc]
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    full_name = db.Column(db.String(255), nullable=False)
    role = db.Column(
        db.String(20), default="user", nullable=False
    )  # 'user', 'approver', 'admin'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    requests = db.relationship("Request", backref="requestor", lazy=True)
    audit_logs = db.relationship("AuditLog", backref="user", lazy=True)
    supported_licenses = db.relationship(
        "SupportedLicense", backref="creator", lazy=True
    )

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


class Request(db.Model):  # type: ignore[misc]
    __tablename__ = "requests"

    id = db.Column(db.Integer, primary_key=True)
    application_name = db.Column(db.String(255), nullable=False)
    version = db.Column(db.String(100), nullable=False)
    requestor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    package_lock_file = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    request_packages = db.relationship("RequestPackage", backref="request", lazy=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "application_name": self.application_name,
            "version": self.version,
            "requestor_id": self.requestor_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Package(db.Model):  # type: ignore[misc]
    __tablename__ = "packages"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    version = db.Column(db.String(100), nullable=False)
    npm_url = db.Column(db.String(500))
    local_path = db.Column(db.String(500))
    integrity = db.Column(db.String(255))
    license_identifier = db.Column(db.String(100))  # SPDX license identifier
    license_text = db.Column(db.Text)  # Full license text
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    request_packages = db.relationship("RequestPackage", backref="package", lazy=True)
    package_status = db.relationship(
        "PackageStatus", backref="package", uselist=False, lazy=True
    )
    security_scans = db.relationship("SecurityScan", backref="package", lazy=True)

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


class RequestPackage(db.Model):  # type: ignore[misc]
    __tablename__ = "request_packages"

    request_id = db.Column(db.Integer, db.ForeignKey("requests.id"), primary_key=True)
    package_id = db.Column(db.Integer, db.ForeignKey("packages.id"), primary_key=True)
    package_type = db.Column(db.String(20), default="new", nullable=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "package_id": self.package_id,
            "package_type": self.package_type,
        }


class PackageStatus(db.Model):  # type: ignore[misc]
    __tablename__ = "package_status"

    package_id = db.Column(db.Integer, db.ForeignKey("packages.id"), primary_key=True)
    status = db.Column(db.String(50), default="Requested", nullable=False)
    file_size = db.Column(db.BigInteger)
    checksum = db.Column(db.String(255))
    license_score = db.Column(db.Integer)
    security_score = db.Column(db.Integer)
    security_scan_status = db.Column(
        db.String(50), default="pending", nullable=False
    )  # pending, running, completed, failed, skipped
    license_status = db.Column(db.String(20))  # Primary license status calculated from supported_licenses table
    approver_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)  # User who approved the package
    rejector_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)  # User who rejected the package
    published_at = db.Column(db.DateTime, nullable=True)  # Timestamp when package was successfully published
    publish_status = db.Column(db.String(20), default="pending", nullable=False)  # Publishing status: pending, publishing, published, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

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
            "Requested", "Checking Licence", "Downloading", "Security Scanning"
        }
        return self.status in processing_statuses

    def is_completed_processing(self) -> bool:
        """Check if package has completed all processing steps"""
        completed_statuses = {
            "Licence Checked", "Downloaded", "Security Scanned", "Pending Approval", "Approved", "Rejected"
        }
        return self.status in completed_statuses

    def is_final_status(self) -> bool:
        """Check if package is in a final status (approved or rejected)"""
        return self.status in {"Approved", "Rejected"}

    def get_processing_stage(self) -> str:
        """Get the current processing stage for display purposes"""
        stage_mapping = {
            "Requested": "Initial",
            "Checking Licence": "License Validation",
            "Licence Checked": "License Complete",
            "Downloading": "Downloading Package",
            "Downloaded": "Download Complete",
            "Security Scanning": "Security Scan",
            "Security Scanned": "Security Complete",
            "Pending Approval": "Awaiting Approval",
            "Approved": "Approved",
            "Rejected": "Rejected"
        }
        return stage_mapping.get(self.status, "Unknown")


class SecurityScan(db.Model):  # type: ignore[misc]
    __tablename__ = "security_scans"

    id = db.Column(db.Integer, primary_key=True)
    package_id = db.Column(
        db.Integer, db.ForeignKey("packages.id", ondelete="CASCADE"), nullable=False
    )
    scan_type = db.Column(
        db.String(50), default="trivy", nullable=False
    )  # trivy, snyk, npm_audit
    scan_result = db.Column(db.JSON)  # Store the full Trivy scan result
    critical_count = db.Column(db.Integer, default=0)
    high_count = db.Column(db.Integer, default=0)
    medium_count = db.Column(db.Integer, default=0)
    low_count = db.Column(db.Integer, default=0)
    info_count = db.Column(db.Integer, default=0)
    scan_duration_ms = db.Column(db.Integer)  # Scan duration in milliseconds
    trivy_version = db.Column(db.String(50))  # Version of Trivy used for the scan
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

    def get_total_vulnerabilities(self) -> int:
        """Calculate total vulnerability count from granular counts"""
        return (
            self.critical_count + 
            self.high_count + 
            self.medium_count + 
            self.low_count + 
            self.info_count
        )

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
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
        }


class SupportedLicense(db.Model):  # type: ignore[misc]
    __tablename__ = "supported_licenses"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    identifier = db.Column(
        db.String(100), unique=True, nullable=False
    )  # SPDX identifier
    status = db.Column(
        db.String(20), default="allowed"
    )  # 'always_allowed', 'allowed', 'avoid', 'blocked'
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

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


class AuditLog(db.Model):  # type: ignore[misc]
    __tablename__ = "audit_log"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    resource_type = db.Column(db.String(100), nullable=False)
    resource_id = db.Column(db.Integer)
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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
