import json
import logging
import os
import traceback
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Union

if TYPE_CHECKING:
    from database.models import User

from database.models import (
    AuditLog,
    Package,
    PackageStatus,
    Request,
    RequestPackage,
    SecurityScan,
)
from database.operations.audit_log_operations import AuditLogOperations
from database.operations.package_operations import PackageOperations
from database.operations.request_operations import RequestOperations
from database.operations.request_package_operations import (
    RequestPackageOperations,
)
from database.session_helper import SessionHelper
from flask import Blueprint, jsonify, request
from flask.typing import ResponseReturnValue


# Type assertion helper for authenticated requests
def get_authenticated_user() -> "User":
    """Get the authenticated user from the request context."""
    return request.user  # type: ignore[attr-defined]


from services.auth_service import AuthService
from services.trivy_service import TrivyService

logger = logging.getLogger(__name__)

# Create blueprint
package_bp = Blueprint("packages", __name__, url_prefix="/api/packages")


def handle_error(e: Exception, context: str = "") -> ResponseReturnValue:
    """Handle errors with detailed information in development mode."""
    logger.error(f"{context} error: {str(e)}")
    logger.error(f"Traceback: {traceback.format_exc()}")

    # Check environment variables for development mode
    flask_env = os.getenv("FLASK_ENV")
    environment = os.getenv("ENVIRONMENT")
    flask_debug = os.getenv("FLASK_DEBUG")

    logger.info(
        f"Environment check - FLASK_ENV: {flask_env}, ENVIRONMENT: {environment}, FLASK_DEBUG: {flask_debug}"
    )

    # For now, always return detailed errors to test
    return (
        jsonify(
            {
                "error": "Internal server error",
                "details": str(e),
                "context": context,
                "traceback": traceback.format_exc(),
            }
        ),
        500,
    )


# Initialize services
auth_service = AuthService()
trivy_service = TrivyService()


@package_bp.route("/upload", methods=["POST"])  # type: ignore[misc]
@auth_service.require_auth
def upload_package_lock() -> ResponseReturnValue:
    """Upload package-lock.json file for background processing."""
    try:
        # Validate the uploaded file
        file = _validate_uploaded_file()
        if isinstance(file, tuple):  # Error response
            return file

        # Parse and validate the JSON content
        package_data = _parse_package_lock_file(file)
        if isinstance(package_data, tuple):  # Error response
            return package_data

        # Create request record with raw blob
        request_data = _create_request_with_blob(package_data)

        return _create_success_response(request_data, package_data)

    except Exception as e:
        return handle_error(e, "Upload")


def _validate_uploaded_file() -> Union[Any, ResponseReturnValue]:
    """Validate the uploaded file."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not file.filename.endswith(".json"):
        return jsonify({"error": "File must be a JSON file"}), 400

    return file


def _parse_package_lock_file(
    file: Any,
) -> Union[Dict[str, Any], ResponseReturnValue]:
    """Parse and validate the package-lock.json file."""
    try:
        package_data = json.load(file)
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON file"}), 400

    # Basic validation that this looks like a package-lock.json
    if not isinstance(package_data, dict):
        return jsonify({"error": "File must contain a valid JSON object"}), 400

    if "lockfileVersion" not in package_data:
        return (
            jsonify(
                {
                    "error": "Invalid file format",
                    "details": (
                        "This file does not appear to be a package-lock.json"
                        " file. Missing required fields."
                    ),
                }
            ),
            400,
        )

    return package_data


def _create_request_with_blob(package_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new request record with raw blob."""
    app_name = package_data.get("name", "Unknown Application")
    app_version = package_data.get("version", "1.0.0")

    with SessionHelper.get_session() as db:
        request_record = Request(
            application_name=app_name,
            version=app_version,
            requestor_id=get_authenticated_user().id,
            raw_request_blob=json.dumps(package_data),  # Store raw JSON blob
        )

        request_ops = RequestOperations(db.session)
        request_ops.create(request_record)
        db.flush()  # Get the ID without committing

        # Log the request creation
        audit_log = AuditLog(
            user_id=get_authenticated_user().id,
            action="create_request",
            resource_type="request",
            resource_id=request_record.id,
            details=f"Created package request for {app_name}@{app_version}",
        )
        audit_ops = AuditLogOperations(db.session)
        audit_ops.create(audit_log)
        db.commit()

        # Return the essential data as a dictionary
        return {
            "id": request_record.id,
            "application_name": request_record.application_name,
            "version": request_record.version,
            "requestor_id": request_record.requestor_id,
            "raw_request_blob": request_record.raw_request_blob,
            "created_at": request_record.created_at,
        }


def _create_success_response(
    request_data: Dict[str, Any],
    package_data: Dict[str, Any],
) -> ResponseReturnValue:
    """Create success response for package upload."""
    app_name = package_data.get("name", "Unknown Application")
    app_version = package_data.get("version", "1.0.0")

    return (
        jsonify(
            {
                "message": "Package lock file uploaded successfully",
                "request_id": request_data["id"],
                "application": {
                    "name": app_name,
                    "version": app_version,
                },
            }
        ),
        200,
    )


@package_bp.route(
    "/requests/<int:request_id>", methods=["GET"]
)  # type: ignore[misc]
@auth_service.require_auth
def get_package_request(request_id: int) -> ResponseReturnValue:
    """Get package request details."""
    try:
        with SessionHelper.get_session() as db:
            request_ops = RequestOperations(db.session)
            request_record = request_ops.get_by_id(request_id)
            if not request_record:
                return jsonify({"error": "Request not found"}), 404

            # Check if user has access to this request
            if (
                not get_authenticated_user().is_admin()
                and request_record.requestor_id != get_authenticated_user().id
            ):
                return jsonify({"error": "Access denied"}), 403

            # Get packages for this request with their creation context and scan results
            package_ops = PackageOperations(db.session)
            packages_with_context = (
                package_ops.get_packages_with_context_and_scans(request_id)
            )

            # Get request status from status manager using the same session
            from services.package_request_status_manager import (
                PackageRequestStatusManager,
            )

            status_manager = PackageRequestStatusManager(db)
            status_summary = status_manager.get_request_status_summary(
                request_id
            )

            # Build packages list
            packages_list = []
            if packages_with_context:
                for item in packages_with_context:
                    try:
                        # Handle both tuple and single object cases
                        if isinstance(item, tuple) and len(item) >= 3:
                            pkg, rp, scan = item[0], item[1], item[2]
                        else:
                            # Fallback: assume it's just a package
                            pkg = item
                            rp = None
                            scan = None

                        packages_list.append(
                            {
                                "id": pkg.id,
                                "name": pkg.name,
                                "version": pkg.version,
                                "status": (
                                    pkg.package_status.status
                                    if pkg.package_status
                                    else "Checking Licence"
                                ),
                                "security_score": (
                                    pkg.package_status.security_score
                                    if pkg.package_status
                                    else None
                                ),
                                "license_score": (
                                    pkg.package_status.license_score
                                    if pkg.package_status
                                    else None
                                ),
                                "security_scan_status": (
                                    pkg.package_status.security_scan_status
                                    if pkg.package_status
                                    else "pending"
                                ),
                                "license_identifier": pkg.license_identifier,
                                "license_status": (
                                    pkg.package_status.license_status
                                    if pkg.package_status
                                    else None
                                ),
                                "type": rp.package_type if rp else "unknown",
                                "scan_result": (
                                    {
                                        "scan_duration_ms": scan.scan_duration_ms,
                                        "critical_count": scan.critical_count,
                                        "high_count": scan.high_count,
                                        "medium_count": scan.medium_count,
                                        "low_count": scan.low_count,
                                        "info_count": scan.info_count,
                                        "scan_type": scan.scan_type,
                                        "trivy_version": scan.trivy_version,
                                        "created_at": (
                                            scan.created_at.isoformat()
                                            if scan.created_at
                                            else None
                                        ),
                                        "completed_at": (
                                            scan.completed_at.isoformat()
                                            if scan.completed_at
                                            else None
                                        ),
                                    }
                                    if scan
                                    else None
                                ),
                            }
                        )
                    except Exception as e:
                        logger.error(f"Error processing package item: {e}")
                        logger.error(f"Item type: {type(item)}, Item: {item}")
                        continue

            return (
                jsonify(
                    {
                        "request": {
                            "id": request_record.id,
                            "application_name": request_record.application_name,
                            "version": request_record.version,
                            "status": status_summary["current_status"],
                            "total_packages": status_summary["total_packages"],
                            "completion_percentage": status_summary[
                                "completion_percentage"
                            ],
                            "created_at": request_record.created_at.isoformat(),
                            "requestor": {
                                "id": request_record.requestor.id,
                                "username": request_record.requestor.username,
                                "full_name": request_record.requestor.full_name,
                            },
                            "package_counts": status_summary["package_counts"],
                        },
                        "packages": packages_list,
                    }
                ),
                200,
            )

    except Exception as e:
        return handle_error(e, "Get request")


@package_bp.route("/requests", methods=["GET"])  # type: ignore[misc]
@auth_service.require_auth
def list_package_requests() -> ResponseReturnValue:
    """List package requests for the user."""
    try:
        with SessionHelper.get_session() as db:
            request_ops = RequestOperations(db.session)
            if get_authenticated_user().is_admin():
                requests = request_ops.get_all()
            else:
                requests = request_ops.get_by_requestor(
                    get_authenticated_user().id
                )

            result_requests = []
            for req in requests:
                # Get request status from status manager (this already includes
                # package counts)
                from services.package_request_status_manager import (
                    PackageRequestStatusManager,
                )

                status_manager = PackageRequestStatusManager()
                status_summary = status_manager.get_request_status_summary(
                    req.id
                )

                result_requests.append(
                    {
                        "id": req.id,
                        "application_name": req.application_name,
                        "version": req.version,
                        "status": status_summary["current_status"],
                        "total_packages": status_summary["total_packages"],
                        "completion_percentage": status_summary[
                            "completion_percentage"
                        ],
                        "created_at": req.created_at.isoformat(),
                        "requestor": {
                            "id": req.requestor.id,
                            "username": req.requestor.username,
                            "full_name": req.requestor.full_name,
                        },
                        "package_counts": status_summary["package_counts"],
                    }
                )

        return jsonify({"requests": result_requests}), 200

    except Exception as e:
        return handle_error(e, "List requests")


@package_bp.route(
    "/<int:package_id>/security-scan/status", methods=["GET"]
)  # type: ignore[misc]
@auth_service.require_auth
def get_package_security_scan_status(package_id: int) -> ResponseReturnValue:
    """Get security scan status for a package."""
    try:
        with SessionHelper.get_session() as db:
            package_ops = PackageOperations(db.session)
            package = package_ops.get_by_id(package_id)
            if not package:
                return jsonify({"error": "Package not found"}), 404

        # Check if user has access to this package
        if not get_authenticated_user().is_admin():
            # Check if user has access through any request
            with SessionHelper.get_session() as db:
                request_package_ops = RequestPackageOperations(db.session)
                has_access = request_package_ops.check_user_access(
                    package_id, get_authenticated_user().id
                )

            if not has_access:
                return jsonify({"error": "Access denied"}), 403

        scan_status = trivy_service.get_scan_status(package_id)

        if not scan_status:
            return (
                jsonify({"error": "No security scan found for this package"}),
                404,
            )

        return (
            jsonify(
                {
                    "package_id": package_id,
                    "package_name": package.name,
                    "package_version": package.version,
                    "scan_status": scan_status,
                }
            ),
            200,
        )

    except Exception as e:
        return handle_error(e, "Get security scan status")


@package_bp.route(
    "/<int:package_id>/security-scan/report", methods=["GET"]
)  # type: ignore[misc]
@auth_service.require_auth
def get_package_security_scan_report(package_id: int) -> ResponseReturnValue:
    """Get detailed security scan report for a package."""
    try:
        with SessionHelper.get_session() as db:
            package_ops = PackageOperations(db.session)
            package = package_ops.get_by_id(package_id)
            if not package:
                return jsonify({"error": "Package not found"}), 404

        # Check if user has access to this package
        if not get_authenticated_user().is_admin():
            # Check if user has access through any request
            with SessionHelper.get_session() as db:
                request_package_ops = RequestPackageOperations(db.session)
                has_access = request_package_ops.check_user_access(
                    package_id, get_authenticated_user().id
                )

            if not has_access:
                return jsonify({"error": "Access denied"}), 403

        scan_report = trivy_service.get_scan_report(package_id)

        if not scan_report:
            return (
                jsonify(
                    {"error": "No security scan report found for this package"}
                ),
                404,
            )

        return (
            jsonify(
                {
                    "package_id": package_id,
                    "package_name": package.name,
                    "package_version": package.version,
                    "scan_report": scan_report,
                }
            ),
            200,
        )

    except Exception as e:
        return handle_error(e, "Get security scan report")


@package_bp.route(
    "/<int:package_id>/security-scan/trigger", methods=["POST"]
)  # type: ignore[misc]
@auth_service.require_auth
def trigger_package_security_scan(package_id: int) -> ResponseReturnValue:
    """Trigger a new security scan for a package."""
    try:
        with SessionHelper.get_session() as db:
            package_ops = PackageOperations(db.session)
            package = package_ops.get_by_id(package_id)
            if not package:
                return jsonify({"error": "Package not found"}), 404

        # Check if user has access to this package
        if not get_authenticated_user().is_admin():
            # Check if user has access through any request
            with SessionHelper.get_session() as db:
                request_package_ops = RequestPackageOperations(db.session)
                has_access = request_package_ops.check_user_access(
                    package_id, get_authenticated_user().id
                )

            if not has_access:
                return jsonify({"error": "Access denied"}), 403

        # Trigger new scan
        scan_result = trivy_service.scan_package(package)

        return (
            jsonify(
                {
                    "package_id": package_id,
                    "package_name": package.name,
                    "package_version": package.version,
                    "scan_result": scan_result,
                }
            ),
            200,
        )

    except Exception as e:
        return handle_error(e, "Trigger security scan")


@package_bp.route("/processing/status", methods=["GET"])  # type: ignore[misc]
@auth_service.require_auth
def get_processing_status() -> ResponseReturnValue:
    """Get overall processing status and statistics."""
    try:
        # Count packages by status
        status_counts = {}
        for status in [
            "Checking Licence",
            "Downloading",
            "Security Scanning",
            "Pending Approval",
            "Rejected",
        ]:
            with SessionHelper.get_session() as db:
                package_ops = PackageOperations(db.session)
                count = package_ops.count_packages_by_status(status)
            status_counts[status] = count

        # Count total requests
        with SessionHelper.get_session() as db:
            request_ops = RequestOperations(db.session)
            total_requests = request_ops.count_total_requests()

            # Get recent activity (last 10 packages processed)
            package_ops = PackageOperations(db.session)
            recent_packages = package_ops.get_recent_packages(limit=10)

        recent_activity = []
        for package in recent_packages:
            recent_activity.append(
                {
                    "package_name": package.name,
                    "package_version": package.version,
                    "status": (
                        package.package_status.status
                        if package.package_status
                        else None
                    ),
                    "updated_at": (
                        package.package_status.updated_at.isoformat()
                        if package.package_status
                        and package.package_status.updated_at
                        else None
                    ),
                }
            )

        return (
            jsonify(
                {
                    "status_counts": status_counts,
                    "total_requests": total_requests,
                    "recent_activity": recent_activity,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ),
            200,
        )

    except Exception as e:
        return handle_error(e, "Get processing status")


@package_bp.route("/processing/retry", methods=["POST"])  # type: ignore[misc]
@auth_service.require_auth
def retry_failed_packages() -> ResponseReturnValue:
    """Retry failed packages, optionally for a specific request."""
    try:
        data = request.get_json() or {}
        request_id = data.get("request_id")

        # Only admins can retry packages
        if not get_authenticated_user().is_admin():
            return jsonify({"error": "Admin access required"}), 403

        # Build query for failed packages
        with SessionHelper.get_session() as db:
            package_ops = PackageOperations(db.session)
            failed_packages = package_ops.get_by_status("Rejected")

            if request_id:
                # Filter by request if specified
                failed_packages = [
                    p
                    for p in failed_packages
                    if any(
                        rp.request_id == request_id
                        for rp in p.request_packages
                    )
                ]

        if not failed_packages:
            return (
                jsonify({"message": "No failed packages found", "retried": 0}),
                200,
            )

        retried_count = 0
        for package in failed_packages:
            if package.package_status:
                package.package_status.status = "Checking Licence"
                package.package_status.updated_at = datetime.utcnow()
                retried_count += 1

        with SessionHelper.get_session() as db:
            db.commit()

        logger.info(f"Retried {retried_count} failed packages")
        return (
            jsonify(
                {
                    "message": f"Retried {retried_count} packages",
                    "retried": retried_count,
                    "request_id": request_id,
                }
            ),
            200,
        )

    except Exception as e:
        with SessionHelper.get_session() as db:
            db.rollback()
        return handle_error(e, "Retry failed packages")


@package_bp.route("/audit", methods=["GET"])  # type: ignore[misc]
@auth_service.require_auth
def get_audit_data() -> ResponseReturnValue:
    """Get audit data for approved packages."""
    try:
        # Only admins and approvers can view audit data
        if not (
            get_authenticated_user().is_admin()
            or get_authenticated_user().is_approver()
        ):
            return jsonify({"error": "Access denied"}), 403

        with SessionHelper.get_session() as db:
            # Query for approved packages with their approval information
            from database.models import User
            from sqlalchemy.orm import joinedload

            # Get all approved packages with their relationships
            approved_packages = (
                db.session.query(Package)
                .join(PackageStatus, Package.id == PackageStatus.package_id)
                .join(RequestPackage, Package.id == RequestPackage.package_id)
                .join(Request, RequestPackage.request_id == Request.id)
                .join(User, Request.requestor_id == User.id)
                .options(
                    joinedload(Package.package_status),
                    joinedload(Package.request_packages).joinedload(
                        RequestPackage.request
                    ),
                )
                .filter(PackageStatus.status == "Approved")
                .all()
            )

            audit_data = []
            for package in approved_packages:
                # Get the approver information
                approver = None
                if (
                    package.package_status
                    and package.package_status.approver_id
                ):
                    approver = (
                        db.session.query(User)
                        .filter(User.id == package.package_status.approver_id)
                        .first()
                    )

                # Get the original request information
                original_request = None
                original_requestor = None
                if package.request_packages:
                    # Get the first request (there should typically be only one)
                    request_package = package.request_packages[0]
                    original_request = request_package.request
                    original_requestor = original_request.requestor

                audit_data.append(
                    {
                        "package": {
                            "id": package.id,
                            "name": package.name,
                            "version": package.version,
                            "license_identifier": package.license_identifier,
                            "created_at": (
                                package.created_at.isoformat()
                                if package.created_at
                                else None
                            ),
                        },
                        "approval": {
                            "approved_at": (
                                package.package_status.updated_at.isoformat()
                                if package.package_status
                                and package.package_status.updated_at
                                else None
                            ),
                            "approver": (
                                {
                                    "id": approver.id,
                                    "username": approver.username,
                                    "full_name": approver.full_name,
                                }
                                if approver
                                else None
                            ),
                        },
                        "original_request": (
                            {
                                "id": original_request.id,
                                "application_name": original_request.application_name,
                                "application_version": original_request.version,
                                "requested_at": (
                                    original_request.created_at.isoformat()
                                    if original_request.created_at
                                    else None
                                ),
                                "requestor": (
                                    {
                                        "id": original_requestor.id,
                                        "username": original_requestor.username,
                                        "full_name": original_requestor.full_name,
                                    }
                                    if original_requestor
                                    else None
                                ),
                            }
                            if original_request
                            else None
                        ),
                    }
                )

        return jsonify({"audit_data": audit_data}), 200

    except Exception as e:
        return handle_error(e, "Get audit data")
