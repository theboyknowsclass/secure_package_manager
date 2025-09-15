from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

# Create a SQLAlchemy instance that will be initialized by the app
db = SQLAlchemy()


class RepositoryConfig(db.Model):
    __tablename__ = "repository_config"

    id = db.Column(db.Integer, primary_key=True)
    config_key = db.Column(db.String(100), unique=True, nullable=False)
    config_value = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def to_dict(self):
        return {
            "id": self.id,
            "config_key": self.config_key,
            "config_value": self.config_value,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @staticmethod
    def get_config_value(key, default=None):
        """Get a configuration value by key"""
        config = RepositoryConfig.query.filter_by(config_key=key).first()
        return config.config_value if config else default

    @staticmethod
    def set_config_value(key, value, description=None):
        """Set a configuration value by key"""
        config = RepositoryConfig.query.filter_by(config_key=key).first()
        if config:
            config.config_value = value
            if description:
                config.description = description
            config.updated_at = datetime.utcnow()
        else:
            config = RepositoryConfig(
                config_key=key, config_value=value, description=description
            )
            db.session.add(config)
        db.session.commit()
        return config


class User(db.Model):
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
    applications = db.relationship("Application", backref="creator", lazy=True)
    package_requests = db.relationship("PackageRequest", backref="requestor", lazy=True)
    audit_logs = db.relationship("AuditLog", backref="user", lazy=True)
    supported_licenses = db.relationship(
        "SupportedLicense", backref="creator", lazy=True
    )

    # Role helper methods
    def is_user(self):
        return self.role == "user"

    def is_approver(self):
        return self.role == "approver"

    def is_admin(self):
        return self.role == "admin"

    def has_permission(self, permission):
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

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Application(db.Model):
    __tablename__ = "applications"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    version = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    package_requests = db.relationship(
        "PackageRequest", backref="application", lazy=True
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SupportedLicense(db.Model):
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

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "identifier": self.identifier,
            "status": self.status,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class PackageRequest(db.Model):
    __tablename__ = "package_requests"

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(
        db.Integer, db.ForeignKey("applications.id"), nullable=False
    )
    requestor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    package_lock_file = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default="requested")
    total_packages = db.Column(db.Integer, default=0)
    validated_packages = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    packages = db.relationship("Package", backref="package_request", lazy=True)
    package_references = db.relationship(
        "PackageReference", backref="package_request", lazy=True
    )

    def to_dict(self):
        return {
            "id": self.id,
            "application_id": self.application_id,
            "requestor_id": self.requestor_id,
            "status": self.status,
            "total_packages": self.total_packages,
            "validated_packages": self.validated_packages,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Package(db.Model):
    __tablename__ = "packages"

    id = db.Column(db.Integer, primary_key=True)
    package_request_id = db.Column(
        db.Integer, db.ForeignKey("package_requests.id"), nullable=False
    )
    name = db.Column(db.String(255), nullable=False)
    version = db.Column(db.String(100), nullable=False)
    npm_url = db.Column(db.String(500))
    local_path = db.Column(db.String(500))
    file_size = db.Column(db.BigInteger)
    checksum = db.Column(db.String(255))
    license_identifier = db.Column(db.String(100))  # SPDX license identifier
    license_text = db.Column(db.Text)  # Full license text
    status = db.Column(db.String(50), default="requested")
    validation_errors = db.Column(db.ARRAY(db.String))
    security_score = db.Column(db.Integer)
    license_score = db.Column(db.Integer)  # License compliance score
    security_scan_status = db.Column(
        db.String(50), default="pending"
    )  # pending, scanning, completed, failed, skipped
    vulnerability_count = db.Column(db.Integer, default=0)
    critical_vulnerabilities = db.Column(db.Integer, default=0)
    high_vulnerabilities = db.Column(db.Integer, default=0)
    medium_vulnerabilities = db.Column(db.Integer, default=0)
    low_vulnerabilities = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    validations = db.relationship("PackageValidation", backref="package", lazy=True)
    security_scans = db.relationship("SecurityScan", backref="package", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "package_request_id": self.package_request_id,
            "name": self.name,
            "version": self.version,
            "npm_url": self.npm_url,
            "local_path": self.local_path,
            "file_size": self.file_size,
            "checksum": self.checksum,
            "license_identifier": self.license_identifier,
            "license_text": self.license_text,
            "status": self.status,
            "validation_errors": self.validation_errors or [],
            "security_score": self.security_score,
            "license_score": self.license_score,
            "security_scan_status": self.security_scan_status,
            "vulnerability_count": self.vulnerability_count,
            "critical_vulnerabilities": self.critical_vulnerabilities,
            "high_vulnerabilities": self.high_vulnerabilities,
            "medium_vulnerabilities": self.medium_vulnerabilities,
            "low_vulnerabilities": self.low_vulnerabilities,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class PackageReference(db.Model):
    __tablename__ = "package_references"

    id = db.Column(db.Integer, primary_key=True)
    package_request_id = db.Column(
        db.Integer, db.ForeignKey("package_requests.id"), nullable=False
    )
    name = db.Column(db.String(255), nullable=False)
    version = db.Column(db.String(100), nullable=False)
    npm_url = db.Column(db.String(500))
    integrity = db.Column(db.String(255))
    status = db.Column(
        db.String(50), default="referenced"
    )  # referenced, already_validated, needs_validation
    existing_package_id = db.Column(
        db.Integer, db.ForeignKey("packages.id"), nullable=True
    )  # If already exists
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    existing_package = db.relationship("Package", foreign_keys=[existing_package_id])

    def to_dict(self):
        return {
            "id": self.id,
            "package_request_id": self.package_request_id,
            "name": self.name,
            "version": self.version,
            "npm_url": self.npm_url,
            "integrity": self.integrity,
            "status": self.status,
            "existing_package_id": self.existing_package_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PackageValidation(db.Model):
    __tablename__ = "package_validations"

    id = db.Column(db.Integer, primary_key=True)
    package_id = db.Column(db.Integer, db.ForeignKey("packages.id"), nullable=False)
    validation_type = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "package_id": self.package_id,
            "validation_type": self.validation_type,
            "status": self.status,
            "details": self.details,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AuditLog(db.Model):
    __tablename__ = "audit_log"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    resource_type = db.Column(db.String(100), nullable=False)
    resource_id = db.Column(db.Integer)
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "details": self.details,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class SecurityScan(db.Model):
    __tablename__ = "security_scans"

    id = db.Column(db.Integer, primary_key=True)
    package_id = db.Column(
        db.Integer, db.ForeignKey("packages.id", ondelete="CASCADE"), nullable=False
    )
    scan_type = db.Column(
        db.String(50), default="trivy", nullable=False
    )  # trivy, snyk, npm_audit
    status = db.Column(
        db.String(50), default="pending", nullable=False
    )  # pending, running, completed, failed, skipped
    scan_result = db.Column(db.JSON)  # Store the full Trivy scan result
    vulnerability_count = db.Column(db.Integer, default=0)
    critical_count = db.Column(db.Integer, default=0)
    high_count = db.Column(db.Integer, default=0)
    medium_count = db.Column(db.Integer, default=0)
    low_count = db.Column(db.Integer, default=0)
    info_count = db.Column(db.Integer, default=0)
    scan_duration_ms = db.Column(db.Integer)  # Scan duration in milliseconds
    trivy_version = db.Column(db.String(50))  # Version of Trivy used for the scan
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    completed_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            "id": self.id,
            "package_id": self.package_id,
            "scan_type": self.scan_type,
            "status": self.status,
            "scan_result": self.scan_result,
            "vulnerability_count": self.vulnerability_count,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
            "info_count": self.info_count,
            "scan_duration_ms": self.scan_duration_ms,
            "trivy_version": self.trivy_version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
        }
