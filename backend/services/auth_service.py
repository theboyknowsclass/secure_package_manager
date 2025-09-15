from functools import wraps

import jwt
from config.constants import JWT_SECRET, OAUTH_AUDIENCE, OAUTH_ISSUER
from flask import jsonify, request
from models import User, db


class AuthService:
    def __init__(self):
        self.secret_key = JWT_SECRET

    def generate_token(self, user):
        """Generate JWT token for user"""
        payload = {
            "user_id": user.id,
            "username": user.username,
            "role": user.role,
            "sub": user.username,  # OAuth2 subject
            "aud": OAUTH_AUDIENCE,  # OAuth2 audience
            "iss": OAUTH_ISSUER,  # OAuth2 issuer
        }
        return jwt.encode(payload, self.secret_key, algorithm="HS256")

    def verify_token(self, token):
        """Verify JWT token and return user"""
        import logging

        logger = logging.getLogger(__name__)

        logger.info("=== TOKEN VERIFICATION DEBUG ===")
        logger.info(f"Token to verify: {token[:50]}...")
        logger.info(f"Secret key: {self.secret_key[:10]}...")

        try:
            # Decode and validate the JWT token
            payload = self._decode_jwt_token(token)
            if not payload:
                return None

            # Get user from token payload
            user = self._get_user_from_token(payload)
            if user:
                return user

        except jwt.ExpiredSignatureError as e:
            logger.error(f"Token expired: {str(e)}")
            return None
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid token: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during token verification: {str(e)}")
            return None

        logger.error("Token verification failed - no valid user found")
        return None

    def _decode_jwt_token(self, token):
        """Decode and validate JWT token"""
        import logging

        logger = logging.getLogger(__name__)

        # For OAuth2 tokens, we need to validate audience and issuer
        payload = jwt.decode(
            token,
            self.secret_key,
            algorithms=["HS256"],
            audience=OAUTH_AUDIENCE,
            issuer=OAUTH_ISSUER,
        )
        logger.info(f"Token decoded successfully. Payload: {payload}")
        return payload

    def _get_user_from_token(self, payload):
        """Get user from token payload (OAuth2 or legacy)"""
        import logging

        logger = logging.getLogger(__name__)

        # Check if this is an OAuth2 token (has 'sub' field) or legacy token (has 'user_id')
        if "sub" in payload:
            return self._handle_oauth2_token(payload)
        elif "user_id" in payload:
            return self._handle_legacy_token(payload)
        else:
            logger.error("Token payload contains neither 'sub' nor 'user_id' field")
            return None

    def _handle_oauth2_token(self, payload):
        """Handle OAuth2 token and return user"""
        import logging

        logger = logging.getLogger(__name__)

        logger.info("OAuth2 token detected (has 'sub' field)")
        username = payload.get("username")
        logger.info(f"Username from token: {username}")

        if not username:
            logger.error("No username found in OAuth2 token payload")
            return None

        user = User.query.filter_by(username=username).first()
        if not user:
            user = self._create_user_from_oauth2_payload(payload, username)
        else:
            user = self._update_user_from_oauth2_payload(user, payload)

        return user

    def _handle_legacy_token(self, payload):
        """Handle legacy token and return user"""
        import logging

        logger = logging.getLogger(__name__)

        logger.info("Legacy token detected (has 'user_id' field)")
        user_id = payload.get("user_id")
        logger.info(f"User ID from token: {user_id}")

        if not user_id:
            logger.error("No user_id found in legacy token payload")
            return None

        user = User.query.get(user_id)
        if user:
            logger.info(f"Found user by ID: {user.username} with role: {user.role}")
            return user
        else:
            logger.error(f"No user found with ID: {user_id}")
            return None

    def _create_user_from_oauth2_payload(self, payload, username):
        """Create new user from OAuth2 token payload"""
        import logging

        logger = logging.getLogger(__name__)

        logger.info(f"User {username} not found in database, creating new user")
        user = User(
            username=username,
            email=payload.get("email", f"{username}@example.com"),
            full_name=payload.get("full_name", username),
            role=payload.get("role", "user"),
        )
        db.session.add(user)
        db.session.commit()
        logger.info(f"Created new user: {user.username} with role: {user.role}")
        return user

    def _update_user_from_oauth2_payload(self, user, payload):
        """Update existing user with OAuth2 token data"""
        import logging

        logger = logging.getLogger(__name__)

        logger.info(f"Found existing user: {user.username} with role: {user.role}")
        # Update existing user with fresh OAuth2 token data
        user.email = payload.get("email", user.email)
        user.full_name = payload.get("full_name", user.full_name)
        user.role = payload.get("role", user.role)
        db.session.commit()
        logger.info(f"Updated existing user: {user.username} with role: {user.role}")
        return user

    def require_auth(self, f):
        """Decorator to require authentication"""

        @wraps(f)
        def decorated_function(*args, **kwargs):
            import logging

            logger = logging.getLogger(__name__)

            logger.info(f"=== AUTH DEBUG: require_auth called for {f.__name__} ===")
            logger.info(f"Request URL: {request.url}")
            logger.info(f"Request method: {request.method}")
            logger.info(f"Request headers: {dict(request.headers)}")

            token = None

            # Get token from header
            if "Authorization" in request.headers:
                auth_header = request.headers["Authorization"]
                logger.info(f"Authorization header found: {auth_header[:50]}...")
                try:
                    token = auth_header.split(" ")[1]
                    logger.info(f"Extracted token: {token[:50]}...")
                except IndexError:
                    logger.error("Invalid token format - missing space separator")
                    return jsonify({"error": "Invalid token format"}), 401
            else:
                logger.warning("No Authorization header found")

            if not token:
                logger.error("No token provided")
                return jsonify({"error": "Token is missing"}), 401

            # Verify token
            logger.info("Verifying token...")
            user = self.verify_token(token)
            if not user:
                logger.error("Token verification failed - invalid or expired token")
                return jsonify({"error": "Invalid or expired token"}), 401

            logger.info(
                f"Token verified successfully for user: {user.username} (ID: {user.id}, Role: {user.role})"
            )

            # Add user to request context
            request.user = user
            logger.info("User added to request context")

            try:
                result = f(*args, **kwargs)
                logger.info(f"Endpoint {f.__name__} executed successfully")
                return result
            except Exception as e:
                logger.error(f"Error in endpoint {f.__name__}: {str(e)}")
                raise

        return decorated_function

    def require_admin(self, f):
        """Decorator to require admin privileges"""

        @wraps(f)
        def decorated_function(*args, **kwargs):
            # First check authentication
            auth_result = self.require_auth(f)(*args, **kwargs)

            # If authentication failed, return the error
            if isinstance(auth_result, tuple) and len(auth_result) == 2:
                if auth_result[1] != 200:
                    return auth_result

            # Check if user is admin
            if not request.user.is_admin():
                return jsonify({"error": "Admin privileges required"}), 403

            return f(*args, **kwargs)

        return decorated_function

    def require_approver(self, f):
        """Decorator to require approver or admin privileges"""

        @wraps(f)
        def decorated_function(*args, **kwargs):
            # First check authentication
            auth_result = self.require_auth(f)(*args, **kwargs)

            # If authentication failed, return the error
            if isinstance(auth_result, tuple) and len(auth_result) == 2:
                if auth_result[1] != 200:
                    return auth_result

            # Check if user is approver or admin
            if not (request.user.role in ["approver", "admin"]):
                return jsonify({"error": "Approver or Admin privileges required"}), 403

            return f(*args, **kwargs)

        return decorated_function

    def require_permission(self, permission):
        """Decorator factory to require specific permission"""

        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                # First check authentication
                auth_result = self.require_auth(f)(*args, **kwargs)

                # If authentication failed, return the error
                if isinstance(auth_result, tuple) and len(auth_result) == 2:
                    if auth_result[1] != 200:
                        return auth_result

                # Check if user has permission
                if not request.user.has_permission(permission):
                    return jsonify({"error": f"Permission required: {permission}"}), 403

                return f(*args, **kwargs)

            return decorated_function

        return decorator
