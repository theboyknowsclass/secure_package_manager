"""Package Parsing Service - Refactored.

Handles parsing of package-lock.json files and extracting package
information. This service is used by both the API (for immediate
processing) and workers (for background processing).

This refactored version works with the new entity-based operations
structure and focuses purely on business logic.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class PackageLockParsingService:
    """Service for parsing package-lock.json files and extracting packages.

    This service handles the business logic of parsing package-lock.json
    files and extracting package information. It works with database
    operations passed in from the caller (worker or API) to maintain
    separation of concerns.
    """

    def parse_package_lock(
        self,
        request_id: int,
        package_data: Dict[str, Any],
        ops: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Parse package-lock.json and extract all packages.

        Args:
            request_id: ID of the request this package-lock belongs to
            package_data: The parsed JSON data from package-lock.json
            ops: Dictionary of database operations instances

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
                packages, request_id, ops
            )

            # Create database records for new packages
            created_packages = self._create_package_records(
                packages_to_process, request_id, ops
            )

            logger.info(
                f"Parsed {len(packages_to_process)} new packages and {len(existing_packages)} existing packages for request {request_id}"
            )

            return {
                "packages_to_process": len(packages_to_process),
                "existing_packages": len(existing_packages),
                "total_packages": len(packages_to_process)
                + len(existing_packages),
                "created_packages": created_packages,
            }

        except Exception as e:
            logger.error(f"Error parsing package-lock.json: {str(e)}")
            raise e

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
        self, packages: Dict[str, Any], request_id: int, ops: Dict[str, Any]
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
            existing_package = ops["package"].get_by_name_version(
                package_name, package_version
            )

            if existing_package:
                # Link existing package to this request if not already linked
                self._link_existing_package_to_request(
                    request_id, existing_package, ops
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
            # For regular packages: "node_modules/lodash" -> "lodash"
            # For scoped packages: "node_modules/@nodelib/package_name" ->
            # "@nodelib/package_name"
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

    def _link_existing_package_to_request(
        self, request_id: int, existing_package: Any, ops: Dict[str, Any]
    ) -> None:
        """Link an existing package to a request if not already linked."""
        # Check if link already exists
        if not ops["request_package"].link_exists(
            request_id, existing_package.id
        ):
            # Create link between request and existing package
            ops["request_package"].create_link(
                request_id, existing_package.id, "existing"
            )

    def _create_package_records(
        self,
        packages_to_process: List[Dict[str, Any]],
        request_id: int,
        ops: Dict[str, Any],
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
            package = ops["package"].create_with_status(
                package_record_data, status="Submitted"
            )

            # Create request-package link
            ops["request_package"].create_link(request_id, package.id, "new")

            created_packages.append(package)
            logger.info(
                f"Created new package: {package.name}@{package.version}"
            )

        return created_packages
