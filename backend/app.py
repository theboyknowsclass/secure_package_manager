from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
import json
import requests
import hashlib
from datetime import datetime
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize extensions
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import models first (they create the db instance)
from models import db, User, Application, PackageRequest, Package, PackageValidation, PackageReference, AuditLog

# Now initialize the database with the app
db.init_app(app)

# Import services after database is initialized
from services.package_service import PackageService
from services.auth_service import AuthService
from services.validation_service import ValidationService

# Initialize services AFTER models are imported
package_service = PackageService()
auth_service = AuthService()
validation_service = ValidationService()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Mock login endpoint - in production this would integrate with ADFS"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        # Mock authentication - in production this would validate against ADFS
        if username == 'admin' and password == 'admin':
            user = User.query.filter_by(username=username).first()
            if not user:
                user = User(username=username, email=f'{username}@example.com', full_name='Admin User', is_admin=True)
                db.session.add(user)
                db.session.commit()
            
            token = auth_service.generate_token(user)
            return jsonify({
                'token': token,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'full_name': user.full_name,
                    'is_admin': user.is_admin
                }
            })
        else:
            return jsonify({'error': 'Invalid credentials'}), 401
            
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/packages/upload', methods=['POST'])
@auth_service.require_auth
def upload_package_lock():
    """Upload and process package-lock.json file"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.endswith('.json'):
            return jsonify({'error': 'File must be a JSON file'}), 400
        
        # Parse package-lock.json
        try:
            package_data = json.load(file)
        except json.JSONDecodeError:
            return jsonify({'error': 'Invalid JSON file'}), 400
        
        # Basic validation that this looks like a package-lock.json
        if not isinstance(package_data, dict):
            return jsonify({'error': 'File must contain a valid JSON object'}), 400
        
        if 'lockfileVersion' not in package_data:
            return jsonify({
                'error': 'Invalid file format',
                'details': 'This file does not appear to be a package-lock.json file. Missing required fields.'
            }), 400
        
        # Extract application info
        app_name = package_data.get('name', 'Unknown Application')
        app_version = package_data.get('version', '1.0.0')
        
        # Check if application already exists
        application = Application.query.filter_by(
            name=app_name,
            version=app_version
        ).first()
        
        if not application:
            # Create new application record
            application = Application(
                name=app_name,
                version=app_version,
                created_by=request.user.id
            )
            db.session.add(application)
            db.session.commit()
        else:
            logger.info(f"Reusing existing application: {app_name} v{app_version}")
        
        # Create package request
        package_request = PackageRequest(
            application_id=application.id,
            requestor_id=request.user.id,
            package_lock_file=json.dumps(package_data),
            status='requested'
        )
        db.session.add(package_request)
        db.session.commit()
        
        # Process packages asynchronously
        try:
            package_service.process_package_lock(package_request.id, package_data)
        except ValueError as ve:
            # Handle validation errors (unsupported lockfile version, wrong file type, etc.)
            logger.warning(f"Package validation error: {str(ve)}")
            # Update request status to rejected
            package_request.status = 'rejected'
            db.session.commit()
            
            return jsonify({
                'error': 'Package validation failed',
                'details': str(ve),
                'request_id': package_request.id
            }), 400
        
        return jsonify({
            'message': 'Package lock file uploaded successfully',
            'request_id': package_request.id,
            'application': {
                'id': application.id,
                'name': app_name,
                'version': app_version
            }
        })
        
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/packages/requests/<int:request_id>', methods=['GET'])
@auth_service.require_auth
def get_package_request(request_id):
    """Get package request details"""
    try:
        package_request = PackageRequest.query.get_or_404(request_id)
        
        # Check if user has access to this request
        if not request.user.is_admin and package_request.requestor_id != request.user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        packages = Package.query.filter_by(package_request_id=request_id).all()
        
        return jsonify({
            'request': {
                'id': package_request.id,
                'status': package_request.status,
                'total_packages': package_request.total_packages,
                'validated_packages': package_request.validated_packages,
                'created_at': package_request.created_at.isoformat(),
                'application': {
                    'id': package_request.application.id,
                    'name': package_request.application.name,
                    'version': package_request.application.version
                }
            },
            'packages': [{
                'id': pkg.id,
                'name': pkg.name,
                'version': pkg.version,
                'status': pkg.status,
                'security_score': pkg.security_score,
                'validation_errors': pkg.validation_errors or []
            } for pkg in packages]
        })
        
    except Exception as e:
        logger.error(f"Get request error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/packages/requests', methods=['GET'])
@auth_service.require_auth
def list_package_requests():
    """List package requests for the user"""
    try:
        if request.user.is_admin:
            requests = PackageRequest.query.all()
        else:
            requests = PackageRequest.query.filter_by(requestor_id=request.user.id).all()
        
        result_requests = []
        for req in requests:
            # Get packages for this request (newly created packages)
            packages = Package.query.filter_by(package_request_id=req.id).all()
            
            # Get package references (all packages mentioned in package-lock.json)
            package_references = PackageReference.query.filter_by(package_request_id=req.id).all()
            
            # Combine both for display
            all_packages = []
            
            # Add newly created packages
            for pkg in packages:
                all_packages.append({
                    'id': pkg.id,
                    'name': pkg.name,
                    'version': pkg.version,
                    'status': pkg.status,
                    'security_score': pkg.security_score,
                    'validation_errors': pkg.validation_errors or [],
                    'type': 'new'
                })
            
            # Add existing validated packages that were referenced
            for ref in package_references:
                if ref.status == 'already_validated' and ref.existing_package_id:
                    existing_pkg = Package.query.get(ref.existing_package_id)
                    if existing_pkg:
                        all_packages.append({
                            'id': existing_pkg.id,
                            'name': ref.name,
                            'version': ref.version,
                            'status': 'already_validated',
                            'security_score': existing_pkg.security_score,
                            'validation_errors': [],
                            'type': 'existing'
                        })
            
            result_requests.append({
                'id': req.id,
                'status': req.status,
                'total_packages': req.total_packages,
                'validated_packages': req.validated_packages,
                'created_at': req.created_at.isoformat(),
                'updated_at': req.updated_at.isoformat(),
                'requestor': {
                    'id': req.requestor.id,
                    'username': req.requestor.username,
                    'full_name': req.requestor.full_name
                },
                'application': {
                    'name': req.application.name,
                    'version': req.application.version
                },
                'packages': all_packages
            })
        
        return jsonify({
            'requests': result_requests
        })
        
    except Exception as e:
        logger.error(f"List requests error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/admin/packages/approve/<int:package_id>', methods=['POST'])
@auth_service.require_admin
def approve_package(package_id):
    """Approve a package and automatically publish it"""
    try:
        package = Package.query.get_or_404(package_id)
        
        if package.status != 'validated':
            return jsonify({'error': 'Package must be validated before approval'}), 400
        
        # Approve the package
        package.status = 'approved'
        db.session.commit()
        
        # Automatically publish to secure repository
        success = package_service.publish_to_secure_repo(package)
        
        if success:
            package.status = 'published'
            db.session.commit()
            
            # Log the approval and publishing
            audit_log = AuditLog(
                user_id=request.user.id,
                action='approve_and_publish_package',
                resource_type='package',
                resource_id=package.id,
                details=f'Package {package.name}@{package.version} approved and automatically published'
            )
            db.session.add(audit_log)
            db.session.commit()
            
            return jsonify({'message': 'Package approved and published successfully'})
        else:
            # Revert status if publishing failed
            package.status = 'approved'
            db.session.commit()
            
            return jsonify({'error': 'Package approved but failed to publish'}), 500
        
    except Exception as e:
        logger.error(f"Approve package error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/admin/packages/publish/<int:package_id>', methods=['POST'])
@auth_service.require_admin
def publish_package(package_id):
    """Publish an approved package to the secure repository"""
    try:
        package = Package.query.get_or_404(package_id)
        
        if package.status != 'approved':
            return jsonify({'error': 'Package must be approved before publishing'}), 400
        
        # Publish to secure repository
        success = package_service.publish_to_secure_repo(package)
        
        if success:
            package.status = 'published'
            db.session.commit()
            
            # Log the action
            audit_log = AuditLog(
                user_id=request.user.id,
                action='publish_package',
                resource_type='package',
                resource_id=package.id,
                details=f'Package {package.name}@{package.version} published to secure repo'
            )
            db.session.add(audit_log)
            db.session.commit()
            
            return jsonify({'message': 'Package published successfully'})
        else:
            return jsonify({'error': 'Failed to publish package'}), 500
        
    except Exception as e:
        logger.error(f"Publish package error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/admin/packages/validated', methods=['GET'])
@auth_service.require_admin
def get_validated_packages():
    """Get all validated packages for admin review"""
    try:
        packages = Package.query.filter_by(status='validated').all()
        
        return jsonify({
            'packages': [{
                'id': pkg.id,
                'name': pkg.name,
                'version': pkg.version,
                'security_score': pkg.security_score,
                'validation_errors': pkg.validation_errors or [],
                'request': {
                    'id': pkg.package_request.id,
                    'application': {
                        'name': pkg.package_request.application.name,
                        'version': pkg.package_request.application.version
                    }
                }
            } for pkg in packages]
        })
        
    except Exception as e:
        logger.error(f"Get validated packages error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)
