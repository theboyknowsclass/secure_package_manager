import jwt
import os
from functools import wraps
from flask import request, jsonify, current_app
from models import User, db

class AuthService:
    def __init__(self):
        self.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')
    
    def generate_token(self, user):
        """Generate JWT token for user"""
        payload = {
            'user_id': user.id,
            'username': user.username,
            'is_admin': user.is_admin
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def verify_token(self, token):
        """Verify JWT token and return user"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            user_id = payload.get('user_id')
            if user_id:
                user = User.query.get(user_id)
                if user:
                    return user
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
        return None
    
    def require_auth(self, f):
        """Decorator to require authentication"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = None
            
            # Get token from header
            if 'Authorization' in request.headers:
                auth_header = request.headers['Authorization']
                try:
                    token = auth_header.split(" ")[1]
                except IndexError:
                    return jsonify({'error': 'Invalid token format'}), 401
            
            if not token:
                return jsonify({'error': 'Token is missing'}), 401
            
            # Verify token
            user = self.verify_token(token)
            if not user:
                return jsonify({'error': 'Invalid or expired token'}), 401
            
            # Add user to request context
            request.user = user
            return f(*args, **kwargs)
        
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
            if not request.user.is_admin:
                return jsonify({'error': 'Admin privileges required'}), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
