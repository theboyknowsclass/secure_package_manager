from datetime import datetime
from typing import Any

from flask_sqlalchemy import SQLAlchemy

# Create a SQLAlchemy instance that will be initialized by the app
db = SQLAlchemy()

# Import the pure SQLAlchemy models to inherit from
from database.models import (
    User as BaseUser,
    Request as BaseRequest, 
    Package as BasePackage,
    RequestPackage as BaseRequestPackage,
    PackageStatus as BasePackageStatus,
    SecurityScan as BaseSecurityScan,
    SupportedLicense as BaseSupportedLicense,
    AuditLog as BaseAuditLog
)


# Flask-SQLAlchemy models that inherit from pure SQLAlchemy models
class User(BaseUser, db.Model):  # type: ignore[misc]
    __tablename__ = "users"

    # Relationships
    requests = db.relationship("Request", backref="requestor", lazy=True)
    audit_logs = db.relationship("AuditLog", backref="user", lazy=True)
    supported_licenses = db.relationship("SupportedLicense", backref="creator", lazy=True)

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


class Request(BaseRequest, db.Model):  # type: ignore[misc]
    __tablename__ = "requests"

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


class Package(BasePackage, db.Model):  # type: ignore[misc]
    __tablename__ = "packages"

    # Relationships
    request_packages = db.relationship("RequestPackage", backref="package", lazy=True)
    package_status = db.relationship("PackageStatus", backref="package", uselist=False, lazy=True)
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


class RequestPackage(BaseRequestPackage, db.Model):  # type: ignore[misc]
    __tablename__ = "request_packages"

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "package_id": self.package_id,
            "package_type": self.package_type,
        }


class PackageStatus(BasePackageStatus, db.Model):  # type: ignore[misc]
    __tablename__ = "package_status"

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


class SecurityScan(BaseSecurityScan, db.Model):  # type: ignore[misc]
    __tablename__ = "security_scans"

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


class SupportedLicense(BaseSupportedLicense, db.Model):  # type: ignore[misc]
    __tablename__ = "supported_licenses"

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


class AuditLog(BaseAuditLog, db.Model):  # type: ignore[misc]
    __tablename__ = "audit_log"

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
