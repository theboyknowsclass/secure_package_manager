from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Create a SQLAlchemy instance that will be initialized by the app
db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    full_name = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    applications = db.relationship('Application', backref='creator', lazy=True)
    package_requests = db.relationship('PackageRequest', backref='requestor', lazy=True)
    audit_logs = db.relationship('AuditLog', backref='user', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'is_admin': self.is_admin,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Application(db.Model):
    __tablename__ = 'applications'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    version = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    package_requests = db.relationship('PackageRequest', backref='application', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class PackageRequest(db.Model):
    __tablename__ = 'package_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('applications.id'), nullable=False)
    requestor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    package_lock_file = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default='requested')
    total_packages = db.Column(db.Integer, default=0)
    validated_packages = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    packages = db.relationship('Package', backref='package_request', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'application_id': self.application_id,
            'requestor_id': self.requestor_id,
            'status': self.status,
            'total_packages': self.total_packages,
            'validated_packages': self.validated_packages,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Package(db.Model):
    __tablename__ = 'packages'
    
    id = db.Column(db.Integer, primary_key=True)
    package_request_id = db.Column(db.Integer, db.ForeignKey('package_requests.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    version = db.Column(db.String(100), nullable=False)
    npm_url = db.Column(db.String(500))
    local_path = db.Column(db.String(500))
    file_size = db.Column(db.BigInteger)
    checksum = db.Column(db.String(255))
    status = db.Column(db.String(50), default='requested')
    validation_errors = db.Column(db.ARRAY(db.String))
    security_score = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    validations = db.relationship('PackageValidation', backref='package', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'package_request_id': self.package_request_id,
            'name': self.name,
            'version': self.version,
            'npm_url': self.npm_url,
            'local_path': self.local_path,
            'file_size': self.file_size,
            'checksum': self.checksum,
            'status': self.status,
            'validation_errors': self.validation_errors or [],
            'security_score': self.security_score,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class PackageValidation(db.Model):
    __tablename__ = 'package_validations'
    
    id = db.Column(db.Integer, primary_key=True)
    package_id = db.Column(db.Integer, db.ForeignKey('packages.id'), nullable=False)
    validation_type = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'package_id': self.package_id,
            'validation_type': self.validation_type,
            'status': self.status,
            'details': self.details,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class AuditLog(db.Model):
    __tablename__ = 'audit_log'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    resource_type = db.Column(db.String(100), nullable=False)
    resource_id = db.Column(db.Integer)
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'action': self.action,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'details': self.details,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
