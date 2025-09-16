import logging

from flask import Blueprint, jsonify, request
from flask.typing import ResponseReturnValue
from models import (
    AuditLog,
    Package,
    PackageStatus,
    Request,
    RequestPackage,
    db,
)
from services.auth_service import AuthService
from services.package_service import PackageService

logger = logging.getLogger(__name__)

# Create blueprint
approver_bp = Blueprint("approver", __name__, url_prefix="/api/approver")

# Initialize services
auth_service = AuthService()
package_service = PackageService()


# Package Approval Routes
@approver_bp.route("/packages/approve/<int:package_id>", methods=["POST"])  # type: ignore[misc]
@auth_service.require_admin
def approve_package(package_id: int) -> ResponseReturnValue:
    """Approve a package and automatically publish it"""
    try:
        package = Package.query.get_or_404(package_id)

        if not package.package_status:
            return jsonify({"error": "Package status not found"}), 404

        if package.package_status.status != "Pending Approval":
            return (
                jsonify(
                    {
                        "error": "Package must be pending approval before it can be approved"
                    }
                ),
                400,
            )

        # Approve the package
        package.package_status.status = "Approved"
        db.session.commit()

        # Automatically publish to secure repository
        success = package_service.publish_to_secure_repo(package)

        if success:
            # Log the approval and publishing
            audit_log = AuditLog(
                user_id=request.user.id,
                action="approve_and_publish_package",
                resource_type="package",
                resource_id=package.id,
                details=f"Package {package.name}@{package.version} approved and automatically published",
            )
            db.session.add(audit_log)
            db.session.commit()

            return jsonify({"message": "Package approved and published successfully"})
        else:
            return jsonify({"error": "Package approved but failed to publish"}), 500

    except Exception as e:
        logger.error(f"Approve package error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@approver_bp.route("/packages/reject/<int:package_id>", methods=["POST"])  # type: ignore[misc]
@auth_service.require_admin
def reject_package(package_id: int) -> ResponseReturnValue:
    """Reject a package"""
    try:
        package = Package.query.get_or_404(package_id)

        if not package.package_status:
            return jsonify({"error": "Package status not found"}), 404

        if package.package_status.status in ["Approved"]:
            return (
                jsonify({"error": "Cannot reject an already approved package"}),
                400,
            )

        # Get rejection reason from request body
        data = request.get_json() or {}
        rejection_reason = data.get("reason", "Package rejected by administrator")

        # Reject the package
        package.package_status.status = "Rejected"
        db.session.commit()

        # Log the rejection
        audit_log = AuditLog(
            user_id=request.user.id,
            action="reject_package",
            resource_type="package",
            resource_id=package.id,
            details=f"Package {package.name}@{package.version} rejected: {rejection_reason}",
        )
        db.session.add(audit_log)
        db.session.commit()

        return jsonify({"message": "Package rejected successfully"})
    except Exception as e:
        logger.error(f"Reject package error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@approver_bp.route("/packages/publish/<int:package_id>", methods=["POST"])  # type: ignore[misc]
@auth_service.require_admin
def publish_package(package_id: int) -> ResponseReturnValue:
    """Publish an approved package to the secure repository"""
    try:
        package = Package.query.get_or_404(package_id)

        if not package.package_status:
            return jsonify({"error": "Package status not found"}), 404

        if package.package_status.status != "Approved":
            return jsonify({"error": "Package must be approved before publishing"}), 400

        # Publish to secure repository
        success = package_service.publish_to_secure_repo(package)

        if success:
            # Log the action
            audit_log = AuditLog(
                user_id=request.user.id,
                action="publish_package",
                resource_type="package",
                resource_id=package.id,
                details=f"Package {package.name}@{package.version} published to secure repo",
            )
            db.session.add(audit_log)
            db.session.commit()

            return jsonify({"message": "Package published successfully"})
        else:
            return jsonify({"error": "Failed to publish package"}), 500

    except Exception as e:
        logger.error(f"Publish package error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@approver_bp.route("/packages/validated", methods=["GET"])  # type: ignore[misc]
@auth_service.require_admin
def get_validated_packages() -> ResponseReturnValue:
    """Get all packages ready for admin review (pending approval)"""
    try:
        packages = (
            db.session.query(Package)
            .join(PackageStatus)
            .filter(PackageStatus.status == "Pending Approval")
            .all()
        )

        # Handle case when no packages exist
        if not packages:
            return jsonify({"packages": []})

        # Build response with proper error handling for relationships
        package_list = []
        for pkg in packages:
            try:
                # Get request information for this package
                request_package = RequestPackage.query.filter_by(
                    package_id=pkg.id
                ).first()
                request_data = None

                if request_package:
                    request_record = Request.query.get(request_package.request_id)
                    if request_record:
                        request_data = {
                            "id": request_record.id,
                            "application_name": request_record.application_name,
                            "version": request_record.version,
                        }

                package_list.append(
                    {
                        "id": pkg.id,
                        "name": pkg.name,
                        "version": pkg.version,
                        "security_score": pkg.package_status.security_score or 0,
                        "license_score": pkg.package_status.license_score,
                        "license_identifier": pkg.license_identifier or "Unknown",
                        "security_scan_status": pkg.package_status.security_scan_status,
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
        return jsonify({"error": "Internal server error"}), 500
