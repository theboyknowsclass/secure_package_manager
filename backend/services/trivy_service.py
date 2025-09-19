import logging
import os
import tempfile
from datetime import datetime
from typing import Any, Dict, Optional

import requests
from config.constants import (
    TRIVY_MAX_RETRIES,
    TRIVY_TIMEOUT,
    TRIVY_URL,
)
from database.flask_utils import get_db_operations
from database.models import Package, SecurityScan

logger = logging.getLogger(__name__)


class TrivyService:
    def __init__(self) -> None:
        self.trivy_url = TRIVY_URL
        self.timeout = TRIVY_TIMEOUT
        self.max_retries = TRIVY_MAX_RETRIES

    def scan_package(self, package: Package) -> Dict[str, Any]:
        """
        Scan a package for vulnerabilities using Trivy

        Args:
            package: Package object to scan

        Returns:
            Dict containing scan results and status
        """
        try:
            with get_db_operations() as ops:
                # Create security scan record
                security_scan = SecurityScan(package_id=package.id, scan_type="trivy")
                ops.add(security_scan)
                ops.commit()

                # Update package security scan status
                if package.package_status:
                    package.package_status.status = "Security Scanning"
                    package.package_status.security_scan_status = "running"
                    package.package_status.updated_at = datetime.utcnow()
                    ops.commit()

            logger.info(f"Starting Trivy scan for package {package.name}@{package.version}")

            # Download package if not already downloaded
            package_path = self._download_package_for_scanning(package)
            if not package_path:
                return self._handle_scan_failure(security_scan, package, "Failed to download package for scanning")

            # Perform the scan
            scan_result = self._perform_trivy_scan(package_path, package)
            if not scan_result:
                return self._handle_scan_failure(security_scan, package, "Trivy scan failed")

            # Process and store results
            return self._process_scan_results(security_scan, package, scan_result)

        except Exception as e:
            logger.error(f"Error scanning package {package.name}@{package.version}: {str(e)}")
            return self._handle_scan_failure(security_scan, package, f"Scan error: {str(e)}")

    def _download_package_for_scanning(self, package: Package) -> Optional[str]:
        """
        Get package path for scanning (package should already be downloaded by PackageWorker)

        Args:
            package: Package object

        Returns:
            Path to downloaded package or None if not available
        """
        try:
            # Import here to avoid circular imports
            from .download_service import DownloadService

            download_service = DownloadService()
            package_path = download_service.get_package_path(package)

            if package_path and os.path.exists(package_path):
                logger.info(f"Using cached package for scanning: {package_path}")
                return package_path
            else:
                logger.warning(f"Package {package.name}@{package.version} not found in cache, downloading for scan")
                # Fallback: download to temp directory for scanning
                return self._download_to_temp_for_scanning(package)

        except Exception as e:
            logger.error(f"Error getting package path for scanning: {str(e)}")
            return None

    def _download_to_temp_for_scanning(self, package: Package) -> Optional[str]:
        """
        Download package to temporary directory for scanning (fallback method)

        Args:
            package: Package object

        Returns:
            Path to temporary package directory or None if failed
        """
        try:
            # Create temporary directory for package
            safe_package_name = package.name.replace("/", "-").replace("@", "")
            temp_dir = tempfile.mkdtemp(prefix=f"trivy_scan_{safe_package_name}_{package.version}_")

            if not package.npm_url:
                logger.error(f"No npm_url available for package {package.name}@{package.version}")
                return None

            logger.info(f"Downloading package tarball for scanning: {package.npm_url}")
            response = requests.get(package.npm_url, timeout=60)

            if response.status_code != 200:
                logger.error(f"Failed to download tarball: HTTP {response.status_code}")
                return None

            # Extract tarball to temp directory
            import io
            import tarfile

            tarball_buffer = io.BytesIO(response.content)
            with tarfile.open(fileobj=tarball_buffer, mode="r:gz") as tar:
                tar.extractall(temp_dir)

            # Return path to the extracted package directory
            package_path = os.path.join(temp_dir, "package")
            logger.info(f"Downloaded package for scanning to: {package_path}")
            return package_path

        except Exception as e:
            logger.error(f"Error downloading package for scanning: {str(e)}")
            return None

    def _perform_trivy_scan(self, package_path: str, package: Package) -> Optional[Dict]:
        """
        Perform actual Trivy scan using the Trivy server

        Args:
            package_path: Path to package directory
            package: Package object

        Returns:
            Scan result dictionary or None if failed
        """
        try:
            # Check if Trivy server is available
            if not self._is_trivy_server_available():
                logger.error("Trivy server not available - cannot perform security scan")
                return None

            logger.info(f"Performing Trivy scan on {package_path}")

            # Use Trivy filesystem scanning via subprocess
            # This is the most reliable way to scan local files
            try:
                import json
                import subprocess
                import time

                # Run Trivy filesystem scan
                cmd = [
                    "trivy",
                    "fs",
                    "--format",
                    "json",
                    "--severity",
                    "CRITICAL,HIGH,MEDIUM,LOW",
                    "--timeout",
                    str(self.timeout) + "s",
                    package_path,
                ]

                logger.info(f"Running Trivy command: {' '.join(cmd)}")

                # Record start time for duration calculation
                start_time = time.time()

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout)

                # Calculate scan duration
                scan_duration_ms = int((time.time() - start_time) * 1000)

                if result.returncode == 0:
                    scan_result = json.loads(result.stdout)
                    logger.info(f"Trivy scan completed successfully for {package.name}")
                    return self._format_trivy_result(scan_result, package, scan_duration_ms)
                else:
                    logger.error(f"Trivy scan failed with return code {result.returncode}: {result.stderr}")
                    return None

            except subprocess.TimeoutExpired:
                logger.error(f"Trivy scan timed out after {self.timeout} seconds")
                return None
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Trivy output as JSON: {str(e)}")
                return None
            except Exception as e:
                logger.error(f"Error running Trivy subprocess: {str(e)}")
                return None

        except Exception as e:
            logger.error(f"Error performing Trivy scan: {str(e)}")
            return None

    def _format_trivy_result(self, trivy_response: Dict, package: Package, scan_duration_ms: int) -> Dict:
        """
        Format Trivy scan response to our expected format

        Args:
            trivy_response: Raw response from Trivy server
            package: Package object
            scan_duration_ms: Scan duration in milliseconds

        Returns:
            Formatted scan result dictionary
        """
        try:
            # Get Trivy version from the binary
            trivy_version = self._get_trivy_version()

            # Extract vulnerabilities from Trivy response
            vulnerabilities = []
            summary = {
                "total": 0,
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
                "info": 0,
            }

            # Parse the real Trivy response structure
            # Trivy response has a "Results" array, each with "Vulnerabilities" array
            if "Results" in trivy_response:
                logger.info(f"Processing {len(trivy_response.get('Results', []))} results from Trivy scan")

                for result in trivy_response.get("Results", []):
                    result_vulnerabilities = result.get("Vulnerabilities", [])
                    logger.info(
                        f"Found {len(result_vulnerabilities)} vulnerabilities in result: {result.get('Target', 'Unknown target')}"
                    )

                    for vuln in result_vulnerabilities:
                        severity = vuln.get("Severity", "UNKNOWN").upper()
                        vulnerability = {
                            "vulnerability_id": vuln.get("VulnerabilityID", "UNKNOWN"),
                            "severity": severity,
                            "title": vuln.get("Title", "Unknown vulnerability"),
                            "description": vuln.get("Description", "No description available"),
                            "package_name": vuln.get("PkgName", package.name),
                            "installed_version": vuln.get("InstalledVersion", package.version),
                            "fixed_version": vuln.get("FixedVersion"),
                            "references": vuln.get("References", []),
                            "cvss_score": (
                                vuln.get("CVSS", {}).get("nvd", {}).get("V3Score") if vuln.get("CVSS") else None
                            ),
                            "published_date": vuln.get("PublishedDate"),
                            "last_modified_date": vuln.get("LastModifiedDate"),
                        }
                        vulnerabilities.append(vulnerability)

                        # Update summary counts
                        summary["total"] += 1
                        if severity in summary:
                            summary[severity.lower()] += 1
                        else:
                            summary["info"] += 1

                        logger.debug(f"Added vulnerability: {vulnerability['vulnerability_id']} ({severity})")

            else:
                logger.info(
                    "No 'Results' found in Trivy response - this is normal for packages with no vulnerabilities"
                )

            # Extract additional metadata from Trivy response
            metadata = trivy_response.get("Metadata", {})
            artifact_info = {
                "artifact_name": trivy_response.get("ArtifactName", package.name),
                "artifact_type": trivy_response.get("ArtifactType", "filesystem"),
                "schema_version": trivy_response.get("SchemaVersion", 2),
                "created_at": trivy_response.get("CreatedAt"),
            }

            # Add OS information if available
            if "OS" in metadata:
                artifact_info["os"] = {
                    "family": metadata["OS"].get("Family"),
                    "name": metadata["OS"].get("Name"),
                    "eosl": metadata["OS"].get("EOSL", False),
                }

            return {
                "trivy_version": trivy_version,
                "scan_duration_ms": scan_duration_ms,
                "vulnerabilities": vulnerabilities,
                "summary": summary,
                "artifact_info": artifact_info,
                "scan_metadata": {
                    "total_results": len(trivy_response.get("Results", [])),
                    "scan_completed_at": trivy_response.get("CreatedAt"),
                },
            }

        except Exception as e:
            logger.error(f"Error formatting Trivy result: {str(e)}")
            # Return empty result on formatting error
            return {
                "trivy_version": "unknown",
                "scan_duration_ms": scan_duration_ms,
                "vulnerabilities": [],
                "summary": {
                    "total": 0,
                    "critical": 0,
                    "high": 0,
                    "medium": 0,
                    "low": 0,
                    "info": 0,
                },
                "artifact_info": {
                    "artifact_name": package.name,
                    "artifact_type": "filesystem",
                    "schema_version": 2,
                },
                "scan_metadata": {
                    "total_results": 0,
                    "error": str(e),
                },
            }

    def _get_trivy_version(self) -> str:
        """
        Get Trivy version from the binary

        Returns:
            Trivy version string or "unknown" if not available
        """
        try:
            import subprocess

            result = subprocess.run(["trivy", "--version"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                # Extract version from output like "Version: 0.66.0"
                version_line = result.stdout.strip()
                if "Version:" in version_line:
                    return version_line.split("Version:")[1].strip()
                return version_line
            return "unknown"
        except Exception as e:
            logger.warning(f"Could not get Trivy version: {str(e)}")
            return "unknown"

    def _is_trivy_server_available(self) -> bool:
        """
        Check if Trivy binary is available

        Returns:
            True if Trivy binary is available, False otherwise
        """
        try:
            import subprocess

            result = subprocess.run(["trivy", "--version"], capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except Exception as e:
            logger.warning(f"Trivy binary not available: {str(e)}")
            return False

    def _process_scan_results(self, security_scan: SecurityScan, package: Package, scan_result: Dict) -> Dict:
        """
        Process and store scan results

        Args:
            security_scan: SecurityScan object
            package: Package object
            scan_result: Raw scan result from Trivy

        Returns:
            Processed scan result dictionary
        """
        try:
            # Extract vulnerability counts
            summary = scan_result.get("summary", {})

            # Update security scan record
            security_scan.scan_result = scan_result
            security_scan.critical_count = summary.get("critical", 0)
            security_scan.high_count = summary.get("high", 0)
            security_scan.medium_count = summary.get("medium", 0)
            security_scan.low_count = summary.get("low", 0)
            security_scan.info_count = summary.get("info", 0)
            security_scan.scan_duration_ms = scan_result.get("scan_duration_ms", 0)
            security_scan.trivy_version = scan_result.get("trivy_version", "unknown")
            security_scan.completed_at = datetime.utcnow()

            # Update package status with scan results
            if package.package_status:
                package.package_status.status = "Security Scanned"
                package.package_status.security_scan_status = "completed"
                package.package_status.security_score = self._calculate_security_score_from_vulnerabilities(
                    security_scan
                )
                package.package_status.updated_at = datetime.utcnow()

            with get_db_operations() as ops:
                ops.commit()

            total_vulnerabilities = security_scan.get_total_vulnerabilities()
            logger.info(
                f"Completed Trivy scan for {package.name}@{package.version}: {total_vulnerabilities} vulnerabilities found"
            )

            return {
                "status": "completed",
                "vulnerability_count": total_vulnerabilities,
                "critical_count": security_scan.critical_count,
                "high_count": security_scan.high_count,
                "medium_count": security_scan.medium_count,
                "low_count": security_scan.low_count,
                "security_score": (package.package_status.security_score if package.package_status else 100),
                "scan_duration_ms": security_scan.scan_duration_ms,
            }

        except Exception as e:
            logger.error(f"Error processing scan results: {str(e)}")
            return self._handle_scan_failure(security_scan, package, f"Error processing results: {str(e)}")

    def _calculate_security_score_from_vulnerabilities(self, security_scan: SecurityScan) -> int:
        """
        Calculate security score based on vulnerability counts

        Business Rules:
        - Any critical vulnerability = 0 (blocks approval)
        - High/medium/low vulnerabilities reduce score proportionally

        Args:
            security_scan: SecurityScan object

        Returns:
            Security score (0-100)
        """
        try:
            # Any critical vulnerability blocks approval (score = 0)
            if security_scan.critical_count > 0:
                return 0

            # Base score starts at 100 for non-critical vulnerabilities
            score = 100

            # Deduct points for non-critical vulnerabilities
            score -= security_scan.high_count * 15  # -15 per high
            score -= security_scan.medium_count * 8  # -8 per medium
            score -= security_scan.low_count * 3  # -3 per low
            # info_count is ignored (informational only)

            # Ensure score is between 0 and 100
            return int(max(0, min(100, score)))

        except Exception as e:
            logger.error(f"Error calculating security score: {str(e)}")
            return 50  # Default score on error

    def _handle_scan_failure(self, security_scan: SecurityScan, package: Package, error_message: str) -> Dict:
        """
        Handle scan failure

        Args:
            security_scan: SecurityScan object
            package: Package object
            error_message: Error message

        Returns:
            Error result dictionary
        """
        try:
            # Update security scan record
            security_scan.scan_result = {"error": error_message}
            security_scan.completed_at = datetime.utcnow()

            # Update package status
            if package.package_status:
                package.package_status.status = "Security Scanned"  # Still mark as scanned even if failed
                package.package_status.security_scan_status = "failed"
                package.package_status.updated_at = datetime.utcnow()

            with get_db_operations() as ops:
                ops.commit()

            logger.error(f"Trivy scan failed for {package.name}@{package.version}: {error_message}")

            return {
                "status": "failed",
                "error": error_message,
                "vulnerability_count": 0,
                "security_score": 0,
            }

        except Exception as e:
            logger.error(f"Error handling scan failure: {str(e)}")
            return {
                "status": "failed",
                "error": f"Failed to handle scan failure: {str(e)}",
                "vulnerability_count": 0,
                "security_score": 0,
            }

    def get_scan_status(self, package_id: int) -> Optional[Dict]:
        """
        Get scan status for a package

        Args:
            package_id: Package ID

        Returns:
            Scan status dictionary or None if not found
        """
        try:
            security_scan = (
                SecurityScan.query.filter_by(package_id=package_id, scan_type="trivy")
                .order_by(SecurityScan.created_at.desc())
                .first()
            )

            if not security_scan:
                return None

            return {
                "status": (security_scan.status if hasattr(security_scan, "status") else "completed"),
                "vulnerability_count": security_scan.vulnerability_count,
                "critical_count": security_scan.critical_count,
                "high_count": security_scan.high_count,
                "medium_count": security_scan.medium_count,
                "low_count": security_scan.low_count,
                "scan_duration_ms": security_scan.scan_duration_ms,
                "trivy_version": security_scan.trivy_version,
                "created_at": (security_scan.created_at.isoformat() if security_scan.created_at else None),
                "completed_at": (security_scan.completed_at.isoformat() if security_scan.completed_at else None),
            }

        except Exception as e:
            logger.error(f"Error getting scan status for package {package_id}: {str(e)}")
            return None

    def get_scan_report(self, package_id: int) -> Optional[Dict]:
        """
        Get detailed scan report for a package

        Args:
            package_id: Package ID

        Returns:
            Detailed scan report or None if not found
        """
        try:
            security_scan = (
                SecurityScan.query.filter_by(package_id=package_id, scan_type="trivy")
                .order_by(SecurityScan.created_at.desc())
                .first()
            )

            if not security_scan or not security_scan.scan_result:
                return None

            return {
                "scan_id": security_scan.id,
                "package_id": package_id,
                "status": (security_scan.status if hasattr(security_scan, "status") else "completed"),
                "scan_result": security_scan.scan_result,
                "vulnerability_count": security_scan.vulnerability_count,
                "critical_count": security_scan.critical_count,
                "high_count": security_scan.high_count,
                "medium_count": security_scan.medium_count,
                "low_count": security_scan.low_count,
                "scan_duration_ms": security_scan.scan_duration_ms,
                "trivy_version": security_scan.trivy_version,
                "created_at": (security_scan.created_at.isoformat() if security_scan.created_at else None),
                "completed_at": (security_scan.completed_at.isoformat() if security_scan.completed_at else None),
            }

        except Exception as e:
            logger.error(f"Error getting scan report for package {package_id}: {str(e)}")
            return None
