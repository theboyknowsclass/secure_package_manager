import logging
import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from database.models import User

from database.models import AuditLog
from database.operations.audit_log_operations import AuditLogOperations
from database.operations.package_operations import PackageOperations
from database.operations.request_package_operations import (
    RequestPackageOperations,
)
from database.service import DatabaseService
from flask import Blueprint, jsonify, request
from flask.typing import ResponseReturnValue


# Type assertion helper for authenticated requests
def get_authenticated_user() -> "User":
    """Get the authenticated user from the request context."""
    return request.user  # type: ignore[attr-defined,no-any-return]


from services.auth_service import AuthService
from services.npm_registry_publishing_service import (
    NpmRegistryPublishingService,
)

logger = logging.getLogger(__name__)

# Create blueprint
approver_bp = Blueprint("approver", __name__, url_prefix="/api/approver")


# Initialize services
auth_service = AuthService()
publishing_service = NpmRegistryPublishingService()

# Define constants
INTERNAL_SERVER_ERROR_STR = "Internal server error"
PACKAGE_NOT_FOUND_STR = "Package not found"
PACKAGE_STATUS_NOT_FOUND_STR = "Package status not found"


# Package Approval Routes - Batch Operations Only
@approver_bp.route("/packages/publish/<int:package_id>", methods=["POST"])
@auth_service.require_admin
def publish_package(package_id: int) -> ResponseReturnValue:
    """Publish an approved package to the secure repository."""
    try:
        db_service = DatabaseService(os.getenv("DATABASE_URL", ""))
        with db_service.get_session() as session:
            package_ops = PackageOperations(session)
            package = package_ops.get_by_id(package_id)
            if not package:
                return jsonify({"error": PACKAGE_NOT_FOUND_STR}), 404

        if not package.package_status:
            return jsonify({"error": PACKAGE_STATUS_NOT_FOUND_STR}), 404

        if package.package_status.status != "Approved":
            return (
                jsonify({"error": "Package must be approved before publishing"}),
                400,
            )

        # Publish to secure repository
        success = publishing_service.publish_to_secure_repo(package)

        if success:
            # Log the action
            audit_log = AuditLog(
                user_id=get_authenticated_user().id,
                action="publish_package",
                resource_type="package",
                resource_id=package.id,
                details=(f"Package {package.name}@{package.version} published to secure repo"),
            )
            db_service = DatabaseService(os.getenv("DATABASE_URL", ""))
            with db_service.get_session() as session:
                audit_ops = AuditLogOperations(session)
                audit_ops.create(audit_log)
                session.commit()

            return jsonify({"message": "Package published successfully"})
        else:
            return jsonify({"error": "Failed to publish package"}), 500

    except Exception as e:
        logger.error(f"Publish package error: {str(e)}")
        return jsonify({"error": INTERNAL_SERVER_ERROR_STR}), 500


@approver_bp.route("/packages/batch-approve", methods=["POST"])
@auth_service.require_admin
def batch_approve_packages() -> ResponseReturnValue:
    """Approve multiple packages at once."""
    try:
        data = request.get_json() or {}
        package_ids = data.get("package_ids", [])
        reason = data.get("reason", "Approved by administrator")

        if not package_ids:
            return jsonify({"error": "No package IDs provided"}), 400

        if not isinstance(package_ids, list):
            return jsonify({"error": "package_ids must be an array"}), 400

        approved_count = 0
        failed_packages = []

        for package_id in package_ids:
            result = _process_package_approval(package_id, get_authenticated_user(), reason)
            if result["success"]:
                approved_count += 1
            else:
                failed_packages.append(result["error"])

        # Create a summary audit log for the batch operation
        summary_audit_log = AuditLog(
            user_id=get_authenticated_user().id,
            action="batch_approve_packages",
            resource_type="batch_operation",
            resource_id=None,  # No single resource ID for batch operations
            details=(
                f"Batch approval: {approved_count}/"
                f"{len(package_ids)} packages "
                f"approved by {get_authenticated_user().username}. Package IDs: "
                f"{list(package_ids)}. Reason: {reason}"
            ),
        )
        db_service = DatabaseService(os.getenv("DATABASE_URL", ""))
        with db_service.get_session() as session:
            audit_ops = AuditLogOperations(session)
            audit_ops.create(summary_audit_log)
            session.commit()

        # Packages are approved immediately and will be published by the
        # background worker
        logger.info((f"Batch approval completed: {approved_count} packages approved will be published by background worker"))

        response_data = {
            "message": (f"Batch approval completed - {approved_count} packages approved"),
            "approved_count": approved_count,
            "total_requested": len(package_ids),
            "package_ids": list(package_ids),
            "approved_by": get_authenticated_user().username,
            "note": (
                "Packages are approved and ready for publishing. Publishing can be done separately for better performance."
            ),
        }

        if failed_packages:
            response_data["failed_packages"] = failed_packages

        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"Batch approve packages error: {str(e)}")
        db_service = DatabaseService(os.getenv("DATABASE_URL", ""))
        with db_service.get_session() as session:
            session.rollback()
        return jsonify({"error": INTERNAL_SERVER_ERROR_STR}), 500


@approver_bp.route("/packages/batch-reject", methods=["POST"])
@auth_service.require_admin
def batch_reject_packages() -> ResponseReturnValue:
    """Reject multiple packages at once."""
    try:
        data = request.get_json() or {}
        package_ids = data.get("package_ids", [])
        reason = data.get("reason", "Rejected by administrator")

        if not package_ids:
            return jsonify({"error": "No package IDs provided"}), 400

        if not isinstance(package_ids, list):
            return jsonify({"error": "package_ids must be an array"}), 400

        if not reason or not reason.strip():
            return jsonify({"error": "Rejection reason is required"}), 400

        rejected_count = 0
        failed_packages = []

        for package_id in package_ids:
            result = _process_package_rejection(package_id, get_authenticated_user(), reason)
            if result["success"]:
                rejected_count += 1
            else:
                failed_packages.append(result["error"])

        # Create a summary audit log for the batch operation
        summary_audit_log = AuditLog(
            user_id=get_authenticated_user().id,
            action="batch_reject_packages",
            resource_type="batch_operation",
            resource_id=None,  # No single resource ID for batch operations
            details=(
                f"Batch rejection: {rejected_count}/{len(package_ids)} packages rejected by "
                f"{get_authenticated_user().username}. Package IDs: {list(package_ids)}. Reason: {reason}"
            ),
        )
        db_service = DatabaseService(os.getenv("DATABASE_URL", ""))
        with db_service.get_session() as session:
            audit_ops = AuditLogOperations(session)
            audit_ops.create(summary_audit_log)
            session.commit()

        response_data = {
            "message": "Batch rejection completed",
            "rejected_count": rejected_count,
            "total_requested": len(package_ids),
            "package_ids": list(package_ids),
            "rejected_by": get_authenticated_user().username,
        }

        if failed_packages:
            response_data["failed_packages"] = failed_packages

        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"Batch reject packages error: {str(e)}")
        db_service = DatabaseService(os.getenv("DATABASE_URL", ""))
        with db_service.get_session() as session:
            session.rollback()
        return jsonify({"error": INTERNAL_SERVER_ERROR_STR}), 500


@approver_bp.route("/packages/validated", methods=["GET"])
@auth_service.require_admin
def get_validated_packages() -> ResponseReturnValue:
    """Get all packages ready for admin review (pending approval)"""
    try:
        db_service = DatabaseService(os.getenv("DATABASE_URL", ""))
        with db_service.get_session() as session:
            package_ops = PackageOperations(session)
            packages = package_ops.get_pending_approval()

        # Handle case when no packages exist
        if not packages:
            return jsonify({"packages": []})

        # Build response with proper error handling for relationships
        package_list = []
        for pkg in packages:
            try:
                # Get request information for this package
                db_service = DatabaseService(os.getenv("DATABASE_URL", ""))
                with db_service.get_session() as session:
                    request_package_ops = RequestPackageOperations(session)
                    request_packages = request_package_ops.get_by_package_id(pkg.id)
                    request_package = request_packages[0] if request_packages else None
                    request_data = None

                    request_data = request_record(request_package=request_package, session=session)
                    if not request_data:
                        continue
                
                # Get package type from RequestPackage
                package_type = request_package.package_type if request_package else "new"

                package_list.append(
                    {
                        "id": pkg.id,
                        "name": pkg.name,
                        "version": pkg.version,
                        "security_score": pkg.package_status.security_score or 0,
                        "license_score": pkg.package_status.license_score,
                        "license_identifier": pkg.license_identifier or "Unknown",
                        "license_status": pkg.package_status.license_status,
                        "security_scan_status": pkg.package_status.security_scan_status,
                        "type": package_type,
                        "request": request_data
                        or {
                            "id": 0,
                            "application_name": "Unknown",
                            "version": "Unknown",
                        },
                    }
                )
            except Exception as pkg_error:
                logger.warning(f"Error processing package {pkg.id}: {str(pkg_error)}")
                # Skip this package but continue with others
                continue

        return jsonify({"packages": package_list})
    except Exception as e:
        logger.error(f"Get validated packages error: {str(e)}")
        return jsonify({"error": INTERNAL_SERVER_ERROR_STR}), 500


def _process_package_approval(package_id: int, user: Any, reason: str) -> dict:
    """Process approval of a single package.

    Returns:
        dict: {"success": bool, "error": dict or None}
    """
    try:
        db_service = DatabaseService(os.getenv("DATABASE_URL", ""))
        with db_service.get_session() as session:
            package_ops = PackageOperations(session)
            package = package_ops.get_by_id(package_id)

            if not package:
                return {
                    "success": False,
                    "error": {"id": package_id, "error": PACKAGE_NOT_FOUND_STR},
                }

            if not package.package_status:
                return {
                    "success": False,
                    "error": {
                        "id": package_id,
                        "error": PACKAGE_STATUS_NOT_FOUND_STR,
                    },
                }

            if package.package_status.status != "Pending Approval":
                return {
                    "success": False,
                    "error": {
                        "id": package_id,
                        "error": "Package must be pending approval",
                    },
                }

            # Approve the package
            package.package_status.status = "Approved"
            package.package_status.approver_id = user.id

            # Log the approval
            audit_log = AuditLog(
                user_id=user.id,
                action="approve_package",
                resource_type="package",
                resource_id=package.id,
                details=(f"Package {package.name}@{package.version} approved: {reason}"),
            )
            audit_ops = AuditLogOperations(session)
            audit_ops.create(audit_log)
            session.commit()

        return {"success": True, "error": None}

    except Exception as pkg_error:
        logger.error(f"Error approving package {package_id}: {str(pkg_error)}")
        return {
            "success": False,
            "error": {"id": package_id, "error": str(pkg_error)},
        }


def _process_package_rejection(package_id: int, user: Any, reason: str) -> dict:
    """Process rejection of a single package.

    Returns:
        dict: {"success": bool, "error": dict or None}
    """
    try:
        db_service = DatabaseService(os.getenv("DATABASE_URL", ""))
        with db_service.get_session() as session:
            package_ops = PackageOperations(session)
            package = package_ops.get_by_id(package_id)

            if not package:
                return {
                    "success": False,
                    "error": {"id": package_id, "error": PACKAGE_NOT_FOUND_STR},
                }

            if not package.package_status:
                return {
                    "success": False,
                    "error": {
                        "id": package_id,
                        "error": PACKAGE_STATUS_NOT_FOUND_STR,
                    },
                }

            if package.package_status.status in ["Approved"]:
                return {
                    "success": False,
                    "error": {
                        "id": package_id,
                        "error": "Cannot reject an already approved package",
                    },
                }

            # Reject the package
            package.package_status.status = "Rejected"
            package.package_status.rejector_id = user.id

            # Log the rejection
            audit_log = AuditLog(
                user_id=user.id,
                action="batch_reject_package",
                resource_type="package",
                resource_id=package.id,
                details=(f"Package {package.name}@{package.version} rejected: {reason}"),
            )
            audit_ops = AuditLogOperations(session)
            audit_ops.create(audit_log)
            session.commit()

        return {"success": True, "error": None}

    except Exception as pkg_error:
        logger.error(f"Error rejecting package {package_id}: {str(pkg_error)}")
        return {
            "success": False,
            "error": {"id": package_id, "error": str(pkg_error)},
        }



def request_record(request_package, session):
    from database.operations.request_operations import RequestOperations
    request_ops = RequestOperations(session)

    request_data = None

    if request_package.request_id is None:
        return request_data
    
    request_record = request_ops.get_by_id(request_package.request_id)
    
    if request_record:
        request_data = {
            "id": request_record.id,
            "application_name": request_record.application_name,
            "version": request_record.version,
        }

    return request_data