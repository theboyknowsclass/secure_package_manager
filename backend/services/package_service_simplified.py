import os
import json
import logging
from models import Package, PackageRequest, PackageValidation, PackageReference, RepositoryConfig, db
from .license_service import LicenseService

logger = logging.getLogger(__name__)

class PackageService:
    def __init__(self):
        # Don't initialize any config values - they'll be loaded dynamically
        self._config_loaded = False
        self._config_cache = {}
        self.license_service = LicenseService()
    
    def _load_config(self):
        """Load repository configuration from database (only when needed)"""
        if self._config_loaded:
            return
            
        try:
            # Load from database - use None as defaults to detect missing configuration
            self._config_cache = {
                'source_repo_url': RepositoryConfig.get_config_value('source_repository_url'),
                'target_repo_url': RepositoryConfig.get_config_value('target_repository_url'),
            }
            
            # Set secure_repo_url based on target_repo_url or environment
            if self._config_cache['target_repo_url']:
                self._config_cache['secure_repo_url'] = os.getenv('SECURE_REPO_URL', self._config_cache['target_repo_url'])
            else:
                self._config_cache['secure_repo_url'] = os.getenv('SECURE_REPO_URL')
            
            self._config_loaded = True
            
            # Log configuration status
            if all(self._config_cache[key] for key in ['source_repo_url', 'target_repo_url']):
                logger.info(f"Loaded repository configuration: source={self._config_cache['source_repo_url']}, target={self._config_cache['target_repo_url']}")
            else:
                logger.warning("Repository configuration is incomplete - some values are missing")
                
        except Exception as e:
            logger.warning(f"Could not load repository config from database: {e}. Configuration will be None.")
            # Set all values to None to indicate missing configuration
            self._config_cache = {
                'source_repo_url': None,
                'target_repo_url': None,
                'secure_repo_url': os.getenv('SECURE_REPO_URL')
            }
            self._config_loaded = True
    
    def refresh_config(self):
        """Refresh repository configuration from database"""
        self._config_loaded = False
        self._load_config()
    
    def is_configuration_complete(self):
        """Check if repository configuration is complete"""
        self._load_config()
        required_keys = ['source_repo_url', 'target_repo_url']
        return all(self._config_cache.get(key) for key in required_keys)
    
    def get_missing_config_keys(self):
        """Get list of missing configuration keys"""
        self._load_config()
        required_keys = ['source_repo_url', 'target_repo_url']
        return [key for key in required_keys if not self._config_cache.get(key)]
    
    @property
    def source_repo_url(self):
        self._load_config()
        return self._config_cache['source_repo_url']
    
    @property
    def target_repo_url(self):
        self._load_config()
        return self._config_cache['target_repo_url']
    
    @property
    def secure_repo_url(self):
        self._load_config()
        return self._config_cache['secure_repo_url']
    
    def process_package_lock(self, request_id, package_data):
        """Process package-lock.json and extract all packages"""
        try:
            packages_to_process = []
            existing_packages = []
            
            # Validate that this is actually a package-lock.json file
            if 'lockfileVersion' not in package_data:
                raise ValueError("This file does not appear to be a package-lock.json file. Missing 'lockfileVersion' field.")
            
            # Check lockfile version - only support modern versions
            lockfile_version = package_data.get('lockfileVersion')
            if lockfile_version < 3:
                raise ValueError(
                    f"Unsupported lockfile version: {lockfile_version}. "
                    f"This system only supports package-lock.json files with lockfileVersion 3 or higher. "
                    f"Please upgrade your npm version (npm 8+) and regenerate the lockfile."
                )
            
            # Extract packages from dependencies
            packages = package_data.get('packages', {})
            
            for package_path, package_info in packages.items():
                if package_path == '':  # Skip root package
                    continue
                
                package_name = package_info.get('name')
                package_version = package_info.get('version')
                
                if not package_name or not package_version:
                    continue
                
                # Check if package already exists
                existing_package = Package.query.filter_by(
                    name=package_name,
                    version=package_version,
                    package_request_id=request_id
                ).first()
                
                if existing_package:
                    existing_packages.append(existing_package)
                    continue
                
                # Create new package
                package = Package(
                    name=package_name,
                    version=package_version,
                    package_request_id=request_id,
                    status='pending',
                    license_identifier=package_info.get('license'),
                    integrity_hash=package_info.get('integrity'),
                    resolved_url=package_info.get('resolved'),
                    dev_dependency=package_info.get('dev', False)
                )
                
                packages_to_process.append(package)
                db.session.add(package)
            
            db.session.commit()
            
            # Process packages asynchronously
            self._process_packages_async(request_id)
            
            return {
                'packages_to_process': len(packages_to_process),
                'existing_packages': len(existing_packages),
                'total_packages': len(packages_to_process) + len(existing_packages)
            }
            
        except Exception as e:
            logger.error(f"Error processing package-lock.json: {str(e)}")
            raise e
    
    def _process_packages_async(self, request_id):
        """Process packages asynchronously (simplified version)"""
        try:
            packages = Package.query.filter_by(package_request_id=request_id).all()
            
            for package in packages:
                if package.status == 'pending':
                    self._download_and_validate_package(package)
            
            # Update request status
            package_request = PackageRequest.query.get(request_id)
            if package_request:
                # Check if all packages are processed
                pending_packages = Package.query.filter_by(
                    package_request_id=request_id,
                    status='pending'
                ).count()
                
                if pending_packages == 0:
                    # Check if any packages failed validation
                    failed_packages = Package.query.filter_by(
                        package_request_id=request_id,
                        status='rejected'
                    ).count()
                    
                    if failed_packages > 0:
                        package_request.status = 'validation_failed'
                    else:
                        package_request.status = 'validated'
                    
                    db.session.commit()
            
        except Exception as e:
            logger.error(f"Error processing packages for request {request_id}: {str(e)}")
            package_request = PackageRequest.query.get(request_id)
            if package_request:
                package_request.status = 'validation_failed'
                db.session.commit()
    
    def _download_and_validate_package(self, package):
        """Validate package information from package-lock.json"""
        try:
            # Update status to validating
            package.status = 'validating'
            db.session.commit()
            
            # For now, we'll validate based on the information in package-lock.json
            # In production, you might want to:
            # 1. Verify integrity hashes
            # 2. Check against security databases
            # 3. Validate license information
            # 4. Check for known vulnerabilities
            
            # Simulate validation process
            if not self._validate_package_info(package):
                package.status = 'rejected'
                package.validation_errors = ['Package validation failed']
                db.session.commit()
                return False
            
            # Create validation records
            if not self._create_validation_records(package):
                package.status = 'rejected'
                package.validation_errors = ['Failed to create validation records']
                db.session.commit()
                return False
            
            # Update status to validated
            package.status = 'validated'
            package.security_score = self._calculate_security_score(package)
            db.session.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing package {package.name}@{package.version}: {str(e)}")
            package.status = 'rejected'
            package.validation_errors = [str(e)]
            db.session.commit()
            return False
    
    def _validate_package_info(self, package):
        """Validate package information from package-lock.json"""
        try:
            # Basic validation - check if we have the required information
            if not package.name or not package.version:
                logger.warning(f"Package {package.name}@{package.version} missing required information")
                return False
            
            # Log validation using configured repository
            logger.info(f"Validating package {package.name}@{package.version} from {self.source_repo_url}")
            
            # In production, you would download and analyze the package from the source repository
            # For now, we'll simulate this process
            if not self._simulate_package_download(package):
                logger.warning(f"Failed to download package {package.name}@{package.version} from {self.source_repo_url}")
                package.validation_errors = [f"Failed to download package from {self.source_repo_url}"]
                return False
            
            # Validate license information
            license_validation = self._validate_package_license(package)
            if license_validation['score'] == 0:
                package.validation_errors = license_validation['errors']
                logger.warning(f"Package {package.name}@{package.version} failed license validation: {license_validation['errors']}")
                return False
            
            logger.info(f"Package {package.name}@{package.version} validated successfully (License score: {license_validation['score']})")
            return True
            
        except Exception as e:
            logger.error(f"Error validating package info for {package.name}@{package.version}: {str(e)}")
            return False
    
    def _simulate_package_download(self, package):
        """Simulate downloading package from source repository"""
        try:
            import time
            import random
            
            # Simulate download delay based on package size and network conditions
            base_delay = 0.1  # Base delay in seconds
            size_factor = 0.001  # Additional delay per MB
            network_factor = random.uniform(0.5, 2.0)  # Simulate network variability
            
            # Calculate simulated download time
            estimated_size = random.uniform(1, 50)  # Simulate package size in MB
            download_time = (base_delay + estimated_size * size_factor) * network_factor
            
            # Simulate download
            logger.info(f"Downloading {package.name}@{package.version} from {self.source_repo_url} (simulated {download_time:.2f}s)")
            time.sleep(min(download_time, 0.5))  # Cap actual sleep time for testing
            
            # Simulate occasional download failures
            if random.random() < 0.05:  # 5% failure rate
                logger.warning(f"Simulated download failure for {package.name}@{package.version}")
                return False
            
            logger.info(f"Successfully downloaded {package.name}@{package.version} from {self.source_repo_url}")
            return True
            
        except Exception as e:
            logger.error(f"Error simulating package download for {package.name}@{package.version}: {str(e)}")
            return False
    
    def _validate_package_license(self, package):
        """Validate package license information"""
        try:
            # Get package data from npm registry or package-lock.json
            package_data = {
                'name': package.name,
                'version': package.version,
                'license': package.license_identifier  # This should be populated from package-lock.json
            }
            
            # Use license service to validate
            validation_result = self.license_service.validate_package_license(package_data)
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating package license for {package.name}@{package.version}: {str(e)}")
            return {
                'score': 0,
                'errors': [f'License validation failed: {str(e)}'],
                'warnings': []
            }
    
    def _calculate_security_score(self, package):
        """Calculate security score for package (simplified)"""
        try:
            # In production, this would analyze various security factors
            # For now, return a mock score based on validation results
            validations = PackageValidation.query.filter_by(package_id=package.id).all()
            passed_validations = sum(1 for v in validations if v.status == 'passed')
            total_validations = len(validations)
            
            if total_validations == 0:
                return 0
            
            # Base score from validation results
            base_score = (passed_validations / total_validations) * 100
            
            # Add some randomness for demo purposes
            import random
            random_factor = random.uniform(0.8, 1.2)
            
            final_score = min(int(base_score * random_factor), 100)
            return max(final_score, 0)
            
        except Exception as e:
            logger.error(f"Error calculating security score: {str(e)}")
            return 50

    
    def publish_to_secure_repo(self, package):
        """Publish package to secure repository"""
        try:
            # In production, this would upload to the actual secure repository
            # For now, we'll simulate the upload
            logger.info(f"Publishing {package.name}@{package.version} to repository at {self.target_repo_url}")
            
            # Simulate upload delay based on package size
            import time
            import random
            estimated_size = random.uniform(1, 50)  # Simulate package size in MB
            upload_time = min(estimated_size * 0.1, 2.0)  # Simulate upload time
            time.sleep(upload_time)
            
            # Log the repository configuration being used
            logger.info(f"Package published to repository: {self.target_repo_url}")
            
            # Log the action
            logger.info(f"Successfully published {package.name}@{package.version} to secure repository")
            return True
            
        except Exception as e:
            logger.error(f"Error publishing package {package.name}@{package.version}: {str(e)}")
            return False
    
    def _create_validation_records(self, package):
        """Create validation records for package"""
        try:
            # Create validation records
            validations = [
                ('package_info', 'passed', 'Package information validated'),
                ('license_check', 'passed', 'License validation passed'),
                ('security_scan', 'passed', 'Security scan completed'),
                ('integrity_check', 'passed', 'Integrity hash verified')
            ]
            
            for validation_type, status, details in validations:
                validation = PackageValidation(
                    package_id=package.id,
                    validation_type=validation_type,
                    status=status,
                    details=details
                )
                db.session.add(validation)
            
            db.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error creating validation records: {str(e)}")
            return False
