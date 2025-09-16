import json
import logging
import os
import subprocess
import tempfile
from typing import Any, Dict, List, Optional

from config.constants import SECURE_REPO_URL
from models import (
    Package,
    PackageRequest,
    RepositoryConfig,
    db,
)

from .license_service import LicenseService
from .package_processor import PackageProcessor
from .package_request_status_manager import PackageRequestStatusManager
from .trivy_service import TrivyService

logger = logging.getLogger(__name__)


class PackageService:
    def __init__(self) -> None:
        # Don't initialize any config values - they'll be loaded dynamically
        self._config_loaded = False
        self._config_cache: Dict[str, Any] = {}
        self.license_service = LicenseService()
        self.trivy_service = TrivyService()

    def _load_config(self) -> None:
        """Load repository configuration from database (only when needed)"""
        if self._config_loaded:
            return

        try:
            # Load from database - use None as defaults to detect missing configuration
            self._config_cache = {
                "source_repo_url": RepositoryConfig.get_config_value(
                    "source_repository_url"
                ),
                "target_repo_url": RepositoryConfig.get_config_value(
                    "target_repository_url"
                ),
            }

            # Set secure_repo_url based on target_repo_url or environment
            if self._config_cache["target_repo_url"]:
                self._config_cache["secure_repo_url"] = SECURE_REPO_URL
            else:
                self._config_cache["secure_repo_url"] = SECURE_REPO_URL

            self._config_loaded = True

            # Log configuration status
            if all(
                self._config_cache[key]
                for key in ["source_repo_url", "target_repo_url"]
            ):
                logger.info(
                    f"Loaded repository configuration: source={self._config_cache['source_repo_url']}, target={self._config_cache['target_repo_url']}"
                )
            else:
                logger.warning(
                    "Repository configuration is incomplete - some values are missing"
                )

        except Exception as e:
            logger.warning(
                f"Could not load repository config from database: {e}. Configuration will be None."
            )
            # Set all values to None to indicate missing configuration
            self._config_cache = {
                "source_repo_url": None,
                "target_repo_url": None,
                "secure_repo_url": SECURE_REPO_URL,
            }
            self._config_loaded = True

    def refresh_config(self) -> None:
        """Refresh repository configuration from database"""
        self._config_loaded = False
        self._load_config()

    def is_configuration_complete(self) -> bool:
        """Check if repository configuration is complete"""
        self._load_config()
        required_keys = ["source_repo_url", "target_repo_url"]
        return all(self._config_cache.get(key) for key in required_keys)

    def get_missing_config_keys(self) -> List[str]:
        """Get list of missing configuration keys"""
        self._load_config()
        required_keys = ["source_repo_url", "target_repo_url"]
        return [key for key in required_keys if not self._config_cache.get(key)]

    @property
    def source_repo_url(self) -> str:
        self._load_config()
        return str(self._config_cache["source_repo_url"])

    @property
    def target_repo_url(self) -> str:
        self._load_config()
        return str(self._config_cache["target_repo_url"])

    @property
    def secure_repo_url(self) -> str:
        self._load_config()
        return str(self._config_cache["secure_repo_url"])

    def process_package_lock(self, request_id: int, package_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process package-lock.json and extract all packages"""
        try:
            # Validate the package-lock.json file
            self._validate_package_lock_file(package_data)

            # Extract packages from the JSON data
            packages = self._extract_packages_from_json(package_data)

            # Filter and process packages
            packages_to_process, existing_packages = self._filter_new_packages(
                packages, request_id
            )

            # Create database records for new packages
            self._create_package_records(packages_to_process)

            # Update request metadata
            self._update_request_metadata(
                request_id, packages_to_process, existing_packages
            )

            # Start async processing
            self._process_packages_async(request_id)

            return {
                "packages_to_process": len(packages_to_process),
                "existing_packages": len(existing_packages),
                "total_packages": len(packages_to_process) + len(existing_packages),
            }

        except Exception as e:
            logger.error(f"Error processing package-lock.json: {str(e)}")
            raise e

    def _validate_package_lock_file(self, package_data: Dict[str, Any]) -> None:
        """Validate that the package data is a valid package-lock.json file"""
        if "lockfileVersion" not in package_data:
            raise ValueError(
                "This file does not appear to be a package-lock.json file. Missing 'lockfileVersion' field."
            )

        lockfile_version = package_data.get("lockfileVersion")
        if lockfile_version is None or lockfile_version < 3:
            raise ValueError(
                f"Unsupported lockfile version: {lockfile_version}. "
                f"This system only supports package-lock.json files with lockfileVersion 3 or higher. "
                f"Please upgrade your npm version (npm 8+) and regenerate the lockfile."
            )

    def _extract_packages_from_json(self, package_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract package information from package-lock.json data"""
        packages = package_data.get("packages", {})
        logger.info(
            f"Processing package-lock.json with {len(packages)} package entries"
        )
        return dict(packages)

    def _filter_new_packages(self, packages: Dict[str, Any], request_id: int) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Filter packages to find new ones that need processing"""
        packages_to_process = []
        existing_packages = []

        # First, deduplicate packages by name+version within the same lock file
        unique_packages = {}

        for package_path, package_info in packages.items():
            if package_path == "":  # Skip root package
                continue

            package_name = self._extract_package_name(package_path, package_info)
            package_version = package_info.get("version")

            if not package_name or not package_version:
                logger.debug(
                    f"Skipping package at path '{package_path}': name='{package_name}', version='{package_version}'"
                )
                continue

            # Use name+version as the key to deduplicate
            package_key = f"{package_name}@{package_version}"

            # Keep the first occurrence of each unique package
            if package_key not in unique_packages:
                unique_packages[package_key] = {
                    "name": package_name,
                    "version": package_version,
                    "info": package_info,
                }

        logger.info(
            f"Deduplicated {len(packages)} package entries to {len(unique_packages)} unique packages"
        )

        # Now process the deduplicated packages
        for package_key, package_data in unique_packages.items():
            package_name = package_data["name"]
            package_version = package_data["version"]
            package_info = package_data["info"]

            # Check if package already exists in database
            existing_package = Package.query.filter_by(
                name=package_name,
                version=package_version,
                package_request_id=request_id,
            ).first()

            if existing_package:
                existing_packages.append(existing_package)
                continue

            # Create new package object
            package_data = {
                "name": package_name,
                "version": package_version,
                "package_info": package_info,
                "request_id": request_id
            }
            packages_to_process.append(package_data)

        return packages_to_process, existing_packages

    def _extract_package_name(self, package_path: str, package_info: Dict[str, Any]) -> str | None:
        """Extract package name from package info or infer from path"""
        package_name = package_info.get("name")

        # If name is not provided, try to extract it from the path
        if not package_name and package_path.startswith("node_modules/"):
            # Extract package name from path like "node_modules/lodash" -> "lodash"
            path_parts = package_path.split("/")
            if len(path_parts) >= 2:
                package_name = path_parts[1]

        return package_name

    def _create_package_object(
        self, package_name: str, package_version: str, package_info: Dict[str, Any], request_id: int
    ) -> Package:
        """Create a new Package object from package information"""
        return Package(
            name=package_name,
            version=package_version,
            package_request_id=request_id,
            status="requested",
            license_identifier=package_info.get("license"),
            checksum=package_info.get("integrity"),
            npm_url=package_info.get("resolved"),
        )

    def _create_package_records(self, packages_to_process: List[Dict[str, Any]]) -> List[Package]:
        """Create database records for new packages"""
        package_objects = []
        for package_data in packages_to_process:
            package = self._create_package_object(
                package_data["name"],
                package_data["version"], 
                package_data,
                package_data["request_id"]
            )
            db.session.add(package)
            package_objects.append(package)
            logger.info(
                f"Added package for processing: {package.name}@{package.version}"
            )
        return package_objects

    def _update_request_metadata(
        self, request_id: int, packages_to_process: List[Dict[str, Any]], existing_packages: List[Dict[str, Any]]
    ) -> None:
        """Update PackageRequest with total package count and status"""
        package_request = PackageRequest.query.get(request_id)
        if package_request:
            package_request.total_packages = len(packages_to_process) + len(
                existing_packages
            )
            package_request.validated_packages = len(
                existing_packages
            )  # Start with existing validated packages
            db.session.commit()

    def _process_packages_async(self, request_id: int) -> None:
        """Process packages asynchronously (refactored version)"""
        try:
            # Initialize services
            status_manager = PackageRequestStatusManager(db.session)
            package_processor = PackageProcessor(
                self.license_service, self.trivy_service, db.session
            )

            # Process pending packages
            processing_results = package_processor.process_pending_packages(request_id)

            # Update request status based on results
            new_status = status_manager.update_request_status(request_id)

            # Log results
            logger.info(
                f"Processed {processing_results['processed']} packages for request {request_id}, "
                f"new status: {new_status}"
            )

            if processing_results["failed"] > 0:
                logger.warning(
                    f"Failed to process {processing_results['failed']} packages: "
                    f"{processing_results['errors']}"
                )

        except Exception as e:
            logger.error(
                f"Error processing packages for request {request_id}: {str(e)}"
            )
            self._handle_processing_error(request_id, e)

    def _handle_processing_error(self, request_id: int, error: Exception) -> None:
        """Handle errors during package processing"""
        try:
            package_request = PackageRequest.query.get(request_id)
            if package_request:
                package_request.status = "validation_failed"
                db.session.commit()
                logger.info(
                    f"Updated request {request_id} status to validation_failed due to error"
                )
        except Exception as commit_error:
            logger.error(
                f"Failed to update request status after error: {str(commit_error)}"
            )

    def _calculate_security_score(self, package: Package) -> int:
        """Calculate security score for package based on Trivy scan results"""
        try:
            # Use Trivy service to calculate security score from vulnerabilities
            if package.security_scans:
                latest_scan = package.security_scans[-1]
                return (
                    self.trivy_service._calculate_security_score_from_vulnerabilities(
                        latest_scan
                    )
                )
            else:
                return 100  # Default to perfect score if no scans yet

        except Exception as e:
            logger.error(f"Error calculating security score: {str(e)}")
            return 100  # Default to perfect score on error

    def get_package_security_scan_status(self, package_id: int) -> Dict[str, Any] | None:
        """Get security scan status for a package"""
        try:
            return self.trivy_service.get_scan_status(package_id)
        except Exception as e:
            logger.error(
                f"Error getting security scan status for package {package_id}: {str(e)}"
            )
            return None

    def get_package_security_scan_report(self, package_id: int) -> Dict[str, Any] | None:
        """Get detailed security scan report for a package"""
        try:
            return self.trivy_service.get_scan_report(package_id)
        except Exception as e:
            logger.error(
                f"Error getting security scan report for package {package_id}: {str(e)}"
            )
            return None

    def publish_to_secure_repo(self, package: Package) -> bool:
        """Publish package to secure repository using real npm publish"""
        try:

            # Get the target repository URL
            self._load_config()
            target_url = self.target_repo_url or SECURE_REPO_URL
            if not target_url:
                raise ValueError("SECURE_REPO_URL environment variable is required")

            logger.info(
                f"Publishing {package.name}@{package.version} to repository at {target_url}"
            )

            # Create a temporary directory for the package
            with tempfile.TemporaryDirectory() as temp_dir:
                # Create package.json
                package_json = {
                    "name": package.name,
                    "version": package.version,
                    "description": f"Secure package {package.name}",
                    "main": "index.js",
                    "scripts": {"test": 'echo "No tests specified"'},
                    "keywords": ["secure", "validated"],
                    "author": "Secure Package Manager",
                    "license": package.license_identifier or "MIT",
                    "repository": {
                        "type": "git",
                        "url": "https://github.com/secure-package-manager/secure-packages.git",
                    },
                }

                # Write package.json
                package_json_path = os.path.join(temp_dir, "package.json")
                with open(package_json_path, "w") as f:
                    json.dump(package_json, f, indent=2)

                # Create a simple index.js file
                index_js_path = os.path.join(temp_dir, "index.js")
                with open(index_js_path, "w") as f:
                    f.write(f"// Secure package {package.name} v{package.version}\n")
                    f.write("module.exports = {\n")
                    f.write(f'  name: "{package.name}",\n')
                    f.write(f'  version: "{package.version}",\n')
                    f.write(
                        '  description: "This package has been validated and approved by the Secure Package Manager"\n'
                    )
                    f.write("};\n")

                # Create a README.md
                readme_path = os.path.join(temp_dir, "README.md")
                with open(readme_path, "w") as f:
                    f.write(f"# {package.name}\n\n")
                    f.write(f"Version: {package.version}\n\n")
                    f.write(
                        "This package has been validated and approved by the Secure Package Manager.\n\n"
                    )
                    f.write("## Security Information\n\n")
                    f.write(f'- Security Score: {package.security_score or "N/A"}\n')
                    f.write(f'- License: {package.license_identifier or "N/A"}\n')
                    f.write(f"- Status: {package.status}\n")

                # Set npm registry to our secure repository
                registry_url = target_url.rstrip("/")
                if not registry_url.startswith("http"):
                    registry_url = f"http://{registry_url}"

                # Run npm publish
                try:
                    # First, set the registry
                    subprocess.run(
                        ["npm", "config", "set", "registry", registry_url],
                        check=True,
                        capture_output=True,
                        text=True,
                        cwd=temp_dir,
                    )

                    # Publish the package
                    result = subprocess.run(
                        ["npm", "publish", "--access", "public"],
                        check=True,
                        capture_output=True,
                        text=True,
                        cwd=temp_dir,
                    )

                    logger.info(f"npm publish output: {result.stdout}")
                    logger.info(
                        f"Successfully published {package.name}@{package.version} to secure repository"
                    )
                    return True

                except subprocess.CalledProcessError as e:
                    logger.error(f"npm publish failed: {e.stderr}")
                    return False

        except Exception as e:
            logger.error(
                f"Error publishing package {package.name}@{package.version}: {str(e)}"
            )
            return False
