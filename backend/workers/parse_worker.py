"""
Parse Worker

Processes raw request blobs to extract packages from package-lock.json files.
Handles the Submitted -> Parsed transition by parsing the stored JSON blob.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from database.service import DatabaseService
from database.operations import DatabaseOperations
from database.models import Package, PackageStatus, Request, RequestPackage
from workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class ParseWorker(BaseWorker):
    """Background worker for parsing package-lock.json blobs and extracting packages"""

    WORKER_TYPE = "parse_worker"

    def __init__(self, sleep_interval: int = 10):
        super().__init__("ParseWorker", sleep_interval)
        self.max_requests_per_cycle = 5  # Process max 5 requests per cycle
        self.stuck_request_timeout = timedelta(minutes=15)
        self.db_service = None
        self.ops = None

    def initialize(self) -> None:
        logger.info("Initializing ParseWorker...")
        # Initialize database service
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is required")
        
        self.db_service = DatabaseService(database_url)
        logger.info("ParseWorker database service initialized")

    def process_cycle(self) -> None:
        try:
            with self.db_service.get_session() as session:
                self.ops = DatabaseOperations(session)
                self._handle_stuck_requests()
                self._process_submitted_requests()
        except Exception as e:
            logger.error(f"Error in parse cycle: {str(e)}", exc_info=True)

    def _handle_stuck_requests(self) -> None:
        """Handle requests that have been stuck in processing too long"""
        try:
            stuck_threshold = datetime.utcnow() - self.stuck_request_timeout
            
            # Find requests that have been processing too long
            # Note: This is a simplified version - in practice, you might want to add a status field to Request
            stuck_requests = self.ops.get_pending_requests(Request)
            stuck_requests = [r for r in stuck_requests if r.created_at < stuck_threshold]
            
            if stuck_requests:
                logger.warning(f"Found {len(stuck_requests)} potentially stuck requests")
                # In a real implementation, you might want to add retry logic or error handling
                    
        except Exception as e:
            logger.error(f"Error handling stuck requests: {str(e)}", exc_info=True)

    def _process_submitted_requests(self) -> None:
        """Process requests that need package extraction"""
        try:
            # Find requests that have raw_request_blob but no packages yet
            # This is a simplified version - in practice, you might want to add a status field to Request
            all_requests = self.ops.get_pending_requests(Request)
            logger.debug(f"Found {len(all_requests)} total requests in database")
            
            requests_to_process = [
                r for r in all_requests 
                if r.raw_request_blob and not r.request_packages
            ][:self.max_requests_per_cycle]
            
            if not requests_to_process:
                if not all_requests:
                    logger.info("ParseWorker heartbeat: No requests found in database to parse")
                else:
                    logger.info(f"ParseWorker heartbeat: No requests found to parse - {len(all_requests)} requests exist but all are either processed or have no raw_request_blob")
                return
                
            logger.info(f"Processing {len(requests_to_process)} requests for package extraction")
            
            for request in requests_to_process:
                try:
                    self._parse_request_blob(request)
                except Exception as e:
                    logger.error(
                        f"Failed to parse request {request.id}: {str(e)}",
                        exc_info=True,
                    )
                    # Mark request as failed (could add a status field to Request model)
                    
        except Exception as e:
            logger.error(f"Error processing submitted requests: {str(e)}", exc_info=True)

    def _parse_request_blob(self, request: Request) -> None:
        """Parse a request's raw blob and extract packages"""
        try:
            # Parse the JSON blob
            package_data = json.loads(request.raw_request_blob)
            
            # Validate the package-lock.json file
            self._validate_package_lock_file(package_data)
            
            # Extract packages from the JSON data
            packages = self._extract_packages_from_json(package_data)
            
            # Filter and process packages
            packages_to_process, existing_packages = self._filter_new_packages(packages, request.id)
            
            # Create database records for new packages
            self._create_package_records(packages_to_process, request.id)
            
            logger.info(
                f"Request {request.id}: Created {len(packages_to_process)} new packages, "
                f"linked {len(existing_packages)} existing packages"
            )
            
        except Exception as e:
            logger.error(f"Error parsing request {request.id} blob: {str(e)}")
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
        logger.info(f"Processing package-lock.json with {len(packages)} package entries")
        return dict(packages)

    def _filter_new_packages(
        self, packages: Dict[str, Any], request_id: int
    ) -> tuple[List[Dict[str, Any]], List[Package]]:
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

        logger.info(f"Deduplicated {len(packages)} package entries to {len(unique_packages)} unique packages")

        # Now process the deduplicated packages
        for package_key, package_data in unique_packages.items():
            package_name = package_data["name"]
            package_version = package_data["version"]
            package_info = package_data["info"]

            # Check if package already exists in database (deduplicated across all requests)
            existing_package = self.ops.get_package_by_name_version(package_name, package_version, Package)

            if existing_package:
                # Check if this package is already linked to this request
                existing_link = self.ops.get_request_package_link(request_id, existing_package.id, RequestPackage)

                if not existing_link:
                    # Create link between request and existing package
                    self.ops.create_request_package_link(request_id, existing_package.id, "existing", RequestPackage)

                existing_packages.append(existing_package)
                continue

            # Create new package object with proper field mapping
            package_data = {
                "name": package_name,
                "version": package_version,
                "npm_url": package_info.get("resolved"),  # Map resolved URL to npm_url
                "integrity": package_info.get("integrity"),  # Map integrity hash
                "license_identifier": package_info.get("license"),  # Map license to license_identifier
            }
            packages_to_process.append(package_data)

        return packages_to_process, existing_packages

    def _extract_package_name(self, package_path: str, package_info: Dict[str, Any]) -> Optional[str]:
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

    def _create_package_records(self, packages_to_process: List[Dict[str, Any]], request_id: int) -> List[Package]:
        """Create database records for new packages"""
        # Use the shared operations to create package records
        package_objects = self.ops.create_package_records(
            packages_to_process, 
            request_id, 
            Package, 
            PackageStatus, 
            RequestPackage
        )
        
        for package in package_objects:
            logger.info(f"Added package for processing: {package.name}@{package.version} (type: new)")
        
        return package_objects

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