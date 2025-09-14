from flask import Blueprint, request, jsonify
from services.auth_service import AuthService
from services.package_service import PackageService
from models import db, Package, SupportedLicense, AuditLog, RepositoryConfig
import logging

logger = logging.getLogger(__name__)

# Create blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

# Initialize services
auth_service = AuthService()
package_service = PackageService()

# Package Management Routes
@admin_bp.route('/packages/approve/<int:package_id>', methods=['POST'])
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

@admin_bp.route('/packages/publish/<int:package_id>', methods=['POST'])
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

@admin_bp.route('/packages/validated', methods=['GET'])
@auth_service.require_admin
def get_validated_packages():
    """Get all validated packages for admin review"""
    try:
        packages = Package.query.filter_by(status='validated').all()
        
        # Handle case when no packages exist
        if not packages:
            return jsonify({'packages': []})
        
        # Build response with proper error handling for relationships
        package_list = []
        for pkg in packages:
            try:
                # Safely access the relationship
                request_data = None
                if pkg.package_request:
                    application_data = None
                    if pkg.package_request.application:
                        application_data = {
                            'name': pkg.package_request.application.name,
                            'version': pkg.package_request.application.version
                        }
                    
                    request_data = {
                        'id': pkg.package_request.id,
                        'application': application_data or {'name': 'Unknown', 'version': 'Unknown'}
                    }
                else:
                    request_data = {
                        'id': 0,
                        'application': {'name': 'Unknown', 'version': 'Unknown'}
                    }
                
                package_list.append({
                    'id': pkg.id,
                    'name': pkg.name,
                    'version': pkg.version,
                    'security_score': pkg.security_score or 0,
                    'license_score': pkg.license_score or 0,
                    'license_identifier': pkg.license_identifier or 'Unknown',
                    'validation_errors': pkg.validation_errors or [],
                    'request': request_data
                })
            except Exception as pkg_error:
                logger.warning(f"Error processing package {pkg.id}: {str(pkg_error)}")
                # Skip this package but continue with others
                continue
        
        return jsonify({'packages': package_list})
        
    except Exception as e:
        logger.error(f"Get validated packages error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# License Management Routes
@admin_bp.route('/licenses', methods=['GET'])
@auth_service.require_auth
def get_supported_licenses():
    """Get all supported licenses"""
    try:
        status = request.args.get('status')  # 'always_allowed', 'allowed', 'avoid', 'blocked'
        query = SupportedLicense.query
        
        if status:
            query = query.filter_by(status=status)
            
        licenses = query.all()
        return jsonify({
            'licenses': [license.to_dict() for license in licenses]
        })
    except Exception as e:
        logger.error(f"Get supported licenses error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@admin_bp.route('/licenses', methods=['POST'])
@auth_service.require_auth
def create_supported_license():
    """Create a new supported license"""
    try:
        if not request.user.is_admin():
            return jsonify({'error': 'Admin access required'}), 403
            
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name') or not data.get('identifier'):
            return jsonify({'error': 'Name and identifier are required'}), 400
            
        # Check if identifier already exists
        existing = SupportedLicense.query.filter_by(identifier=data['identifier']).first()
        if existing:
            return jsonify({'error': 'License identifier already exists'}), 400
            
        # Create new license
        license = SupportedLicense(
            name=data['name'],
            identifier=data['identifier'],
            status=data.get('status', 'allowed'),
            created_by=request.user.id
        )
        
        db.session.add(license)
        db.session.commit()
        
        # Log the action
        audit_log = AuditLog(
            user_id=request.user.id,
            action='create_license',
            resource_type='license',
            resource_id=license.id,
            details=f'Created license: {license.name} ({license.identifier})'
        )
        db.session.add(audit_log)
        db.session.commit()
        
        return jsonify({
            'message': 'License created successfully',
            'license': license.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Create license error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@admin_bp.route('/licenses/<int:license_id>', methods=['PUT'])
@auth_service.require_auth
def update_supported_license(license_id):
    """Update a supported license"""
    try:
        if not request.user.is_admin():
            return jsonify({'error': 'Admin access required'}), 403
            
        license = SupportedLicense.query.get_or_404(license_id)
        data = request.get_json()
        
        # Update fields
        if 'name' in data:
            license.name = data['name']
        if 'status' in data:
            license.status = data['status']
            
        db.session.commit()
        
        # Log the action
        audit_log = AuditLog(
            user_id=request.user.id,
            action='update_license',
            resource_type='license',
            resource_id=license.id,
            details=f'Updated license: {license.name} ({license.identifier})'
        )
        db.session.add(audit_log)
        db.session.commit()
        
        return jsonify({
            'message': 'License updated successfully',
            'license': license.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Update license error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@admin_bp.route('/licenses/<int:license_id>', methods=['DELETE'])
@auth_service.require_auth
def delete_supported_license(license_id):
    """Delete a supported license"""
    try:
        if not request.user.is_admin():
            return jsonify({'error': 'Admin access required'}), 403
            
        license = SupportedLicense.query.get_or_404(license_id)
        
        # Check if license is being used by any packages
        package_count = Package.query.filter_by(license_identifier=license.identifier).count()
        if package_count > 0:
            return jsonify({
                'error': f'Cannot delete license. It is used by {package_count} package(s). Disable it instead.'
            }), 400
        
        db.session.delete(license)
        db.session.commit()
        
        # Log the action
        audit_log = AuditLog(
            user_id=request.user.id,
            action='delete_license',
            resource_type='license',
            resource_id=license_id,
            details=f'Deleted license: {license.name} ({license.identifier})'
        )
        db.session.add(audit_log)
        db.session.commit()
        
        return jsonify({'message': 'License deleted successfully'})
        
    except Exception as e:
        logger.error(f"Delete license error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

# Repository Configuration Routes
@admin_bp.route('/repository-config', methods=['GET'])
@auth_service.require_admin
def get_repository_config():
    """Get all repository configuration settings"""
    try:
        configs = RepositoryConfig.query.all()
        return jsonify({
            'configs': [config.to_dict() for config in configs]
        })
    except Exception as e:
        logger.error(f"Get repository config error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@admin_bp.route('/repository-config', methods=['PUT'])
@auth_service.require_admin
def update_repository_config():
    """Update repository configuration settings"""
    try:
        data = request.get_json()
        
        if not data or 'configs' not in data:
            return jsonify({'error': 'Configuration data is required'}), 400
        
        updated_configs = []
        
        for config_data in data['configs']:
            if 'config_key' not in config_data or 'config_value' not in config_data:
                continue
                
            config = RepositoryConfig.set_config_value(
                key=config_data['config_key'],
                value=config_data['config_value'],
                description=config_data.get('description')
            )
            updated_configs.append(config.to_dict())
        
        # Log the action
        audit_log = AuditLog(
            user_id=request.user.id,
            action='update_repository_config',
            resource_type='config',
            resource_id=None,
            details=f'Updated repository configuration: {len(updated_configs)} settings'
        )
        db.session.add(audit_log)
        db.session.commit()
        
        return jsonify({
            'message': 'Repository configuration updated successfully',
            'configs': updated_configs
        })
        
    except Exception as e:
        logger.error(f"Update repository config error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@admin_bp.route('/repository-config/<config_key>', methods=['GET'])
@auth_service.require_auth
def get_repository_config_value(config_key):
    """Get a specific repository configuration value"""
    try:
        value = RepositoryConfig.get_config_value(config_key)
        if value is None:
            return jsonify({'error': 'Configuration key not found'}), 404
        
        return jsonify({
            'config_key': config_key,
            'config_value': value
        })
        
    except Exception as e:
        logger.error(f"Get repository config value error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@admin_bp.route('/repository-config/status', methods=['GET'])
@auth_service.require_auth
def get_repository_config_status():
    """Get repository configuration status"""
    try:
        from services.package_service import PackageService
        package_service = PackageService()
        
        is_complete = package_service.is_configuration_complete()
        missing_keys = package_service.get_missing_config_keys()
        
        return jsonify({
            'is_complete': is_complete,
            'missing_keys': missing_keys,
            'requires_admin_setup': not is_complete
        })
        
    except Exception as e:
        logger.error(f"Get repository config status error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
