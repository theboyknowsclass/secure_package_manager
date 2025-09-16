import json
import logging
from datetime import datetime
from typing import Any, Dict, Union

from flask import Blueprint, jsonify, request
from flask.typing import ResponseReturnValue
from models import Package, Request, RequestPackage, db
from services.auth_service import AuthService
from services.package_service import PackageService

logger = logging.getLogger(__name__)

# Create blueprint
package_bp = Blueprint("packages", __name__, url_prefix="/api/packages")

# Initialize services
auth_service = AuthService()
package_service = PackageService()


@package_bp.route("/upload", methods=["POST"])  # type: ignore[misc]
@auth_service.require_auth
def upload_package_lock() -> ResponseReturnValue:
    """Upload and process package-lock.json file"""
    try:
        # Validate the uploaded file
        file = _validate_uploaded_file()
        if isinstance(file, tuple):  # Error response
            return file

        # Parse and validate the JSON content
        package_data = _parse_package_lock_file(file)
        if isinstance(package_data, tuple):  # Error response
            return package_data

        # Create request record
        request_record = _create_request(package_data)

        # Process packages and handle validation errors
        result = _process_package_validation(request_record, package_data)
        if isinstance(result, tuple):  # Error response
            return result

        return _create_success_response(request_record, package_data)

    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


def _validate_uploaded_file() -> Union[Any, ResponseReturnValue]:
    """Validate the uploaded file"""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not file.filename.endswith(".json"):
        return jsonify({"error": "File must be a JSON file"}), 400

    return file


def _parse_package_lock_file(file: Any) -> Union[Dict[str, Any], ResponseReturnValue]:
    """Parse and validate the package-lock.json file"""
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
                    "details": "This file does not appear to be a package-lock.json file. Missing required fields.",
                }
            ),
            400,
        )

    return package_data


def _create_request(package_data: Dict[str, Any]) -> Request:
    """Create a new request record"""
    app_name = package_data.get("name", "Unknown Application")
    app_version = package_data.get("version", "1.0.0")

    request_record = Request(
        application_name=app_name,
        version=app_version,
        requestor_id=request.user.id,
        package_lock_file=json.dumps(package_data),
    )
    db.session.add(request_record)
    db.session.commit()
    return request_record


def _process_package_validation(
    request_record: Request, package_data: Dict[str, Any]
) -> ResponseReturnValue | None:
    """Process package validation and handle errors"""
    try:
        package_service.process_package_lock(request_record.id, package_data)
        return None  # Success
    except ValueError as ve:
        # Handle validation errors (unsupported lockfile version, wrong file type, etc.)
        logger.warning(f"Package validation error: {str(ve)}")

        # Update package statuses to reflect error
        packages = (
            db.session.query(Package)
            .join(RequestPackage)
            .filter(RequestPackage.request_id == request_record.id)
            .all()
        )

        for package in packages:
            if package.package_status:
                package.package_status.status = "Rejected"
                package.package_status.updated_at = datetime.utcnow()

        db.session.commit()

        return (
            jsonify(
                {
                    "error": "Package validation failed",
                    "details": str(ve),
                    "request_id": request_record.id,
                }
            ),
            400,
        )


def _create_success_response(
    request_record: Request,
    package_data: Dict[str, Any],
) -> ResponseReturnValue:
    """Create success response for package upload"""
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


@package_bp.route("/requests/<int:request_id>", methods=["GET"])  # type: ignore[misc]
@auth_service.require_auth
def get_package_request(request_id: int) -> ResponseReturnValue:
    """Get package request details"""
    try:
        request_record = Request.query.get_or_404(request_id)

        # Check if user has access to this request
        if (
            not request.user.is_admin()
            and request_record.requestor_id != request.user.id
        ):
            return jsonify({"error": "Access denied"}), 403

        # Get packages for this request
        packages = (
            db.session.query(Package)
            .join(RequestPackage)
            .filter(RequestPackage.request_id == request_id)
            .all()
        )

        # Get request status from status manager
        from services.package_request_status_manager import PackageRequestStatusManager

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
                                else "Requested"
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
                        }
                        for pkg in packages
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
    """List package requests for the user"""
    try:
        if request.user.is_admin():
            requests = Request.query.all()
        else:
            requests = Request.query.filter_by(requestor_id=request.user.id).all()

        result_requests = []
        for req in requests:
            # Get request status from status manager (this already includes package counts)
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
                    "completion_percentage": status_summary["completion_percentage"],
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


@package_bp.route("/<int:package_id>/security-scan/status", methods=["GET"])  # type: ignore[misc]
@auth_service.require_auth
def get_package_security_scan_status(package_id: int) -> ResponseReturnValue:
    """Get security scan status for a package"""
    try:
        package = Package.query.get_or_404(package_id)

        # Check if user has access to this package
        if not request.user.is_admin():
            # Check if user has access through any request
            has_access = (
                db.session.query(RequestPackage)
                .join(Request)
                .filter(
                    RequestPackage.package_id == package_id,
                    Request.requestor_id == request.user.id,
                )
                .first()
            )

            if not has_access:
                return jsonify({"error": "Access denied"}), 403

        scan_status = package_service.get_package_security_scan_status(package_id)

        if not scan_status:
            return jsonify({"error": "No security scan found for this package"}), 404

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


@package_bp.route("/<int:package_id>/security-scan/report", methods=["GET"])  # type: ignore[misc]
@auth_service.require_auth
def get_package_security_scan_report(package_id: int) -> ResponseReturnValue:
    """Get detailed security scan report for a package"""
    try:
        package = Package.query.get_or_404(package_id)

        # Check if user has access to this package
        if not request.user.is_admin():
            # Check if user has access through any request
            has_access = (
                db.session.query(RequestPackage)
                .join(Request)
                .filter(
                    RequestPackage.package_id == package_id,
                    Request.requestor_id == request.user.id,
                )
                .first()
            )

            if not has_access:
                return jsonify({"error": "Access denied"}), 403

        scan_report = package_service.get_package_security_scan_report(package_id)

        if not scan_report:
            return (
                jsonify({"error": "No security scan report found for this package"}),
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


@package_bp.route("/<int:package_id>/security-scan/trigger", methods=["POST"])  # type: ignore[misc]
@auth_service.require_auth
def trigger_package_security_scan(package_id: int) -> ResponseReturnValue:
    """Trigger a new security scan for a package"""
    try:
        package = Package.query.get_or_404(package_id)

        # Check if user has access to this package
        if not request.user.is_admin():
            # Check if user has access through any request
            has_access = (
                db.session.query(RequestPackage)
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
        scan_result = package_service.trivy_service.scan_package(package)

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
