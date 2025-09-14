import logging
from models import db, SupportedLicense, Package

logger = logging.getLogger(__name__)

class LicenseService:
    """Service for license validation and management"""
    
    def __init__(self):
        self.logger = logger
    
    def validate_package_license(self, package_data):
        """
        Validate a package's license against 4-tier status system
        
        Args:
            package_data (dict): Package data including license information
            
        Returns:
            dict: Validation result with score and errors
        """
        try:
            license_identifier = package_data.get('license')
            package_name = package_data.get('name', 'Unknown')
            
            if not license_identifier:
                return {
                    'score': 0,
                    'errors': ['No license information found'],
                    'warnings': ['Package has no license specified']
                }
            
            # Handle multiple licenses (array format)
            if isinstance(license_identifier, list):
                if len(license_identifier) == 0:
                    return {
                        'score': 0,
                        'errors': ['No license information found'],
                        'warnings': ['Package has no license specified']
                    }
                # Use the first license for validation
                license_identifier = license_identifier[0]
            
            # Handle license objects (e.g., {"type": "MIT", "url": "..."})
            if isinstance(license_identifier, dict):
                license_identifier = license_identifier.get('type', '')
            
            # Clean up license identifier
            license_identifier = str(license_identifier).strip()
            
            if not license_identifier:
                return {
                    'score': 0,
                    'errors': ['Invalid license format'],
                    'warnings': ['License information is empty']
                }
            
            # Find the license in the database
            license = SupportedLicense.query.filter_by(
                identifier=license_identifier
            ).first()
            
            if not license:
                # Check for common variations
                license = self._find_license_variation(license_identifier)
            
            if not license:
                return {
                    'score': 0,
                    'errors': [f'License "{license_identifier}" is not recognized'],
                    'warnings': [f'License "{license_identifier}" is not in the license database']
                }
            
            # Handle different statuses
            if license.status == 'blocked':
                return {
                    'score': 0,
                    'errors': [f'License "{license_identifier}" is blocked by policy'],
                    'warnings': [f'License "{license_identifier}" is explicitly prohibited']
                }
            
            elif license.status == 'avoid':
                return {
                    'score': 30,
                    'errors': [],
                    'warnings': [f'License "{license_identifier}" is discouraged and may have restrictions']
                }
            
            elif license.status == 'allowed':
                score = self._calculate_license_score(license)
                result = {
                    'score': score,
                    'errors': [],
                    'warnings': []
                }
                
                self.logger.info(f"License validation for {package_name}: {license_identifier} - Score: {score} (Allowed)")
                return result
            
            elif license.status == 'always_allowed':
                score = self._calculate_license_score(license)
                result = {
                    'score': score,
                    'errors': [],
                    'warnings': []
                }
                
                self.logger.info(f"License validation for {package_name}: {license_identifier} - Score: {score} (Always Allowed)")
                return result
            
            else:
                return {
                    'score': 0,
                    'errors': [f'License "{license_identifier}" has unknown status'],
                    'warnings': []
                }
            
        except Exception as e:
            self.logger.error(f"License validation error for {package_data.get('name', 'Unknown')}: {str(e)}")
            return {
                'score': 0,
                'errors': [f'License validation failed: {str(e)}'],
                'warnings': []
            }
    
    def _find_license_variation(self, license_identifier):
        """Find license by common variations"""
        variations = [
            license_identifier.lower(),
            license_identifier.upper(),
            license_identifier.replace('-', ' '),
            license_identifier.replace(' ', '-'),
            license_identifier.replace('_', '-'),
            license_identifier.replace('_', ' ')
        ]
        
        for variation in variations:
            license = SupportedLicense.query.filter_by(
                identifier=variation
            ).first()
            if license:
                return license
        
        # Try partial matches
        licenses = SupportedLicense.query.filter(
            SupportedLicense.identifier.ilike(f'%{license_identifier}%')
        ).all()
        
        if licenses:
            return licenses[0]  # Return first match
        
        return None
    
    def _calculate_license_score(self, supported_license):
        """Calculate license compliance score based on status"""
        if supported_license.status == 'always_allowed':
            return 100
        elif supported_license.status == 'allowed':
            return 80
        elif supported_license.status == 'avoid':
            return 30
        elif supported_license.status == 'blocked':
            return 0
        else:
            return 0
    
    def get_supported_licenses(self, status=None):
        """Get all supported licenses, optionally filtered by status"""
        try:
            query = SupportedLicense.query
            if status:
                query = query.filter_by(status=status)
            return query.all()
        except Exception as e:
            self.logger.error(f"Error getting supported licenses: {str(e)}")
            return []
    
    def is_license_allowed(self, license_identifier):
        """Check if a license is allowed (not blocked)"""
        try:
            license = SupportedLicense.query.filter_by(
                identifier=license_identifier
            ).first()
            
            if not license:
                return False
            
            return license.status in ['always_allowed', 'allowed', 'avoid']
        except Exception as e:
            self.logger.error(f"Error checking license support: {str(e)}")
            return False
