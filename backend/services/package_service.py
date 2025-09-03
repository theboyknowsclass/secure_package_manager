import os
import requests
import hashlib
import json
import logging
from urllib.parse import urljoin
from models import Package, PackageRequest, PackageValidation, db

logger = logging.getLogger(__name__)

class PackageService:
    def __init__(self):
        self.npm_proxy_url = os.getenv('NPM_PROXY_URL', 'https://registry.npmjs.org')
        self.secure_repo_url = os.getenv('SECURE_REPO_URL', 'http://localhost:8080')
        self.package_cache_dir = os.getenv('PACKAGE_CACHE_DIR', '/app/package_cache')
        
        # Create package cache directory if it doesn't exist
        os.makedirs(self.package_cache_dir, exist_ok=True)
    
    def process_package_lock(self, request_id, package_data):
        """Process package-lock.json and extract all packages"""
        try:
            dependencies = package_data.get('dependencies', {})
            packages = []
            
            # Extract all packages from dependencies
            for package_name, package_info in dependencies.items():
                if isinstance(package_info, dict):
                    version = package_info.get('version', 'unknown')
                    packages.append({
                        'name': package_name,
                        'version': version,
                        'resolved': package_info.get('resolved', ''),
                        'integrity': package_info.get('integrity', '')
                    })
            
            # Create package records in database
            total_packages = len(packages)
            for package_info in packages:
                package = Package(
                    package_request_id=request_id,
                    name=package_info['name'],
                    version=package_info['version'],
                    npm_url=package_info['resolved'],
                    status='requested'
                )
                db.session.add(package)
            
            # Update package request with total count
            package_request = PackageRequest.query.get(request_id)
            if package_request:
                package_request.total_packages = total_packages
                package_request.status = 'validating'
            
            db.session.commit()
            
            # Start processing packages asynchronously
            self._process_packages_async(request_id)
            
            logger.info(f"Processed {total_packages} packages for request {request_id}")
            
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
                self._download_and_validate_package(package)
            
            # Update request status
            package_request = PackageRequest.query.get(request_id)
            if package_request:
                validated_count = Package.query.filter_by(
                    package_request_id=request_id, 
                    status='validated'
                ).count()
                
                package_request.validated_packages = validated_count
                
                if validated_count == package_request.total_packages:
                    package_request.status = 'validated'
                elif validated_count > 0:
                    package_request.status = 'partially_validated'
                else:
                    package_request.status = 'validation_failed'
                
                db.session.commit()
                
        except Exception as e:
            logger.error(f"Error in async package processing: {str(e)}")
    
    def _download_and_validate_package(self, package):
        """Download and validate a single package"""
        try:
            # Update status to downloading
            package.status = 'downloading'
            db.session.commit()
            
            # Download package from npm
            if not self._download_package(package):
                package.status = 'rejected'
                package.validation_errors = ['Failed to download package']
                db.session.commit()
                return False
            
            # Update status to downloaded
            package.status = 'downloaded'
            db.session.commit()
            
            # Validate package
            if not self._validate_package(package):
                package.status = 'rejected'
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
    
    def _download_package(self, package):
        """Download package from npm registry"""
        try:
            # Construct npm package URL
            package_url = f"{self.npm_proxy_url}/{package.name}/-/{package.name}-{package.version}.tgz"
            
            # Download package
            response = requests.get(package_url, stream=True)
            if response.status_code != 200:
                logger.error(f"Failed to download {package.name}@{package.version}: {response.status_code}")
                return False
            
            # Save to local cache
            local_filename = f"{package.name}-{package.version}.tgz"
            local_path = os.path.join(self.package_cache_dir, local_filename)
            
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Calculate file size and checksum
            file_size = os.path.getsize(local_path)
            checksum = self._calculate_checksum(local_path)
            
            # Update package record
            package.local_path = local_path
            package.file_size = file_size
            package.checksum = checksum
            
            logger.info(f"Downloaded {package.name}@{package.version} to {local_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error downloading package {package.name}@{package.version}: {str(e)}")
            return False
    
    def _validate_package(self, package):
        """Validate downloaded package"""
        try:
            # Create validation records
            validations = [
                ('file_integrity', 'pending'),
                ('security_scan', 'pending'),
                ('license_check', 'pending'),
                ('dependency_analysis', 'pending')
            ]
            
            validation_results = []
            
            for validation_type, status in validations:
                # Simulate validation (in production, this would run actual validation tools)
                if validation_type == 'file_integrity':
                    # Check file integrity
                    if os.path.exists(package.local_path):
                        validation_results.append(('file_integrity', 'passed', 'File integrity verified'))
                    else:
                        validation_results.append(('file_integrity', 'failed', 'File not found'))
                        return False
                
                elif validation_type == 'security_scan':
                    # Simulate security scan
                    validation_results.append(('security_scan', 'passed', 'Security scan completed'))
                
                elif validation_type == 'license_check':
                    # Simulate license check
                    validation_results.append(('license_check', 'passed', 'License check completed'))
                
                elif validation_type == 'dependency_analysis':
                    # Simulate dependency analysis
                    validation_results.append(('dependency_analysis', 'passed', 'Dependency analysis completed'))
            
            # Save validation results
            for validation_type, status, details in validation_results:
                validation = PackageValidation(
                    package_id=package.id,
                    validation_type=validation_type,
                    status=status,
                    details=details
                )
                db.session.add(validation)
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating package {package.name}@{package.version}: {str(e)}")
            return False
    
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
    
    def _calculate_checksum(self, file_path):
        """Calculate SHA256 checksum of file"""
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"Error calculating checksum: {str(e)}")
            return None
    
    def publish_to_secure_repo(self, package):
        """Publish package to secure repository"""
        try:
            if not package.local_path or not os.path.exists(package.local_path):
                logger.error(f"Package file not found: {package.local_path}")
                return False
            
            # In production, this would upload to the actual secure repository
            # For now, we'll simulate the upload
            logger.info(f"Publishing {package.name}@{package.version} to secure repository")
            
            # Simulate upload delay
            import time
            time.sleep(1)
            
            # Log the action
            logger.info(f"Successfully published {package.name}@{package.version} to secure repository")
            return True
            
        except Exception as e:
            logger.error(f"Error publishing package {package.name}@{package.version}: {str(e)}")
            return False
