import json
import logging

from flask import Blueprint, jsonify, request
from models import Application, Package, PackageReference, PackageRequest, db
from services.auth_service import AuthService
from services.package_service import PackageService

logger = logging.getLogger(__name__)

# Create blueprint
package_bp = Blueprint("packages", __name__, url_prefix="/api/packages")

# Initialize services
auth_service = AuthService()
package_service = PackageService()


@package_bp.route("/upload", methods=["POST"])
@auth_service.require_auth
def upload_package_lock():
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

        # Get or create application record
        application = _get_or_create_application(package_data)

        # Create package request
        package_request = _create_package_request(application, package_data)

        # Process packages and handle validation errors
        result = _process_package_validation(package_request, package_data)
        if isinstance(result, tuple):  # Error response
            return result

        return _create_success_response(package_request, application, package_data)

    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


def _validate_uploaded_file():
    """Validate the uploaded file"""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not file.filename.endswith(".json"):
        return jsonify({"error": "File must be a JSON file"}), 400

    return file


def _parse_package_lock_file(file):
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


def _get_or_create_application(package_data):
    """Get existing application or create a new one"""
    app_name = package_data.get("name", "Unknown Application")
    app_version = package_data.get("version", "1.0.0")

    # Check if application already exists
    application = Application.query.filter_by(
        name=app_name, version=app_version
    ).first()

    if not application:
        # Create new application record
        application = Application(
            name=app_name, version=app_version, created_by=request.user.id
        )
        db.session.add(application)
        db.session.commit()
    else:
        logger.info(f"Reusing existing application: {app_name} v{app_version}")

    return application


def _create_package_request(application, package_data):
    """Create a new package request record"""
    package_request = PackageRequest(
        application_id=application.id,
        requestor_id=request.user.id,
        package_lock_file=json.dumps(package_data),
        status="requested",
    )
    db.session.add(package_request)
    db.session.commit()
    return package_request


def _process_package_validation(package_request, package_data):
    """Process package validation and handle errors"""
    try:
        package_service.process_package_lock(package_request.id, package_data)
        return None  # Success
    except ValueError as ve:
        # Handle validation errors (unsupported lockfile version, wrong file type, etc.)
        logger.warning(f"Package validation error: {str(ve)}")
        # Update request status to rejected
        package_request.status = "rejected"
        db.session.commit()

        return (
            jsonify(
                {
                    "error": "Package validation failed",
                    "details": str(ve),
                    "request_id": package_request.id,
                }
            ),
            400,
        )


def _create_success_response(package_request, application, package_data):
    """Create success response for package upload"""
    app_name = package_data.get("name", "Unknown Application")
    app_version = package_data.get("version", "1.0.0")

    return jsonify(
        {
            "message": "Package lock file uploaded successfully",
            "request_id": package_request.id,
            "application": {
                "id": application.id,
                "name": app_name,
                "version": app_version,
            },
        }
    )


@package_bp.route("/requests/<int:request_id>", methods=["GET"])
@auth_service.require_auth
def get_package_request(request_id):
    """Get package request details"""
    try:
        package_request = PackageRequest.query.get_or_404(request_id)

        # Check if user has access to this request
        if (
            not request.user.is_admin()
            and package_request.requestor_id != request.user.id
        ):
            return jsonify({"error": "Access denied"}), 403

        packages = Package.query.filter_by(package_request_id=request_id).all()

        return jsonify(
            {
                "request": {
                    "id": package_request.id,
                    "status": package_request.status,
                    "total_packages": package_request.total_packages,
                    "validated_packages": package_request.validated_packages,
                    "created_at": package_request.created_at.isoformat(),
                    "application": {
                        "id": package_request.application.id,
                        "name": package_request.application.name,
                        "version": package_request.application.version,
                    },
                },
                "packages": [
                    {
                        "id": pkg.id,
                        "name": pkg.name,
                        "version": pkg.version,
                        "status": pkg.status,
                        "security_score": pkg.security_score,
                        "license_score": pkg.license_score,
                        "security_scan_status": pkg.security_scan_status,
                        "vulnerability_count": pkg.vulnerability_count,
                        "critical_vulnerabilities": pkg.critical_vulnerabilities,
                        "high_vulnerabilities": pkg.high_vulnerabilities,
                        "medium_vulnerabilities": pkg.medium_vulnerabilities,
                        "low_vulnerabilities": pkg.low_vulnerabilities,
                        "validation_errors": pkg.validation_errors or [],
                    }
                    for pkg in packages
                ],
            }
        )

    except Exception as e:
        logger.error(f"Get request error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@package_bp.route("/requests", methods=["GET"])
@auth_service.require_auth
def list_package_requests():
    """List package requests for the user"""
    try:
        if request.user.is_admin():
            requests = PackageRequest.query.all()
        else:
            requests = PackageRequest.query.filter_by(
                requestor_id=request.user.id
            ).all()

        result_requests = []
        for req in requests:
            # Get packages for this request (newly created packages)
            packages = Package.query.filter_by(package_request_id=req.id).all()

            # Get package references (all packages mentioned in package-lock.json)
            package_references = PackageReference.query.filter_by(
                package_request_id=req.id
            ).all()

            # Combine both for display
            all_packages = []

            # Add newly created packages
            for pkg in packages:
                all_packages.append(
                    {
                        "id": pkg.id,
                        "name": pkg.name,
                        "version": pkg.version,
                        "status": pkg.status,
                        "security_score": pkg.security_score,
                        "license_score": pkg.license_score,
                        "license_identifier": pkg.license_identifier,
                        "security_scan_status": pkg.security_scan_status,
                        "vulnerability_count": pkg.vulnerability_count,
                        "critical_vulnerabilities": pkg.critical_vulnerabilities,
                        "high_vulnerabilities": pkg.high_vulnerabilities,
                        "medium_vulnerabilities": pkg.medium_vulnerabilities,
                        "low_vulnerabilities": pkg.low_vulnerabilities,
                        "validation_errors": pkg.validation_errors or [],
                        "type": "new",
                    }
                )

            # Add existing validated packages that were referenced
            for ref in package_references:
                if ref.status == "already_validated" and ref.existing_package_id:
                    existing_pkg = Package.query.get(ref.existing_package_id)
                    if existing_pkg:
                        all_packages.append(
                            {
                                "id": existing_pkg.id,
                                "name": ref.name,
                                "version": ref.version,
                                "status": "already_validated",
                                "security_score": existing_pkg.security_score,
                                "license_identifier": existing_pkg.license_identifier,
                                "security_scan_status": existing_pkg.security_scan_status,
                                "vulnerability_count": existing_pkg.vulnerability_count,
                                "critical_vulnerabilities": existing_pkg.critical_vulnerabilities,
                                "high_vulnerabilities": existing_pkg.high_vulnerabilities,
                                "medium_vulnerabilities": existing_pkg.medium_vulnerabilities,
                                "low_vulnerabilities": existing_pkg.low_vulnerabilities,
                                "validation_errors": [],
                                "type": "existing",
                            }
                        )

            result_requests.append(
                {
                    "id": req.id,
                    "status": req.status,
                    "total_packages": req.total_packages,
                    "validated_packages": req.validated_packages,
                    "created_at": req.created_at.isoformat(),
                    "updated_at": req.updated_at.isoformat(),
                    "requestor": {
                        "id": req.requestor.id,
                        "username": req.requestor.username,
                        "full_name": req.requestor.full_name,
                    },
                    "application": {
                        "name": req.application.name,
                        "version": req.application.version,
                    },
                    "packages": all_packages,
                }
            )

        return jsonify({"requests": result_requests})

    except Exception as e:
        logger.error(f"List requests error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@package_bp.route("/<int:package_id>/security-scan/status", methods=["GET"])
@auth_service.require_auth
def get_package_security_scan_status(package_id):
    """Get security scan status for a package"""
    try:
        package = Package.query.get_or_404(package_id)

        # Check if user has access to this package
        if (
            not request.user.is_admin()
            and package.package_request.requestor_id != request.user.id
        ):
            return jsonify({"error": "Access denied"}), 403

        scan_status = package_service.get_package_security_scan_status(package_id)

        if not scan_status:
            return jsonify({"error": "No security scan found for this package"}), 404

        return jsonify(
            {
                "package_id": package_id,
                "package_name": package.name,
                "package_version": package.version,
                "scan_status": scan_status,
            }
        )

    except Exception as e:
        logger.error(f"Get security scan status error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@package_bp.route("/<int:package_id>/security-scan/report", methods=["GET"])
@auth_service.require_auth
def get_package_security_scan_report(package_id):
    """Get detailed security scan report for a package"""
    try:
        package = Package.query.get_or_404(package_id)

        # Check if user has access to this package
        if (
            not request.user.is_admin()
            and package.package_request.requestor_id != request.user.id
        ):
            return jsonify({"error": "Access denied"}), 403

        scan_report = package_service.get_package_security_scan_report(package_id)

        if not scan_report:
            return (
                jsonify({"error": "No security scan report found for this package"}),
                404,
            )

        return jsonify(
            {
                "package_id": package_id,
                "package_name": package.name,
                "package_version": package.version,
                "scan_report": scan_report,
            }
        )

    except Exception as e:
        logger.error(f"Get security scan report error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@package_bp.route("/<int:package_id>/security-scan/trigger", methods=["POST"])
@auth_service.require_auth
def trigger_package_security_scan(package_id):
    """Trigger a new security scan for a package"""
    try:
        package = Package.query.get_or_404(package_id)

        # Check if user has access to this package
        if (
            not request.user.is_admin()
            and package.package_request.requestor_id != request.user.id
        ):
            return jsonify({"error": "Access denied"}), 403

        # Trigger new scan
        scan_result = package_service.trivy_service.scan_package(package)

        return jsonify(
            {
                "package_id": package_id,
                "package_name": package.name,
                "package_version": package.version,
                "scan_result": scan_result,
            }
        )

    except Exception as e:
        logger.error(f"Trigger security scan error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
