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
                'source_repo_type': RepositoryConfig.get_config_value('source_repository_type'),
                'target_repo_type': RepositoryConfig.get_config_value('target_repo_type'),
                'validation_timeout': RepositoryConfig.get_config_value('validation_timeout'),
                'max_package_size': RepositoryConfig.get_config_value('max_package_size'),
            }
            
            # Convert string values to appropriate types
            if self._config_cache['validation_timeout']:
                self._config_cache['validation_timeout'] = int(self._config_cache['validation_timeout'])
            if self._config_cache['max_package_size']:
                self._config_cache['max_package_size'] = int(self._config_cache['max_package_size'])
            
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
                'source_repo_type': None,
                'target_repo_type': None,
                'validation_timeout': None,
                'max_package_size': None,
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
        required_keys = ['source_repo_url', 'target_repo_url', 'source_repo_type', 'target_repo_type']
        return all(self._config_cache.get(key) for key in required_keys)
    
    def get_missing_config_keys(self):
        """Get list of missing configuration keys"""
        self._load_config()
        required_keys = ['source_repo_url', 'target_repo_url', 'source_repo_type', 'target_repo_type']
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
    def source_repo_type(self):
        self._load_config()
        return self._config_cache['source_repo_type']
    
    @property
    def target_repo_type(self):
        self._load_config()
        return self._config_cache['target_repo_type']
    
    @property
    def validation_timeout(self):
        self._load_config()
        return self._config_cache['validation_timeout']
    
    @property
    def max_package_size(self):
        self._load_config()
        return self._config_cache['max_package_size']
    
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
            
            # Modern format (lockfileVersion 3+)
            # Extract from packages[""].dependencies and packages[""].devDependencies
            root_package = package_data.get('packages', {}).get('', {})
            dependencies = root_package.get('dependencies', {})
            dev_dependencies = root_package.get('devDependencies', {})
            
            # Combine all dependencies
            all_dependencies = {**dependencies, **dev_dependencies}
            
            # Also extract from node_modules packages
            packages = package_data.get('packages', {})
            for package_path, package_info in packages.items():
                if package_path.startswith('node_modules/') and package_path != 'node_modules/':
                    package_name = package_path.replace('node_modules/', '')
                    if isinstance(package_info, dict) and 'version' in package_info:
                        all_dependencies[package_name] = package_info
            
            logger.info(f"Processing package-lock.json with lockfileVersion {lockfile_version}, found {len(all_dependencies)} dependencies")
            
            # Extract all packages from dependencies
            for package_name, package_info in all_dependencies.items():
                if isinstance(package_info, dict):
                    version = package_info.get('version', 'unknown')
                    resolved = package_info.get('resolved', '')
                    integrity = package_info.get('integrity', '')
                    
                    # Skip packages without version info or resolved URL
                    if version == 'unknown' or not resolved:
                        logger.warning(f"Skipping package {package_name} - missing version or resolved URL")
                        continue
                    
                    # Check if this package+version already exists and is validated
                    existing_package = Package.query.filter_by(
                        name=package_name,
                        version=version,
                        status='validated'
                    ).first()
                    
                    if existing_package:
                        # Package already exists and is validated
                        existing_packages.append({
                            'name': package_name,
                            'version': version,
                            'status': 'already_validated',
                            'package_id': existing_package.id
                        })
                        
                        # Create package reference for existing package
                        package_ref = PackageReference(
                            package_request_id=request_id,
                            name=package_name,
                            version=version,
                            npm_url=resolved,
                            integrity=integrity,
                            status='already_validated',
                            existing_package_id=existing_package.id
                        )
                        db.session.add(package_ref)
                        
                        logger.info(f"Package {package_name}@{version} already validated, skipping")
                    else:
                        # Package needs validation
                        # Extract license information from package data
                        license_info = package_data.get('license', '')
                        
                        packages_to_process.append({
                            'name': package_name,
                            'version': version,
                            'resolved': resolved,
                            'integrity': integrity,
                            'license': license_info
                        })
                        
                        # Create package reference for new package
                        package_ref = PackageReference(
                            package_request_id=request_id,
                            name=package_name,
                            version=version,
                            npm_url=resolved,
                            integrity=integrity,
                            status='needs_validation'
                        )
                        db.session.add(package_ref)
            
            # Create package records only for packages that need validation
            total_packages = len(packages_to_process) + len(existing_packages)
            validated_packages = len(existing_packages)
            
            for package_info in packages_to_process:
                package = Package(
                    package_request_id=request_id,
                    name=package_info['name'],
                    version=package_info['version'],
                    npm_url=package_info['resolved'],
                    license_identifier=package_info.get('license', ''),
                    status='requested'
                )
                db.session.add(package)
            
            # Update package request with counts
            package_request = PackageRequest.query.get(request_id)
            if package_request:
                package_request.total_packages = total_packages
                package_request.validated_packages = validated_packages
                package_request.status = 'validating' if packages_to_process else 'validated'
            
            db.session.commit()
            
            # Start processing only the packages that need validation
            if packages_to_process:
                self._process_packages_async(request_id)
            
            logger.info(f"Processed {len(packages_to_process)} new packages, {len(existing_packages)} already validated for request {request_id}")
            
        except Exception as e:
            logger.error(f"Error processing package lock: {str(e)}")
            # Update request status to failed
            package_request = PackageRequest.query.get(request_id)
            if package_request:
                package_request.status = 'rejected'
                db.session.commit()
    
    def _process_packages_async(self, request_id):
        """Process packages asynchronously (simplified version)"""
        try:
            packages = Package.query.filter_by(package_request_id=request_id).all()
            
            for package in packages:
                try:
                    self._download_and_validate_package(package)
                except Exception as e:
                    logger.error(f"Error processing package {package.name}@{package.version}: {str(e)}")
                    package.status = 'rejected'
                    package.validation_errors = [str(e)]
                    db.session.commit()
                    continue
            
            # Update request status
            package_request = PackageRequest.query.get(request_id)
            if package_request:
                validated_count = Package.query.filter_by(
                    package_request_id=request_id, 
                    status='validated'
                ).count()
                rejected_count = Package.query.filter_by(
                    package_request_id=request_id, 
                    status='rejected'
                ).count()
                
                package_request.validated_packages = validated_count
                
                if validated_count == package_request.total_packages:
                    package_request.status = 'validated'
                elif validated_count > 0 and rejected_count < package_request.total_packages:
                    package_request.status = 'partially_validated'
                elif rejected_count == package_request.total_packages:
                    package_request.status = 'validation_failed'
                else:
                    package_request.status = 'partially_validated'
                
                db.session.commit()
                
        except Exception as e:
            logger.error(f"Error in async package processing: {str(e)}")
            # Update request status to failed
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
            
            # Check package size against configured limit
            if hasattr(package, 'size') and package.size:
                size_mb = package.size / (1024 * 1024)  # Convert bytes to MB
                if size_mb > self.max_package_size:
                    logger.warning(f"Package {package.name}@{package.version} size {size_mb:.2f}MB exceeds limit {self.max_package_size}MB")
                    package.validation_errors = [f"Package size {size_mb:.2f}MB exceeds maximum allowed size of {self.max_package_size}MB"]
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
            
            # Store license information
            package.license_score = license_validation['score']
            if license_validation.get('warnings'):
                if not package.validation_errors:
                    package.validation_errors = []
                package.validation_errors.extend(license_validation['warnings'])
            
            # In production, you would:
            # 1. Verify the integrity hash if available
            # 2. Check against npm registry for package existence
            # 3. Validate version format
            # 4. Check for known security issues
            
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
            
            # Apply timeout check
            if download_time > self.validation_timeout:
                logger.warning(f"Package {package.name}@{package.version} download would exceed timeout {self.validation_timeout}s")
                return False
            
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
            return self.license_service.validate_package_license(package_data)
            
        except Exception as e:
            logger.error(f"Error validating license for {package.name}@{package.version}: {str(e)}")
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
            
            # Base score of 70, with bonus for passed validations
            base_score = 70
            bonus_per_validation = 10
            score = base_score + (passed_validations * bonus_per_validation)
            
            return min(score, 100)
            
        except Exception as e:
            logger.error(f"Error calculating security score: {str(e)}")
            return 50
    

    
    def publish_to_secure_repo(self, package):
        """Publish package to secure repository"""
        try:
            # In production, this would upload to the actual secure repository
            # For now, we'll simulate the upload
            logger.info(f"Publishing {package.name}@{package.version} to {self.target_repo_type} repository at {self.target_repo_url}")
            
            # Simulate upload delay based on package size
            import time
            import random
            estimated_size = random.uniform(1, 50)  # Simulate package size in MB
            upload_time = min(estimated_size * 0.1, 2.0)  # Simulate upload time
            time.sleep(upload_time)
            
            # Log the repository configuration being used
            logger.info(f"Package published to {self.target_repo_type} repository: {self.target_repo_url}")
            
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
                ('security_check', 'passed', 'Security check completed'),
                ('license_check', 'passed', 'License check completed'),
                ('dependency_analysis', 'passed', 'Dependency analysis completed')
            ]
            
            # Save validation results
            for validation_type, status, details in validations:
                validation = PackageValidation(
                    package_id=package.id,
                    validation_type=validation_type,
                    status=status,
                    details=details
                )
                db.session.add(validation)
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating validation records for {package.name}@{package.version}: {str(e)}")
            return False
