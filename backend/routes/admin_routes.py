import logging

from database.models import AuditLog, Package, SupportedLicense
from flask import Blueprint, jsonify, request
from flask.typing import ResponseReturnValue
from services.auth_service import AuthService
from services.package_service import PackageService

from database import db

logger = logging.getLogger(__name__)

# Create blueprint
admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")

# Initialize services
auth_service = AuthService()
package_service = PackageService()


# Package Management Routes (moved to approver_routes.py)
# Package approval, rejection, publishing, and validation routes have been moved
# to /api/approver/ endpoints for better separation of concerns


# License Management Routes
@admin_bp.route("/licenses", methods=["GET"])  # type: ignore[misc]
@auth_service.require_auth
def get_supported_licenses() -> ResponseReturnValue:
    """Get all supported licenses"""
    try:
        status = request.args.get("status")  # 'always_allowed', 'allowed', 'avoid', 'blocked'
        query = SupportedLicense.query

        if status:
            query = query.filter_by(status=status)

        licenses = query.all()
        return jsonify({"licenses": [license.to_dict() for license in licenses]})
    except Exception as e:
        logger.error(f"Get supported licenses error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@admin_bp.route("/licenses", methods=["POST"])  # type: ignore[misc]
@auth_service.require_auth
def create_supported_license() -> ResponseReturnValue:
    """Create a new supported license"""
    try:
        if not request.user.is_admin():
            return jsonify({"error": "Admin access required"}), 403

        data = request.get_json()

        # Validate required fields
        if not data.get("name") or not data.get("identifier"):
            return jsonify({"error": "Name and identifier are required"}), 400

        # Check if identifier already exists
        existing = SupportedLicense.query.filter_by(identifier=data["identifier"]).first()
        if existing:
            return jsonify({"error": "License identifier already exists"}), 400

        # Create new license
        license = SupportedLicense(
            name=data["name"],
            identifier=data["identifier"],
            status=data.get("status", "allowed"),
            created_by=request.user.id,
        )

        db.session.add(license)
        db.session.commit()

        # Log the action
        audit_log = AuditLog(
            user_id=request.user.id,
            action="create_license",
            resource_type="license",
            resource_id=license.id,
            details=f"Created license: {license.name} ({license.identifier})",
        )
        db.session.add(audit_log)
        db.session.commit()

        return (
            jsonify(
                {
                    "message": "License created successfully",
                    "license": license.to_dict(),
                }
            ),
            201,
        )

    except Exception as e:
        logger.error(f"Create license error: {str(e)}")
        db.session.rollback()
        return jsonify({"error": "Internal server error"}), 500


@admin_bp.route("/licenses/<int:license_id>", methods=["PUT"])  # type: ignore[misc]
@auth_service.require_auth
def update_supported_license(license_id: int) -> ResponseReturnValue:
    """Update a supported license"""
    try:
        if not request.user.is_admin():
            return jsonify({"error": "Admin access required"}), 403

        license = SupportedLicense.query.get_or_404(license_id)
        data = request.get_json()

        # Update fields
        if "name" in data:
            license.name = data["name"]
        if "status" in data:
            license.status = data["status"]

        db.session.commit()

        # Log the action
        audit_log = AuditLog(
            user_id=request.user.id,
            action="update_license",
            resource_type="license",
            resource_id=license.id,
            details=f"Updated license: {license.name} ({license.identifier})",
        )
        db.session.add(audit_log)
        db.session.commit()

        return jsonify({"message": "License updated successfully", "license": license.to_dict()})
    except Exception as e:
        logger.error(f"Update license error: {str(e)}")
        db.session.rollback()
        return jsonify({"error": "Internal server error"}), 500


@admin_bp.route("/licenses/<int:license_id>", methods=["DELETE"])  # type: ignore[misc]
@auth_service.require_auth
def delete_supported_license(license_id: int) -> ResponseReturnValue:
    """Delete a supported license"""
    try:
        if not request.user.is_admin():
            return jsonify({"error": "Admin access required"}), 403

        license = SupportedLicense.query.get_or_404(license_id)

        # Check if license is being used by any packages
        package_count = Package.query.filter_by(license_identifier=license.identifier).count()
        if package_count > 0:
            return (
                jsonify(
                    {"error": f"Cannot delete license. It is used by {package_count} package(s). Disable it instead."}
                ),
                400,
            )

        db.session.delete(license)
        db.session.commit()

        # Log the action
        audit_log = AuditLog(
            user_id=request.user.id,
            action="delete_license",
            resource_type="license",
            resource_id=license_id,
            details=f"Deleted license: {license.name} ({license.identifier})",
        )
        db.session.add(audit_log)
        db.session.commit()

        return jsonify({"message": "License deleted successfully"})
    except Exception as e:
        logger.error(f"Delete license error: {str(e)}")
        db.session.rollback()
        return jsonify({"error": "Internal server error"}), 500


# Configuration Route (consolidated from repository-config endpoints)
@admin_bp.route("/config", methods=["GET"])  # type: ignore[misc]
@auth_service.require_auth
def get_config() -> ResponseReturnValue:
    """Get system configuration including status and environment variables"""
    try:
        import os

        from config.constants import (
            API_URL,
            DATABASE_URL,
            FRONTEND_URL,
            IDP_URL,
            SOURCE_REPOSITORY_URL,
            TARGET_REPOSITORY_URL,
            TRIVY_URL,
        )

        # Check configuration status
        is_complete = package_service.is_configuration_complete()
        missing_keys = package_service.get_missing_config_keys()

        # Get configuration values (mask sensitive data)
        config = {
            "repository": {
                "source_repository_url": SOURCE_REPOSITORY_URL,
                "target_repository_url": TARGET_REPOSITORY_URL,
            },
            "services": {
                "api_url": API_URL,
                "frontend_url": FRONTEND_URL,
                "database_url": _mask_url(DATABASE_URL),
                "idp_url": IDP_URL,
                "trivy_url": TRIVY_URL,
            },
            "security": {
                "jwt_secret_configured": bool(os.getenv("JWT_SECRET")),
                "flask_secret_configured": bool(os.getenv("FLASK_SECRET_KEY")),
                "oauth_audience": os.getenv("OAUTH_AUDIENCE", "Not configured"),
                "oauth_issuer": os.getenv("OAUTH_ISSUER", "Not configured"),
            },
            "trivy": {
                "timeout": os.getenv("TRIVY_TIMEOUT", "300"),
                "max_retries": os.getenv("TRIVY_MAX_RETRIES", "3"),
            },
            "environment": {
                "flask_env": os.getenv("FLASK_ENV", "development"),
                "flask_debug": os.getenv("FLASK_DEBUG", "0"),
                "max_content_length": os.getenv("MAX_CONTENT_LENGTH", "16777216"),
            },
        }

        return jsonify(
            {
                "config": config,
                "status": {
                    "is_complete": is_complete,
                    "missing_keys": missing_keys,
                    "requires_admin_setup": not is_complete,
                    "note": "Repository configuration is now managed via environment variables",
                },
            }
        )

    except Exception as e:
        logger.error(f"Get config error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


def _mask_url(url: str) -> str:
    """Mask sensitive parts of URLs for display"""
    if not url:
        return "Not configured"

    # Mask password in database URLs
    if "://" in url and "@" in url:
        parts = url.split("://")
        if len(parts) == 2:
            protocol = parts[0]
            rest = parts[1]
            if "@" in rest:
                user_pass, host_db = rest.split("@", 1)
                if ":" in user_pass:
                    user, _ = user_pass.split(":", 1)
                    return f"{protocol}://{user}:***@{host_db}"

    return url
