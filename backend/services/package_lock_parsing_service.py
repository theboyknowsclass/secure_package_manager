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

from database.operations import (
    AuditLogOperations,
    PackageOperations,
    PackageStatusOperations,
    RequestOperations,
    RequestPackageOperations,
)
from database.service import DatabaseService

logger = logging.getLogger(__name__)


class PackageLockParsingService:
    """Service for parsing package-lock.json files and extracting packages.

    This service handles the business logic of parsing package-lock.json
    files and extracting package information. It manages its own database
    sessions and operations to maintain proper separation of concerns.
    """

    def __init__(self) -> None:
        """Initialize the parsing service."""
        self.database_url = os.getenv("DATABASE_URL", "")
        self.db_service = DatabaseService(self.database_url)

    def process_requests(self, max_requests_per_cycle: int = 5) -> Dict[str, Any]:
        """Process requests that need parsing.

        This method separates database operations from I/O work:
        1. Get requests that need parsing (short DB session)
        2. Perform parsing work (no DB session)
        3. Update database with results (short DB session)

        Args:
            max_requests_per_cycle: Maximum number of requests to process per cycle

        Returns:
            Dict with processing results
        """
        try:
            # Phase 1: Get request data (short DB session)
            requests_to_process = self._get_requests_for_parsing(max_requests_per_cycle)
            if not requests_to_process:
                return {
                    "success": True,
                    "processed_requests": 0,
                    "total_packages": 0,
                    "message": "No requests to process",
                }

            # Phase 2: Perform parsing work (no DB session)
            parsing_results = self._perform_parsing_batch(requests_to_process)

            # Phase 3: Update database with results (short DB session)
            return self._update_parsing_results(parsing_results)

        except Exception as e:
            logger.error(f"Error processing parsing requests: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "processed_requests": 0,
                "total_packages": 0,
            }

    def _get_requests_for_parsing(self, max_requests: int) -> List[Any]:
        """Get requests that need package lock parsing (short DB session)."""
        with self.db_service.get_session() as session:
            request_ops = RequestOperations(session)
            requests = request_ops.get_needing_parsing()
            logger.info(f"Found {len(requests)} requests needing parsing")
            if requests:
                logger.info(f"Request IDs needing parsing: {[r.id for r in requests]}")

            # Limit the number of requests processed per cycle
            return requests[:max_requests]

    def _perform_parsing_batch(self, requests: List[Any]) -> List[Tuple[Any, Dict[str, Any]]]:
        """Perform package lock parsing work (no DB session)."""
        parsing_results = []

        for request in requests:
            try:
                # Pure I/O work - no database operations
                result = self._parse_package_lock_data_only(request)
                parsing_results.append((request, result))
            except Exception as e:
                logger.error(f"Error parsing request {request.id}: {str(e)}")
                parsing_results.append((request, {"status": "failed", "error": str(e)}))

        return parsing_results

    def _update_parsing_results(self, parsing_results: List[Tuple[Any, Dict[str, Any]]]) -> Dict[str, Any]:
        """Update database with parsing results (short DB session)."""
        successful_count = 0
        failed_count = 0
        total_packages = 0

        with self.db_service.get_session() as session:
            request_ops = RequestOperations(session)
            request_package_ops = RequestPackageOperations(session)
            package_ops = PackageOperations(session)
            package_status_ops = PackageStatusOperations(session)
            audit_log_ops = AuditLogOperations(session)

            for request, result in parsing_results:
                try:
                    # Verify request still needs processing (race condition protection)
                    current_request = request_ops.get_by_id(request.id)
                    if not current_request or current_request.raw_request_blob is None:
                        continue

                    if result["status"] == "success":
                        # Store parsed packages
                        if "packages" in result:
                            self._store_parsed_packages(
                                request.id,
                                result["packages"],
                                request_ops,
                                request_package_ops,
                                package_ops,
                                package_status_ops,
                                audit_log_ops,
                            )
                            total_packages += result.get("total_packages", 0)

                        successful_count += 1
                        logger.info(
                            f"Successfully parsed request {request.id}: "
                            f"Created {result.get('packages_to_process', 0)} new packages, "
                            f"linked {result.get('existing_packages', 0)} existing packages"
                        )
                    else:
                        # Handle failure
                        failed_count += 1
                        logger.error(f"Failed to parse request {request.id}: {result.get('error', 'Unknown error')}")

                except Exception as e:
                    logger.error(f"Error updating request {request.id}: {str(e)}")
                    failed_count += 1

            session.commit()

        return {
            "success": True,
            "processed_requests": len(parsing_results),
            "successful_parsing": successful_count,
            "failed_parsing": failed_count,
            "total_packages": total_packages,
            "message": f"Processed {len(parsing_results)} requests with {total_packages} total packages",
        }

    def _parse_package_lock_data_only(self, request: Any) -> Dict[str, Any]:
        """Parse package lock file (pure I/O work, no database operations)."""
        try:
            # Extract request information
            request_id = request.id
            package_lock_content = request.raw_request_blob

            # Parse the package-lock.json content
            import json

            package_data = json.loads(package_lock_content)

            # Validate the package-lock.json file
            self._validate_package_lock_file(package_data)

            # Extract packages from the JSON data
            packages = self._extract_packages_from_json(package_data)

            # Deduplicate packages
            unique_packages = self._deduplicate_packages(packages)

            # Prepare packages for processing (without database operations)
            packages_to_process = []
            existing_packages_count = 0

            for package_key, package_data in unique_packages.items():
                package_name = package_data["name"]
                package_version = package_data["version"]
                package_info = package_data["info"]

                # We'll check for existing packages in the database update phase
                # For now, just prepare the data
                packages_to_process.append(
                    {
                        "name": package_name,
                        "version": package_version,
                        "info": package_info,
                        "request_id": request_id,
                    }
                )

            return {
                "status": "success",
                "request_id": request_id,
                "packages": packages_to_process,
                "total_packages": len(unique_packages),
                "packages_to_process": len(packages_to_process),
                "existing_packages": existing_packages_count,
            }

        except Exception as e:
            logger.error(f"Error parsing package lock for request {request_id}: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "request_id": request_id,
            }

    def _store_parsed_packages(
        self,
        request_id: int,
        packages: List[Dict[str, Any]],
        request_ops: Any,
        request_package_ops: Any,
        package_ops: Any,
        package_status_ops: Any,
        audit_log_ops: Any,
    ) -> None:
        """Store parsed packages in database."""
        packages_to_process = []
        existing_packages = []

        for package_data in packages:
            package_name = package_data["name"]
            package_version = package_data["version"]

            # Check if package already exists in database
            existing_package = package_ops.get_by_name_version(package_name, package_version)

            if existing_package:
                # Link existing package to this request if not already linked
                if not request_package_ops.link_exists(request_id, existing_package.id):
                    request_package_ops.create_link(request_id, existing_package.id, "existing")
                existing_packages.append(existing_package)
            else:
                packages_to_process.append(package_data)

        # Create new packages
        created_packages = []
        for package_data in packages_to_process:
            package_info = package_data["info"]
            package_record_data = {
                "name": package_data["name"],
                "version": package_data["version"],
                "npm_url": package_info.get("resolved"),
                "integrity": package_info.get("integrity"),
                "license_identifier": package_info.get("license"),
            }

            # Create package with initial status
            package = package_ops.create_with_status(package_record_data, status="Checking Licence")

            # Create request-package link
            request_package_ops.create_link(request_id, package.id, "new")
            created_packages.append(package)

            logger.info(f"Created new package: {package.name}@{package.version}")

        # Log the parsing results
        logger.info(
            f"Request {request_id} parsing complete: "
            f"{len(created_packages)} new packages, "
            f"{len(existing_packages)} existing packages"
        )

    def _validate_package_lock_file(self, package_data: Dict[str, Any]) -> None:
        """Validate that the package data is a valid package-lock.json file."""
        if "lockfileVersion" not in package_data:
            raise ValueError("This file does not appear to be a package-lock.json file. " "Missing 'lockfileVersion' field.")

        lockfile_version = package_data.get("lockfileVersion")
        if lockfile_version is None or lockfile_version < 3:
            raise ValueError(
                f"Unsupported lockfile version: {lockfile_version}. "
                f"This system only supports package-lock.json files with "
                f"lockfileVersion 3 or higher. "
                f"Please upgrade your npm version (npm 8+) and regenerate the lockfile."
            )

    def _extract_packages_from_json(self, package_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract package information from package-lock.json data."""
        packages = package_data.get("packages", {})
        logger.info(f"Processing package-lock.json with {len(packages)} package entries")
        return dict(packages)

    def _deduplicate_packages(self, packages: Dict[str, Any]) -> Dict[str, Any]:
        """Deduplicate packages by name+version within the same lock file."""
        unique_packages = {}

        for package_path, package_info in packages.items():
            if package_path == "":  # Skip root package
                continue

            package_name = self._extract_package_name(package_path, package_info)
            package_version = package_info.get("version")

            if not package_name or not package_version:
                logger.debug(f"Skipping package at path '{package_path}': " f"name='{package_name}', version='{package_version}'")
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

        logger.info(f"Deduplicated {len(packages)} package entries to " f"{len(unique_packages)} unique packages")
        return unique_packages

    def _extract_package_name(self, package_path: str, package_info: Dict[str, Any]) -> Optional[str]:
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
                remaining_path = package_path[last_node_modules + len("node_modules/") :]
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
