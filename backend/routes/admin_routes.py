import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from database.models import User

from database.models import AuditLog, SupportedLicense
from database.operations.audit_log_operations import AuditLogOperations
from database.operations.supported_license_operations import (
    SupportedLicenseOperations,
)
from database.service import DatabaseService
from flask import Blueprint, jsonify, request
from flask.typing import ResponseReturnValue


# Type assertion helper for authenticated requests
def get_authenticated_user() -> "User":
    """Get the authenticated user from the request context."""
    return request.user  # type: ignore[attr-defined,no-any-return]


from services.auth_service import AuthService
from services.configuration_service import ConfigurationService

logger = logging.getLogger(__name__)

# Create blueprint
admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")

# Initialize services
auth_service = AuthService()
config_service = ConfigurationService()


# License Management Routes
@admin_bp.route("/licenses", methods=["GET"])
@auth_service.require_auth
def get_supported_licenses() -> ResponseReturnValue:
    """Get all supported licenses."""
    try:
        status = request.args.get(
            "status"
        )  # 'always_allowed', 'allowed', 'avoid', 'blocked'
        
        db_service = DatabaseService(os.getenv("DATABASE_URL", ""))
        with db_service.get_session() as session:
            license_ops = SupportedLicenseOperations(session)
            
            if status:
                licenses = license_ops.get_by_status(status)
            else:
                licenses = license_ops.get_all()
                
        return jsonify(
            {"licenses": [license.to_dict() for license in licenses]}
        )
    except Exception as e:
        logger.error(f"Get supported licenses error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@admin_bp.route("/licenses", methods=["POST"])
@auth_service.require_auth
def create_supported_license() -> ResponseReturnValue:
    """Create a new supported license."""
    try:
        if not get_authenticated_user().is_admin():
            return jsonify({"error": "Admin access required"}), 403

        data = request.get_json()

        # Validate required fields
        if not data.get("name") or not data.get("identifier"):
            return jsonify({"error": "Name and identifier are required"}), 400

        # Check if identifier already exists
        db_service = DatabaseService(os.getenv("DATABASE_URL", ""))
        with db_service.get_session() as session:
            license_ops = SupportedLicenseOperations(session)
            existing = license_ops.get_by_identifier(data["identifier"])
        if existing:
            return jsonify({"error": "License identifier already exists"}), 400

        # Create new license
        license = SupportedLicense(
            name=data["name"],
            identifier=data["identifier"],
            status=data.get("status", "allowed"),
            created_by=get_authenticated_user().id,
        )

        db_service = DatabaseService(os.getenv("DATABASE_URL", ""))
        with db_service.get_session() as session:
            license_ops = SupportedLicenseOperations(session)
            license_ops.create(license)
            session.commit()

            # Log the action
            audit_log = AuditLog(
                user_id=get_authenticated_user().id,
                action="create_license",
                resource_type="license",
                resource_id=license.id,
                details=f"Created license: {license.name} ({license.identifier})",
            )
            audit_ops = AuditLogOperations(session)
            audit_ops.create(audit_log)
            session.commit()

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
        db_service = DatabaseService(os.getenv("DATABASE_URL", ""))
        with db_service.get_session() as session:
            session.rollback()
        return jsonify({"error": "Internal server error"}), 500


@admin_bp.route(
    "/licenses/<int:license_id>", methods=["PUT"]
)
@auth_service.require_auth
def update_supported_license(license_id: int) -> ResponseReturnValue:
    """Update a supported license."""
    try:
        if not get_authenticated_user().is_admin():
            return jsonify({"error": "Admin access required"}), 403

        db_service = DatabaseService(os.getenv("DATABASE_URL", ""))
        with db_service.get_session() as session:
            license_ops = SupportedLicenseOperations(session)
            license = license_ops.get_by_id(license_id)
            if not license:
                return jsonify({"error": "License not found"}), 404
        data = request.get_json()

        # Update fields
        if "name" in data:
            license.name = data["name"]
        if "status" in data:
            license.status = data["status"]

        db_service = DatabaseService(os.getenv("DATABASE_URL", ""))
        with db_service.get_session() as session:
            session.commit()

            # Log the action
            audit_log = AuditLog(
                user_id=get_authenticated_user().id,
                action="update_license",
                resource_type="license",
                resource_id=license.id,
                details=f"Updated license: {license.name} ({license.identifier})",
            )
            audit_ops = AuditLogOperations(session)
            audit_ops.create(audit_log)
            session.commit()

        return jsonify(
            {
                "message": "License updated successfully",
                "license": license.to_dict(),
            }
        )
    except Exception as e:
        logger.error(f"Update license error: {str(e)}")
        db_service = DatabaseService(os.getenv("DATABASE_URL", ""))
        with db_service.get_session() as session:
            session.rollback()
        return jsonify({"error": "Internal server error"}), 500


@admin_bp.route(
    "/licenses/<int:license_id>", methods=["DELETE"]
)
@auth_service.require_auth
def delete_supported_license(license_id: int) -> ResponseReturnValue:
    """Delete a supported license."""
    try:
        if not get_authenticated_user().is_admin():
            return jsonify({"error": "Admin access required"}), 403

        db_service = DatabaseService(os.getenv("DATABASE_URL", ""))
        with db_service.get_session() as session:
            license_ops = SupportedLicenseOperations(session)
            license = license_ops.get_by_id(license_id)
            if not license:
                return jsonify({"error": "License not found"}), 404

        # Check if license is being used by any packages
        if license.identifier is None:
            # Skip licenses without identifier - they can be deleted safely
            package_count = 0
        else:
            db_service = DatabaseService(os.getenv("DATABASE_URL", ""))
            with db_service.get_session() as session:
                license_ops = SupportedLicenseOperations(session)
                package_count = license_ops.count_packages_by_license(
                    license.identifier
                )
        if package_count > 0:
            return (
                jsonify(
                    {
                        "error": (
                            f"Cannot delete license. It is used by "
                            f"{package_count} package(s). Disable it instead."
                        )
                    }
                ),
                400,
            )

        db_service = DatabaseService(os.getenv("DATABASE_URL", ""))
        with db_service.get_session() as session:
            license_ops = SupportedLicenseOperations(session)
            license_ops.delete(license)
            session.commit()

            # Log the action
            audit_log = AuditLog(
                user_id=get_authenticated_user().id,
                action="delete_license",
                resource_type="license",
                resource_id=license_id,
                details=f"Deleted license: {license.name} ({license.identifier})",
            )
            audit_ops = AuditLogOperations(session)
            audit_ops.create(audit_log)
            session.commit()

        return jsonify({"message": "License deleted successfully"})
    except Exception as e:
        logger.error(f"Delete license error: {str(e)}")
        db_service = DatabaseService(os.getenv("DATABASE_URL", ""))
        with db_service.get_session() as session:
            session.rollback()
        return jsonify({"error": "Internal server error"}), 500


# Configuration Route (consolidated from repository-config endpoints)
@admin_bp.route("/config", methods=["GET"])
@auth_service.require_auth
def get_config() -> ResponseReturnValue:
    """Get system configuration including status and environment variables."""
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
        is_complete = config_service.is_configuration_complete()
        missing_keys = config_service.get_missing_config_keys()

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
                "oauth_audience": os.getenv(
                    "OAUTH_AUDIENCE", "Not configured"
                ),
                "oauth_issuer": os.getenv("OAUTH_ISSUER", "Not configured"),
            },
            "trivy": {
                "timeout": os.getenv("TRIVY_TIMEOUT", "300"),
                "max_retries": os.getenv("TRIVY_MAX_RETRIES", "3"),
            },
            "environment": {
                "flask_env": os.getenv("FLASK_ENV", "development"),
                "flask_debug": os.getenv("FLASK_DEBUG", "0"),
                "max_content_length": os.getenv(
                    "MAX_CONTENT_LENGTH", "16777216"
                ),
            },
        }

        return jsonify(
            {
                "config": config,
                "status": {
                    "is_complete": is_complete,
                    "missing_keys": missing_keys,
                    "requires_admin_setup": not is_complete,
                    "note": (
                        "Repository configuration is now managed via "
                        "environment variables"
                    ),
                },
            }
        )

    except Exception as e:
        logger.error(f"Get config error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


def _mask_url(url: str) -> str:
    """Mask sensitive parts of URLs for display."""
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
