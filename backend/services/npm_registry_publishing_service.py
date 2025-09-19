"""Package Publishing Service.

Handles publishing packages to the secure repository. This service is
used by both the API (for immediate publishing) and workers (for
background publishing).
"""

import base64
import json
import logging
import os
import tarfile
import tempfile
from typing import Optional
from urllib.parse import quote

import requests
from config.constants import TARGET_REPOSITORY_URL
from database.models import Package

logger = logging.getLogger(__name__)


class NpmRegistryPublishingService:
    """Service for publishing packages to secure repository."""

    def __init__(self):
        self.target_repo_url = os.getenv(
            "TARGET_REPOSITORY_URL", TARGET_REPOSITORY_URL
        )

    def publish_to_secure_repo(self, package: Package) -> bool:
        """Publish package to secure repository using direct HTTP API.

        Args:
            package: Package object to publish

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.target_repo_url:
                raise ValueError(
                    "TARGET_REPOSITORY_URL environment variable is required"
                )

            logger.info(
                f"Publishing {package.name}@{package.version} to repository at {self.target_repo_url}"
            )

            # Create package tarball
            tarball_path = self._create_package_tarball(package)
            if not tarball_path:
                return False

            # Upload to registry
            success = self._upload_to_registry(package, tarball_path)

            # Clean up temporary file
            if os.path.exists(tarball_path):
                os.unlink(tarball_path)

            return success

        except Exception as e:
            logger.error(
                f"Error publishing package {package.name}@{package.version}: {str(e)}"
            )
            return False

    def _create_package_tarball(self, package: Package) -> Optional[str]:
        """Create a tarball for the package.

        Args:
            package: Package object

        Returns:
            Path to created tarball or None if failed
        """
        try:
            # Create a temporary directory for the package
            with tempfile.TemporaryDirectory() as temp_dir:
                # Create package.json
                package_json = self._create_package_json(package)
                package_json_path = os.path.join(temp_dir, "package.json")
                with open(package_json_path, "w") as f:
                    json.dump(package_json, f, indent=2)

                # Create a simple index.js file
                self._create_index_js(package, temp_dir)

                # Create a README.md
                self._create_readme(package, temp_dir)

                # Create tarball
                safe_name = package.name.replace("@", "").replace("/", "-")
                tarball_path = os.path.join(
                    temp_dir, f"{safe_name}-{package.version}.tgz"
                )

                with tarfile.open(tarball_path, "w:gz") as tar:
                    tar.add(
                        temp_dir,
                        arcname="package",
                        filter=lambda tarinfo: (
                            None
                            if tarinfo.name == os.path.basename(tarball_path)
                            else tarinfo
                        ),
                    )

                # Move tarball to a permanent location
                permanent_path = os.path.join(
                    temp_dir, f"{safe_name}-{package.version}.tgz"
                )
                os.rename(tarball_path, permanent_path)

                return permanent_path

        except Exception as e:
            logger.error(
                f"Error creating tarball for {package.name}@{package.version}: {str(e)}"
            )
            return None

    def _create_package_json(self, package: Package) -> dict:
        """Create package.json content for the package."""
        return {
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

    def _create_index_js(self, package: Package, temp_dir: str) -> None:
        """Create index.js file for the package."""
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

    def _create_readme(self, package: Package, temp_dir: str) -> None:
        """Create README.md file for the package."""
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
                (
                    f"- Status: {package.package_status.status if package.package_status else 'N/A'}\n"
                )
            )

    def _upload_to_registry(self, package: Package, tarball_path: str) -> bool:
        """Upload package to npm registry using direct HTTP API.

        Args:
            package: Package object
            tarball_path: Path to the tarball file

        Returns:
            True if successful, False otherwise
        """
        try:
            # Read the tarball as base64
            with open(tarball_path, "rb") as f:
                tarball_data = f.read()
            tarball_b64 = base64.b64encode(tarball_data).decode("ascii")

            # URL encode the package name for scoped packages like @babel/core
            encoded_package_name = quote(package.name, safe="")

            # Create the npm publish payload
            publish_payload = self._create_publish_payload(
                package, tarball_b64, tarball_data
            )

            # Upload to registry
            registry_url = self.target_repo_url.rstrip("/")
            if not registry_url.startswith("http"):
                registry_url = f"http://{registry_url}"

            response = requests.put(
                f"{registry_url}/{encoded_package_name}",
                json=publish_payload,
                headers={"Content-Type": "application/json"},
                timeout=60,
            )

            if response.status_code in [200, 201]:
                logger.info(
                    f"Successfully published {package.name}@{package.version} to secure repository"
                )
                return True
            else:
                logger.error(
                    f"Failed to publish package: {response.status_code} - {response.text}"
                )
                return False

        except Exception as e:
            logger.error(
                f"Failed to publish package via direct HTTP: {str(e)}"
            )
            return False

    def _create_publish_payload(
        self, package: Package, tarball_b64: str, tarball_data: bytes
    ) -> dict:
        """Create the npm publish payload."""
        # Sanitize package name for filesystem (replace @ and / with -)
        safe_name = package.name.replace("@", "").replace("/", "-")

        registry_url = self.target_repo_url.rstrip("/")
        if not registry_url.startswith("http"):
            registry_url = f"http://{registry_url}"

        encoded_package_name = quote(package.name, safe="")

        return {
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
                        "tarball": f"{registry_url}/{encoded_package_name}/-/{safe_name}-{package.version}.tgz",
                    },
                }
            },
            "_attachments": {
                f"{safe_name}-{package.version}.tgz": {
                    "content_type": "application/octet-stream",
                    "data": tarball_b64,
                    "length": len(tarball_data),
                }
            },
        }
