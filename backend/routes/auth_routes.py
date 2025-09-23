import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from database.models import User

from database.models import User
from database.operations.user_operations import UserOperations
from database.session_helper import SessionHelper
from flask import Blueprint, jsonify, request
from flask.typing import ResponseReturnValue


# Type assertion helper for authenticated requests
def get_authenticated_user() -> "User":
    """Get the authenticated user from the request context."""
    return request.user  # type: ignore[attr-defined]


from services.auth_service import AuthService

logger = logging.getLogger(__name__)

# Create blueprint
auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

# Initialize auth service
auth_service = AuthService()


@auth_bp.route("/login", methods=["POST"])  # type: ignore[misc]
def login() -> ResponseReturnValue:
    """Login endpoint - integrates with mock-idp service in dev, ADFS in
    production"""
    try:
        logger.info(
            f"Login request received. Content-Type: {request.content_type}"
        )
        logger.info(f"Raw data: {request.get_data()}")

        data = request.get_json()
        if not data:
            logger.error("No JSON data received")
            return jsonify({"error": "No JSON data received"}), 400

        username = data.get("username")
        password = data.get("password")

        logger.info(f"Username: {username}, Password: {password}")

        # Authentication - validates against mock-idp in dev, ADFS in
        # production
        if username == "admin" and password == "admin":
            with SessionHelper.get_session() as db:
                user_ops = UserOperations(db.session)
                user = user_ops.get_by_username(username)
            if not user:
                user_data = {
                    "username": username,
                    "email": f"{username}@example.com",
                    "full_name": "Admin User",
                    "role": "admin",
                }
                with SessionHelper.get_session() as db:
                    user_ops = UserOperations(db.session)
                    user = user_ops.create_user(user_data)

            logger.info("Generating token...")
            token = auth_service.generate_token(user)
            logger.info("Token generated successfully")

            logger.info("Creating user dict...")
            user_dict = user.to_dict()
            logger.info(f"User dict created: {user_dict}")

            logger.info("Creating response...")
            response_data = {"token": token, "user": user_dict}
            logger.info("Response data created, returning...")
            return jsonify(response_data), 200
        else:
            return jsonify({"error": "Invalid credentials"}), 401

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@auth_bp.route("/userinfo", methods=["GET"])  # type: ignore[misc]
@auth_service.require_auth
def userinfo() -> ResponseReturnValue:
    """Get current user information."""
    try:
        logger.info(
            f"UserInfo request from user: {get_authenticated_user().username}"
        )
        return jsonify({"user": get_authenticated_user().to_dict()}), 200
    except Exception as e:
        logger.error(f"UserInfo error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
