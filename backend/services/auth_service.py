import jwt
import os
from functools import wraps
from flask import request, jsonify, current_app
from models import User, db

class AuthService:
    def __init__(self):
        self.secret_key = os.getenv('FLASK_SECRET_KEY', 'mock-jwt-secret')
    
    def generate_token(self, user):
        """Generate JWT token for user"""
        payload = {
            'user_id': user.id,
            'username': user.username,
            'role': user.role,
            'sub': user.username,  # OAuth2 subject
            'aud': 'secure-package-manager',  # OAuth2 audience
            'iss': 'http://localhost:8081'  # OAuth2 issuer
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def verify_token(self, token):
        """Verify JWT token and return user"""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"=== TOKEN VERIFICATION DEBUG ===")
        logger.info(f"Token to verify: {token[:50]}...")
        logger.info(f"Secret key: {self.secret_key[:10]}...")
        
        try:
            # For OAuth2 tokens, we need to validate audience and issuer
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=['HS256'],
                audience='secure-package-manager',  # Validate audience
                issuer='http://localhost:8081'     # Validate issuer
            )
            logger.info(f"Token decoded successfully. Payload: {payload}")
            
            # Check if this is an OAuth2 token (has 'sub' field) or legacy token (has 'user_id')
            if 'sub' in payload:
                logger.info("OAuth2 token detected (has 'sub' field)")
                # OAuth2 token - create user from token payload
                username = payload.get('username')
                logger.info(f"Username from token: {username}")
                
                if username:
                    user = User.query.filter_by(username=username).first()
                    if not user:
                        logger.info(f"User {username} not found in database, creating new user")
                        # Create user from OAuth2 token if doesn't exist
                        user = User(
                            username=username,
                            email=payload.get('email', f'{username}@example.com'),
                            full_name=payload.get('full_name', username),
                            role=payload.get('role', 'user')
                        )
                        db.session.add(user)
                        db.session.commit()
                        logger.info(f"Created new user: {user.username} with role: {user.role}")
                    else:
                        logger.info(f"Found existing user: {user.username} with role: {user.role}")
                        # Update existing user with fresh OAuth2 token data
                        user.email = payload.get('email', user.email)
                        user.full_name = payload.get('full_name', user.full_name)
                        user.role = payload.get('role', user.role)
                        db.session.commit()
                        logger.info(f"Updated existing user: {user.username} with role: {user.role}")
                    return user
                else:
                    logger.error("No username found in OAuth2 token payload")
            elif 'user_id' in payload:
                logger.info("Legacy token detected (has 'user_id' field)")
                # Legacy token - lookup by user_id
                user_id = payload.get('user_id')
                logger.info(f"User ID from token: {user_id}")
                
                if user_id:
                    user = User.query.get(user_id)
                    if user:
                        logger.info(f"Found user by ID: {user.username} with role: {user.role}")
                        return user
                    else:
                        logger.error(f"No user found with ID: {user_id}")
                else:
                    logger.error("No user_id found in legacy token payload")
            else:
                logger.error("Token payload contains neither 'sub' nor 'user_id' field")
                
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
            if 'Authorization' in request.headers:
                auth_header = request.headers['Authorization']
                logger.info(f"Authorization header found: {auth_header[:50]}...")
                try:
                    token = auth_header.split(" ")[1]
                    logger.info(f"Extracted token: {token[:50]}...")
                except IndexError:
                    logger.error("Invalid token format - missing space separator")
                    return jsonify({'error': 'Invalid token format'}), 401
            else:
                logger.warning("No Authorization header found")
            
            if not token:
                logger.error("No token provided")
                return jsonify({'error': 'Token is missing'}), 401
            
            # Verify token
            logger.info("Verifying token...")
            user = self.verify_token(token)
            if not user:
                logger.error("Token verification failed - invalid or expired token")
                return jsonify({'error': 'Invalid or expired token'}), 401
            
            logger.info(f"Token verified successfully for user: {user.username} (ID: {user.id}, Role: {user.role})")
            
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
                return jsonify({'error': 'Admin privileges required'}), 403
            
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
            if not (request.user.role in ['approver', 'admin']):
                return jsonify({'error': 'Approver or Admin privileges required'}), 403
            
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
                    return jsonify({'error': f'Permission required: {permission}'}), 403
                
                return f(*args, **kwargs)
            
            return decorated_function
        return decorator
