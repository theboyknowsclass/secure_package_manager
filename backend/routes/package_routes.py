import json
import logging
from datetime import datetime
from typing import Any, Dict, Union

from database.flask_utils import get_db_operations
from database.models import (
    AuditLog,
    Package,
    PackageStatus,
    Request,
    RequestPackage,
    SecurityScan,
)
from flask import Blueprint, jsonify, request
from flask.typing import ResponseReturnValue
from services.auth_service import AuthService
from services.trivy_service import TrivyService

logger = logging.getLogger(__name__)

# Create blueprint
package_bp = Blueprint("packages", __name__, url_prefix="/api/packages")

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
        request_record = _create_request_with_blob(package_data)

        return _create_success_response(request_record, package_data)

    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


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


def _create_request_with_blob(package_data: Dict[str, Any]) -> Request:
    """Create a new request record with raw blob."""
    app_name = package_data.get("name", "Unknown Application")
    app_version = package_data.get("version", "1.0.0")

    request_record = Request(
        application_name=app_name,
        version=app_version,
        requestor_id=request.user.id,
        raw_request_blob=json.dumps(package_data),  # Store raw JSON blob
    )
    with get_db_operations() as ops:
        ops.add(request_record)
        ops.commit()

        # Log the request creation
        audit_log = AuditLog(
            user_id=request.user.id,
            action="create_request",
            resource_type="request",
            resource_id=request_record.id,
            details=f"Created package request for {app_name}@{app_version}",
        )
        ops.add(audit_log)
        ops.commit()

    return request_record


def _create_success_response(
    request_record: Request,
    package_data: Dict[str, Any],
) -> ResponseReturnValue:
    """Create success response for package upload."""
    app_name = package_data.get("name", "Unknown Application")
    app_version = package_data.get("version", "1.0.0")

    return (
        jsonify(
            {
                "message": "Package lock file uploaded successfully",
                "request_id": request_record.id,
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
        with get_db_operations() as ops:
            request_record = (
                ops.query(Request).filter(Request.id == request_id).first()
            )
            if not request_record:
                return jsonify({"error": "Request not found"}), 404

        # Check if user has access to this request
        if (
            not request.user.is_admin()
            and request_record.requestor_id != request.user.id
        ):
            return jsonify({"error": "Access denied"}), 403

        # Get packages for this request with their creation context and scan
        # results
        with get_db_operations() as ops:
            packages_with_context = (
                ops.query(Package, RequestPackage, SecurityScan)
                .join(RequestPackage)
                .outerjoin(
                    SecurityScan
                )  # LEFT JOIN - allows null scan results
                .filter(RequestPackage.request_id == request_id)
                .all()
            )

        # Get request status from status manager
        from services.package_request_status_manager import (
            PackageRequestStatusManager,
        )

        status_manager = PackageRequestStatusManager()
        status_summary = status_manager.get_request_status_summary(request_id)

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
                    "packages": [
                        {
                            "id": pkg.id,
                            "name": pkg.name,
                            "version": pkg.version,
                            "status": (
                                pkg.package_status.status
                                if pkg.package_status
                                else "Submitted"
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
                            "type": rp.package_type,
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
                        for pkg, rp, scan in packages_with_context
                    ],
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Get request error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@package_bp.route("/requests", methods=["GET"])  # type: ignore[misc]
@auth_service.require_auth
def list_package_requests() -> ResponseReturnValue:
    """List package requests for the user."""
    try:
        with get_db_operations() as ops:
            if request.user.is_admin():
                requests = ops.query(Request).all()
            else:
                requests = (
                    ops.query(Request)
                    .filter_by(requestor_id=request.user.id)
                    .all()
                )

        result_requests = []
        for req in requests:
            # Get request status from status manager (this already includes
            # package counts)
            from services.package_request_status_manager import (
                PackageRequestStatusManager,
            )

            status_manager = PackageRequestStatusManager()
            status_summary = status_manager.get_request_status_summary(req.id)

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
        logger.error(f"List requests error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@package_bp.route(
    "/<int:package_id>/security-scan/status", methods=["GET"]
)  # type: ignore[misc]
@auth_service.require_auth
def get_package_security_scan_status(package_id: int) -> ResponseReturnValue:
    """Get security scan status for a package."""
    try:
        with get_db_operations() as ops:
            package = (
                ops.query(Package).filter(Package.id == package_id).first()
            )
            if not package:
                return jsonify({"error": "Package not found"}), 404

        # Check if user has access to this package
        if not request.user.is_admin():
            # Check if user has access through any request
            with get_db_operations() as ops:
                has_access = (
                    ops.query(RequestPackage)
                    .join(Request)
                    .filter(
                        RequestPackage.package_id == package_id,
                        Request.requestor_id == request.user.id,
                    )
                    .first()
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
        logger.error(f"Get security scan status error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@package_bp.route(
    "/<int:package_id>/security-scan/report", methods=["GET"]
)  # type: ignore[misc]
@auth_service.require_auth
def get_package_security_scan_report(package_id: int) -> ResponseReturnValue:
    """Get detailed security scan report for a package."""
    try:
        with get_db_operations() as ops:
            package = (
                ops.query(Package).filter(Package.id == package_id).first()
            )
            if not package:
                return jsonify({"error": "Package not found"}), 404

        # Check if user has access to this package
        if not request.user.is_admin():
            # Check if user has access through any request
            with get_db_operations() as ops:
                has_access = (
                    ops.query(RequestPackage)
                    .join(Request)
                    .filter(
                        RequestPackage.package_id == package_id,
                        Request.requestor_id == request.user.id,
                    )
                    .first()
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
        logger.error(f"Get security scan report error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@package_bp.route(
    "/<int:package_id>/security-scan/trigger", methods=["POST"]
)  # type: ignore[misc]
@auth_service.require_auth
def trigger_package_security_scan(package_id: int) -> ResponseReturnValue:
    """Trigger a new security scan for a package."""
    try:
        with get_db_operations() as ops:
            package = (
                ops.query(Package).filter(Package.id == package_id).first()
            )
            if not package:
                return jsonify({"error": "Package not found"}), 404

        # Check if user has access to this package
        if not request.user.is_admin():
            # Check if user has access through any request
            with get_db_operations() as ops:
                has_access = (
                    ops.query(RequestPackage)
                    .join(Request)
                    .filter(
                        RequestPackage.package_id == package_id,
                        Request.requestor_id == request.user.id,
                    )
                    .first()
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
        logger.error(f"Trigger security scan error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@package_bp.route("/processing/status", methods=["GET"])  # type: ignore[misc]
@auth_service.require_auth
def get_processing_status() -> ResponseReturnValue:
    """Get overall processing status and statistics."""
    try:
        # Count packages by status
        status_counts = {}
        for status in [
            "Submitted",
            "Parsed",
            "Checking Licence",
            "Downloading",
            "Security Scanning",
            "Pending Approval",
            "Rejected",
        ]:
            with get_db_operations() as ops:
                count = (
                    ops.query(Package)
                    .join(PackageStatus)
                    .filter(PackageStatus.status == status)
                    .count()
                )
            status_counts[status] = count

        # Count total requests
        with get_db_operations() as ops:
            total_requests = ops.query(Request).count()

            # Get recent activity (last 10 packages processed)
            recent_packages = (
                ops.query(Package, PackageStatus)
                .join(PackageStatus)
                .filter(PackageStatus.updated_at.isnot(None))
                .order_by(PackageStatus.updated_at.desc())
                .limit(10)
                .all()
            )

        recent_activity = []
        for package, status in recent_packages:
            recent_activity.append(
                {
                    "package_name": package.name,
                    "package_version": package.version,
                    "status": status.status,
                    "updated_at": (
                        status.updated_at.isoformat()
                        if status.updated_at
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
        logger.error(f"Get processing status error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@package_bp.route("/processing/retry", methods=["POST"])  # type: ignore[misc]
@auth_service.require_auth
def retry_failed_packages() -> ResponseReturnValue:
    """Retry failed packages, optionally for a specific request."""
    try:
        data = request.get_json() or {}
        request_id = data.get("request_id")

        # Only admins can retry packages
        if not request.user.is_admin():
            return jsonify({"error": "Admin access required"}), 403

        # Build query for failed packages
        with get_db_operations() as ops:
            query = (
                ops.query(Package)
                .join(PackageStatus)
                .filter(PackageStatus.status == "Rejected")
            )

        if request_id:
            query = query.join(RequestPackage).filter(
                RequestPackage.request_id == request_id
            )

        failed_packages = query.all()

        if not failed_packages:
            return (
                jsonify({"message": "No failed packages found", "retried": 0}),
                200,
            )

        retried_count = 0
        for package in failed_packages:
            if package.package_status:
                package.package_status.status = "Submitted"
                package.package_status.updated_at = datetime.utcnow()
                retried_count += 1

        with get_db_operations() as ops:
            ops.commit()

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
        logger.error(f"Retry failed packages error: {str(e)}")
        with get_db_operations() as ops:
            ops.rollback()
        return jsonify({"error": "Internal server error"}), 500
