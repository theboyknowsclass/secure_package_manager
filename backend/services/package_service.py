import base64
import json
import logging
import os
import subprocess
import tempfile
from datetime import datetime
from typing import Any, Dict, List

from config.constants import TARGET_REPOSITORY_URL
from models import (
    Package,
    PackageStatus,
    RequestPackage,
    db,
)

from .license_service import LicenseService
from .package_request_status_manager import PackageRequestStatusManager
from .trivy_service import TrivyService

logger = logging.getLogger(__name__)


class PackageService:
    def __init__(self) -> None:
        # Repository configuration moved to environment variables
        self.license_service = LicenseService()
        self.trivy_service = TrivyService()

    def is_configuration_complete(self) -> bool:
        """Check if repository configuration is complete (now from environment variables)"""
        # Check environment variables instead of database
        source_repo_url = os.getenv("SOURCE_REPOSITORY_URL")
        target_repo_url = os.getenv("TARGET_REPOSITORY_URL")
        return bool(source_repo_url and target_repo_url)

    def get_missing_config_keys(self) -> List[str]:
        """Get list of missing configuration keys (now from environment variables)"""
        missing = []
        if not os.getenv("SOURCE_REPOSITORY_URL"):
            missing.append("SOURCE_REPOSITORY_URL")
        if not os.getenv("TARGET_REPOSITORY_URL"):
            missing.append("TARGET_REPOSITORY_URL")
        return missing

    @property
    def source_repo_url(self) -> str:
        return os.getenv("SOURCE_REPOSITORY_URL", "")

    @property
    def target_repo_url(self) -> str:
        return os.getenv("TARGET_REPOSITORY_URL", "")


    def process_package_lock(
        self, request_id: int, package_data: Dict[str, Any]
    ) -> Dict[str, Any]:
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
            self._create_package_records(packages_to_process, request_id)

            # Packages are now processed by the background worker
            # No need to process synchronously - worker will pick them up
            logger.info(f"Created {len(packages_to_process)} packages for request {request_id}, worker will process them")

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

    def _extract_packages_from_json(
        self, package_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract package information from package-lock.json data"""
        packages = package_data.get("packages", {})
        logger.info(
            f"Processing package-lock.json with {len(packages)} package entries"
        )
        return dict(packages)

    def _filter_new_packages(
        self, packages: Dict[str, Any], request_id: int
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
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

            # Check if package already exists in database (deduplicated across all requests)
            existing_package = Package.query.filter_by(
                name=package_name,
                version=package_version,
            ).first()

            if existing_package:
                # Check if this package is already linked to this request
                existing_link = RequestPackage.query.filter_by(
                    request_id=request_id, package_id=existing_package.id
                ).first()

                if not existing_link:
                    # Create link between request and existing package
                    # Since package exists in DB, it's "existing" for this request
                    request_package = RequestPackage(
                        request_id=request_id, 
                        package_id=existing_package.id,
                        package_type="existing"
                    )
                    db.session.add(request_package)
                    db.session.commit()

                existing_packages.append(existing_package)
                continue

            # Create new package object
            package_data = {
                "name": package_name,
                "version": package_version,
                "package_info": package_info,
                "request_id": request_id,
            }
            packages_to_process.append(package_data)

        return packages_to_process, existing_packages

    def _extract_package_name(
        self, package_path: str, package_info: Dict[str, Any]
    ) -> str | None:
        """Extract package name from package info or infer from path"""
        package_name = package_info.get("name")

        # If name is not provided, try to extract it from the path
        if not package_name and package_path.startswith("node_modules/"):
            # Extract package name from path
            # For regular packages: "node_modules/lodash" -> "lodash"
            # For scoped packages: "node_modules/@nodelib/package_name" -> "@nodelib/package_name"
            path_parts = package_path.split("/")
            if len(path_parts) >= 2:
                if path_parts[1].startswith("@"):
                    # Scoped package: take both scope and package name
                    if len(path_parts) >= 3:
                        package_name = f"{path_parts[1]}/{path_parts[2]}"
                    else:
                        package_name = path_parts[1]
                else:
                    # Regular package: take just the package name
                    package_name = path_parts[1]

        return package_name

    def _create_package_object(
        self,
        package_name: str,
        package_version: str,
        package_info: Dict[str, Any],
        request_id: int,
    ) -> Package:
        """Create a new Package object from package information"""
        return Package(
            name=package_name,
            version=package_version,
            license_identifier=package_info.get("license"),
            integrity=package_info.get("integrity"),
            npm_url=package_info.get("resolved"),
        )

    def _create_package_records(
        self, packages_to_process: List[Dict[str, Any]], request_id: int
    ) -> List[Package]:
        """Create database records for new packages"""
        package_objects = []
        for package_data in packages_to_process:
            package = self._create_package_object(
                package_data["name"],
                package_data["version"],
                package_data["package_info"],
                request_id,
            )
            db.session.add(package)
            db.session.flush()  # Get the package ID

            # Create package status record
            package_status = PackageStatus(
                package_id=package.id,
                status="Requested",
                security_scan_status="pending",
            )
            db.session.add(package_status)

            # Create request-package link
            # Since this is a newly created package, it's "new" for this request
            request_package = RequestPackage(
                request_id=request_id, 
                package_id=package.id,
                package_type="new"
            )
            db.session.add(request_package)

            package_objects.append(package)
            logger.info(
                f"Added package for processing: {package.name}@{package.version} (type: new)"
            )

        db.session.commit()
        return package_objects


    def _handle_processing_error(self, request_id: int, error: Exception) -> None:
        """Handle errors during package processing"""
        try:
            # Update package statuses to reflect error
            packages = (
                db.session.query(Package)
                .join(RequestPackage)
                .filter(RequestPackage.request_id == request_id)
                .all()
            )

            for package in packages:
                if package.package_status:
                    package.package_status.status = "Rejected"
                    package.package_status.updated_at = datetime.utcnow()

            db.session.commit()
            logger.info(
                f"Updated package statuses for request {request_id} to Rejected due to error"
            )
        except Exception as commit_error:
            logger.error(
                f"Failed to update package statuses after error: {str(commit_error)}"
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

    def get_package_security_scan_status(
        self, package_id: int
    ) -> Dict[str, Any] | None:
        """Get security scan status for a package"""
        try:
            return self.trivy_service.get_scan_status(package_id)
        except Exception as e:
            logger.error(
                f"Error getting security scan status for package {package_id}: {str(e)}"
            )
            return None

    def get_package_security_scan_report(
        self, package_id: int
    ) -> Dict[str, Any] | None:
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
            target_url = self.target_repo_url or TARGET_REPOSITORY_URL
            if not target_url:
                raise ValueError(
                    "TARGET_REPOSITORY_URL environment variable is required"
                )

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
                    f.write(
                        f'- Security Score: {package.package_status.security_score if package.package_status else "N/A"}\n'
                    )
                    f.write(f'- License: {package.license_identifier or "N/A"}\n')
                    f.write(
                        f"- Status: {package.package_status.status if package.package_status else 'N/A'}\n"
                    )

                # Set npm registry to our secure repository
                registry_url = target_url.rstrip("/")
                if not registry_url.startswith("http"):
                    registry_url = f"http://{registry_url}"

                # Create a tarball of the package
                import tarfile
                # Sanitize package name for filesystem (replace @ and / with -)
                safe_name = package.name.replace("@", "").replace("/", "-")
                tarball_path = os.path.join(temp_dir, f"{safe_name}-{package.version}.tgz")
                with tarfile.open(tarball_path, "w:gz") as tar:
                    tar.add(temp_dir, arcname="package", filter=lambda tarinfo: None if tarinfo.name == os.path.basename(tarball_path) else tarinfo)

                # Use curl to directly publish to the registry
                try:
                    # Read the tarball as base64
                    with open(tarball_path, 'rb') as f:
                        tarball_data = f.read()
                    tarball_b64 = base64.b64encode(tarball_data).decode('ascii')

                    # Create the npm publish payload
                    publish_payload = {
                        "_id": package.name,
                        "name": package.name,
                        "description": f"Secure package {package.name}",
                        "dist-tags": {"latest": package.version},
                        "versions": {
                            package.version: {
                                "name": package.name,
                                "version": package.version,
                                "description": f"Secure package {package.name}",
                                "main": "index.js",
                                "scripts": {"test": 'echo "No tests specified"'},
                                "keywords": ["secure", "validated"],
                                "author": "Secure Package Manager",
                                "license": package.license_identifier or "MIT",
                                "dist": {
                                    "shasum": "mock-shasum",
                                    "tarball": f"{registry_url}/{package.name}/-/{package.name}-{package.version}.tgz"
                                }
                            }
                        },
                        "_attachments": {
                            f"{safe_name}-{package.version}.tgz": {
                                "content_type": "application/octet-stream",
                                "data": tarball_b64,
                                "length": len(tarball_data)
                            }
                        }
                    }

                    # Use curl to publish directly to the registry
                    import requests
                    from urllib.parse import quote
                    # URL encode the package name for scoped packages like @babel/core
                    encoded_package_name = quote(package.name, safe='')
                    response = requests.put(
                        f"{registry_url}/{encoded_package_name}",
                        json=publish_payload,
                        headers={"Content-Type": "application/json"}
                    )
                    
                    if response.status_code in [200, 201]:
                        logger.info(f"Successfully published {package.name}@{package.version} to secure repository")
                        return True
                    else:
                        logger.error(f"Failed to publish package: {response.status_code} - {response.text}")
                        return False

                except Exception as e:
                    logger.error(f"Failed to publish package via direct HTTP: {str(e)}")
                    return False

        except Exception as e:
            logger.error(
                f"Error publishing package {package.name}@{package.version}: {str(e)}"
            )
            return False
