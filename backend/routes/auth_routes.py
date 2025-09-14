from flask import Blueprint, request, jsonify
from services.auth_service import AuthService
from models import User, db
import logging

logger = logging.getLogger(__name__)

# Create blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# Initialize auth service
auth_service = AuthService()

@auth_bp.route('/login', methods=['POST'])
def login():
    """Mock login endpoint - in production this would integrate with ADFS"""
    try:
        logger.info(f"Login request received. Content-Type: {request.content_type}")
        logger.info(f"Raw data: {request.get_data()}")
        
        data = request.get_json()
        if not data:
            logger.error("No JSON data received")
            return jsonify({'error': 'No JSON data received'}), 400
            
        username = data.get('username')
        password = data.get('password')
        
        logger.info(f"Username: {username}, Password: {password}")
        
        # Mock authentication - in production this would validate against ADFS
        if username == 'admin' and password == 'admin':
            user = User.query.filter_by(username=username).first()
            if not user:
                user = User(username=username, email=f'{username}@example.com', full_name='Admin User', role='admin')
                db.session.add(user)
                db.session.commit()
            
            logger.info("Generating token...")
            token = auth_service.generate_token(user)
            logger.info("Token generated successfully")
            
            logger.info("Creating user dict...")
            user_dict = user.to_dict()
            logger.info(f"User dict created: {user_dict}")
            
            logger.info("Creating response...")
            response_data = {
                'token': token,
                'user': user_dict
            }
            logger.info("Response data created, returning...")
            return jsonify(response_data)
        else:
            return jsonify({'error': 'Invalid credentials'}), 401
            
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@auth_bp.route('/userinfo', methods=['GET'])
@auth_service.require_auth
def userinfo():
    """Get current user information"""
    try:
        logger.info(f"UserInfo request from user: {request.user.username}")
        return jsonify({
            'user': request.user.to_dict()
        })
    except Exception as e:
        logger.error(f"UserInfo error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
