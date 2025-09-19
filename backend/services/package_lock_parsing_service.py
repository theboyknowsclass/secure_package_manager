"""Package Parsing Service.

Handles parsing of package-lock.json files and extracting package
information. This service is used by both the API (for immediate
processing) and workers (for background processing).

This service manages its own database sessions and operations to maintain
proper separation of concerns.
"""

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from database.session_helper import SessionHelper
from database.operations import (
    RequestOperations,
    RequestPackageOperations,
    PackageOperations,
    PackageStatusOperations,
    AuditLogOperations
)

logger = logging.getLogger(__name__)


class PackageLockParsingService:
    """Service for parsing package-lock.json files and extracting packages.

    This service handles the business logic of parsing package-lock.json
    files and extracting package information. It manages its own database
    sessions and operations to maintain proper separation of concerns.
    """

    def __init__(self):
        """Initialize the parsing service."""
        self._session = None
        self._request_ops = None
        self._request_package_ops = None
        self._package_ops = None
        self._package_status_ops = None
        self._audit_log_ops = None

    def _setup_operations(self, session):
        """Set up operations instances for the current session."""
        self._session = session
        self._request_ops = RequestOperations(session)
        self._request_package_ops = RequestPackageOperations(session)
        self._package_ops = PackageOperations(session)
        self._package_status_ops = PackageStatusOperations(session)
        self._audit_log_ops = AuditLogOperations(session)

    def parse_package_lock(
        self,
        request_id: int,
        package_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Parse package-lock.json and extract all packages.

        Args:
            request_id: ID of the request this package-lock belongs to
            package_data: The parsed JSON data from package-lock.json

        Returns:
            Dict with processing results
        """
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
            created_packages = self._create_package_records(
                packages_to_process, request_id
            )

            # Link existing packages to the request
            linked_packages = self._link_existing_packages(
                existing_packages, request_id
            )

            # Log the parsing results
            self._log_parsing_results(
                request_id, created_packages, linked_packages
            )

            logger.info(
                f"Parsed {len(packages_to_process)} new packages and {len(existing_packages)} existing packages for request {request_id}"
            )

            return {
                "success": True,
                "packages_to_process": len(created_packages),
                "existing_packages": len(linked_packages),
                "total_packages": len(packages),
                "created_packages": created_packages,
                "linked_packages": linked_packages,
            }

        except Exception as e:
            logger.error(f"Error parsing package-lock for request {request_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "packages_to_process": 0,
                "existing_packages": 0,
                "total_packages": 0,
            }

    def process_requests(self, max_requests_per_cycle: int = 5) -> Dict[str, Any]:
        """Process requests that need parsing.
        
        Args:
            max_requests_per_cycle: Maximum number of requests to process per cycle
            
        Returns:
            Dict with processing results
        """
        try:
            with SessionHelper.get_session() as db:
                # Set up operations instances
                self._setup_operations(db.session)
                
                # Process requests that need parsing
                result = self._process_submitted_requests(max_requests_per_cycle)
                
                # Commit the transaction
                db.commit()
                
                return result
                
        except Exception as e:
            logger.error(f"Error in parsing service: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "processed_requests": 0,
                "total_packages": 0,
            }


    def _process_submitted_requests(self, max_requests_per_cycle: int) -> Dict[str, Any]:
        """Process requests that need package extraction."""
        try:
            # Find requests that need parsing
            requests_to_process = self._request_ops.get_needing_parsing()
            logger.info(f"Found {len(requests_to_process)} requests needing parsing")
            if requests_to_process:
                logger.info(f"Request IDs needing parsing: {[r.id for r in requests_to_process]}")

            # Limit the number of requests processed per cycle
            requests_to_process = requests_to_process[:max_requests_per_cycle]

            if not requests_to_process:
                logger.info("ParseWorker heartbeat: No requests found to parse")
                return {
                    "success": True,
                    "processed_requests": 0,
                    "total_packages": 0,
                    "message": "No requests to process"
                }

            logger.info(
                f"Processing {len(requests_to_process)} requests for package extraction"
            )

            total_packages = 0
            processed_requests = 0

            for request in requests_to_process:
                try:
                    # Parse the JSON blob
                    import json
                    package_data = json.loads(request.raw_request_blob)

                    # Parse the package lock
                    result = self.parse_package_lock(request.id, package_data)
                    
                    if result["success"]:
                        total_packages += result["total_packages"]
                        processed_requests += 1
                        logger.info(
                            f"Successfully parsed request {request.id}: "
                            f"Created {result.get('packages_to_process', 0)} new packages, "
                            f"linked {result.get('existing_packages', 0)} existing packages"
                        )
                    else:
                        logger.error(f"Failed to parse request {request.id}: {result.get('error', 'Unknown error')}")

                except Exception as e:
                    logger.error(
                        f"Failed to parse request {request.id}: {str(e)}",
                        exc_info=True,
                    )

            return {
                "success": True,
                "processed_requests": processed_requests,
                "total_packages": total_packages,
                "message": f"Processed {processed_requests} requests with {total_packages} total packages"
            }

        except Exception as e:
            logger.error(
                f"Error processing submitted requests: {str(e)}", exc_info=True
            )
            return {
                "success": False,
                "error": str(e),
                "processed_requests": 0,
                "total_packages": 0,
            }

    def _validate_package_lock_file(
        self, package_data: Dict[str, Any]
    ) -> None:
        """Validate that the package data is a valid package-lock.json file."""
        if "lockfileVersion" not in package_data:
            raise ValueError(
                "This file does not appear to be a package-lock.json file. "
                "Missing 'lockfileVersion' field."
            )

        lockfile_version = package_data.get("lockfileVersion")
        if lockfile_version is None or lockfile_version < 3:
            raise ValueError(
                f"Unsupported lockfile version: {lockfile_version}. "
                f"This system only supports package-lock.json files with "
                f"lockfileVersion 3 or higher. "
                f"Please upgrade your npm version (npm 8+) and regenerate the lockfile."
            )

    def _extract_packages_from_json(
        self, package_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract package information from package-lock.json data."""
        packages = package_data.get("packages", {})
        logger.info(
            f"Processing package-lock.json with {len(packages)} package entries"
        )
        return dict(packages)

    def _filter_new_packages(
        self, packages: Dict[str, Any], request_id: int
    ) -> Tuple[List[Dict[str, Any]], List[Any]]:
        """Filter packages to find new ones that need processing.

        Returns:
            Tuple of (packages_to_process, existing_packages)
        """
        packages_to_process = []
        existing_packages = []

        # First, deduplicate packages by name+version within the same lock file
        unique_packages = self._deduplicate_packages(packages)

        # Now process the deduplicated packages
        for package_key, package_data in unique_packages.items():
            package_name = package_data["name"]
            package_version = package_data["version"]
            package_info = package_data["info"]

            # Check if package already exists in database
            existing_package = self._package_ops.get_by_name_version(
                package_name, package_version
            )

            if existing_package:
                # Link existing package to this request if not already linked
                self._link_existing_package_to_request(
                    request_id, existing_package
                )
                existing_packages.append(existing_package)
            else:
                # This is a new package that needs processing
                packages_to_process.append(
                    {
                        "name": package_name,
                        "version": package_version,
                        "info": package_info,
                        "request_id": request_id,
                    }
                )

        return packages_to_process, existing_packages

    def _deduplicate_packages(
        self, packages: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deduplicate packages by name+version within the same lock file."""
        unique_packages = {}

        for package_path, package_info in packages.items():
            if package_path == "":  # Skip root package
                continue

            package_name = self._extract_package_name(
                package_path, package_info
            )
            package_version = package_info.get("version")

            if not package_name or not package_version:
                logger.debug(
                    f"Skipping package at path '{package_path}': "
                    f"name='{package_name}', version='{package_version}'"
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
            f"Deduplicated {len(packages)} package entries to "
            f"{len(unique_packages)} unique packages"
        )
        return unique_packages

    def _extract_package_name(
        self, package_path: str, package_info: Dict[str, Any]
    ) -> Optional[str]:
        """Extract package name from package info or infer from path."""
        package_name = package_info.get("name")

        # If name is not provided, try to extract it from the path
        if not package_name and package_path.startswith("node_modules/"):
            # Extract package name from path
            # Handle nested packages by finding the last node_modules segment
            # Examples:
            # "node_modules/lodash" -> "lodash"
            # "node_modules/@nodelib/package_name" -> "@nodelib/package_name"
            # "node_modules/test-exclude/node_modules/minimatch" -> "minimatch"
            # "node_modules/test-exclude/node_modules/@types/node" -> "@types/node"
            
            # Find the last occurrence of "node_modules/" in the path
            last_node_modules = package_path.rfind("node_modules/")
            if last_node_modules != -1:
                # Get the part after the last "node_modules/"
                remaining_path = package_path[last_node_modules + len("node_modules/"):]
                path_parts = remaining_path.split("/")
                
                if len(path_parts) >= 1:
                    if path_parts[0].startswith("@"):
                        # Scoped package: take both scope and package name
                        if len(path_parts) >= 2:
                            package_name = f"{path_parts[0]}/{path_parts[1]}"
                        else:
                            package_name = path_parts[0]
                    else:
                        # Regular package: take just the package name
                        package_name = path_parts[0]

        return package_name

    def _link_existing_package_to_request(
        self, request_id: int, existing_package: Any
    ) -> None:
        """Link an existing package to a request if not already linked."""
        # Check if link already exists
        if not self._request_package_ops.link_exists(
            request_id, existing_package.id
        ):
            # Create link between request and existing package
            self._request_package_ops.create_link(
                request_id, existing_package.id, "existing"
            )

    def _create_package_records(
        self,
        packages_to_process: List[Dict[str, Any]],
        request_id: int,
    ) -> List[Any]:
        """Create database records for new packages."""
        created_packages = []

        for package_data in packages_to_process:
            # Create package object with proper field mapping
            package_info = package_data["info"]
            package_record_data = {
                "name": package_data["name"],
                "version": package_data["version"],
                "npm_url": package_info.get("resolved"),
                "integrity": package_info.get("integrity"),
                "license_identifier": package_info.get("license"),
            }

            # Create package with initial status
            package = self._package_ops.create_with_status(
                package_record_data, status="Checking Licence"
            )

            # Create request-package link
            self._request_package_ops.create_link(request_id, package.id, "new")

            created_packages.append(package)
            logger.info(
                f"Created new package: {package.name}@{package.version}"
            )

        return created_packages

    def _link_existing_packages(
        self, existing_packages: List[Any], request_id: int
    ) -> List[Any]:
        """Link existing packages to a request."""
        linked_packages = []
        for existing_package in existing_packages:
            self._link_existing_package_to_request(request_id, existing_package)
            linked_packages.append(existing_package)
        return linked_packages

    def _log_parsing_results(
        self, request_id: int, created_packages: List[Any], linked_packages: List[Any]
    ) -> None:
        """Log the results of parsing a request."""
        logger.info(
            f"Request {request_id} parsing complete: "
            f"{len(created_packages)} new packages, "
            f"{len(linked_packages)} existing packages"
        )
