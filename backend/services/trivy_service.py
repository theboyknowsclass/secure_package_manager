import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional
from config.constants import (
    TRIVY_MAX_RETRIES,
    TRIVY_TIMEOUT,
    TRIVY_URL,
)
from database.session_helper import SessionHelper
from database.operations.security_scan_operations import SecurityScanOperations
from database.operations.package_status_operations import PackageStatusOperations
from database.models import Package, SecurityScan

logger = logging.getLogger(__name__)


class TrivyService:
    def __init__(self) -> None:
        self.trivy_url = TRIVY_URL
        self.timeout = TRIVY_TIMEOUT
        self.max_retries = TRIVY_MAX_RETRIES

    def scan_package(self, package: Package) -> Dict[str, Any]:
        """Scan a package for vulnerabilities using Trivy.

        Args:
            package: Package object to scan

        Returns:
            Dict containing scan results and status
        """
        try:
            # Extract package information before session closes
            package_id = package.id
            package_name = package.name
            package_version = package.version
            
            # Create security scan record and update status in a short session
            security_scan_id = None
            with SessionHelper.get_session() as db:
                # Create security scan record
                security_scan = SecurityScan(
                    package_id=package_id, scan_type="trivy"
                )
                security_scan_ops = SecurityScanOperations(db.session)
                security_scan_ops.create(security_scan)
                db.flush()  # Get the ID without committing
                security_scan_id = security_scan.id
                
                # Update package security scan status
                status_ops = PackageStatusOperations(db.session)
                status_ops.go_to_next_stage(package_id, security_scan_status="running")
                
                db.commit()

            logger.info(
                f"Starting Trivy scan for package {package_name}@{package_version}"
            )

            # Download package if not already downloaded
            package_path = self._download_package_for_scanning(package)
            if not package_path:
                return self._handle_scan_failure(
                    security_scan_id,
                    package_id,
                    package_name,
                    package_version,
                    "Failed to download package for scanning",
                )

            # Perform the scan
            scan_result = self._perform_trivy_scan(package_path, package_name, package_version)
            if not scan_result:
                return self._handle_scan_failure(
                    security_scan_id, package_id, package_name, package_version, "Trivy scan failed"
                )

            # Process and store results
            return self._process_scan_results(
                security_scan_id, package_id, package_name, package_version, scan_result
            )

        except Exception as e:
            logger.error(
                f"Error scanning package {package.name}@{package.version}: {str(e)}"
            )
            return self._handle_scan_failure(
                security_scan_id, package_id, package_name, package_version, f"Scan error: {str(e)}"
            )

    def _download_package_for_scanning(
        self, package: Package
    ) -> Optional[str]:
        """Get package path for scanning (package should already be downloaded
        by DownloadWorker)

        Args:
            package: Package object

        Returns:
            Path to downloaded package or None if not available
        """
        try:
            # First, try to use the stored cache_path from package_status
            if package.package_status and package.package_status.cache_path and os.path.exists(package.package_status.cache_path):
                # The cache_path points to the cache directory, we need the package subdirectory
                package_path = os.path.join(package.package_status.cache_path, "package")
                if os.path.exists(package_path):
                    logger.info(
                        f"Using stored cache_path for scanning: {package_path}"
                    )
                    return package_path
                else:
                    logger.warning(
                        f"Stored cache_path exists but package subdirectory not found: {package.package_status.cache_path}"
                    )

            # Fallback to the old method for backward compatibility
            from .package_cache_service import PackageCacheService

            cache_service = PackageCacheService()
            package_path = cache_service.get_package_path(package)

            if package_path and os.path.exists(package_path):
                logger.info(
                    f"Using fallback cache lookup for scanning: {package_path}"
                )
                return package_path
            else:
                logger.error(
                    f"Package {package.name}@{package.version} not found in cache. "
                    f"Download worker should have completed download before security scanning. "
                    f"Stored cache_path: {package.package_status.cache_path if package.package_status else 'None'}"
                )
                return None

        except Exception as e:
            logger.error(f"Error getting package path for scanning: {str(e)}")
            return None


    def _perform_trivy_scan(
        self, package_path: str, package_name: str, package_version: str
    ) -> Optional[Dict]:
        """Perform actual Trivy scan using the Trivy server.

        Args:
            package_path: Path to package directory
            package_name: Name of the package
            package_version: Version of the package

        Returns:
            Scan result dictionary or None if failed
        """
        try:
            # Check if Trivy server is available
            if not self._is_trivy_server_available():
                logger.error(
                    "Trivy server not available - cannot perform security scan"
                )
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

                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=self.timeout
                )

                # Calculate scan duration
                scan_duration_ms = int((time.time() - start_time) * 1000)

                if result.returncode == 0:
                    scan_result = json.loads(result.stdout)
                    logger.info(
                        f"Trivy scan completed successfully for {package_name}"
                    )
                    return self._format_trivy_result(
                        scan_result, package_name, package_version, scan_duration_ms
                    )
                else:
                    logger.error(
                        f"Trivy scan failed with return code {result.returncode}: {result.stderr}"
                    )
                    return None

            except subprocess.TimeoutExpired:
                logger.error(
                    f"Trivy scan timed out after {self.timeout} seconds"
                )
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

    def _format_trivy_result(
        self, trivy_response: Dict, package_name: str, package_version: str, scan_duration_ms: int
    ) -> Dict:
        """Format Trivy scan response to our expected format.

        Args:
            trivy_response: Raw response from Trivy server
            package_name: Name of the package
            package_version: Version of the package
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
            vulnerabilities, summary = self._parse_trivy_results(
                trivy_response, package_name, package_version
            )

            # Extract additional metadata from Trivy response
            metadata = trivy_response.get("Metadata", {})
            artifact_info = {
                "artifact_name": trivy_response.get(
                    "ArtifactName", package_name
                ),
                "artifact_type": trivy_response.get(
                    "ArtifactType", "filesystem"
                ),
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
                    "artifact_name": package_name,
                    "artifact_type": "filesystem",
                    "schema_version": 2,
                },
                "scan_metadata": {
                    "total_results": 0,
                    "error": str(e),
                },
            }

    def _parse_trivy_results(
        self, trivy_response: Dict, package_name: str, package_version: str
    ) -> tuple[list, dict]:
        """Parse Trivy JSON response to extract vulnerabilities and summary.

        Args:
            trivy_response: Raw JSON response from Trivy
            package_name: Name of the package being scanned
            package_version: Version of the package being scanned

        Returns:
            Tuple of (vulnerabilities_list, summary_dict)
        """
        try:
            vulnerabilities = []
            summary = {
                "total": 0,
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
                "info": 0,
            }

            # Trivy JSON structure: {"Results": [{"Target": "...", "Vulnerabilities": [...]}]}
            results = trivy_response.get("Results", [])
            
            for result in results:
                target = result.get("Target", "")
                vulns = result.get("Vulnerabilities", [])
                
                for vuln in vulns:
                    # Extract vulnerability information
                    vulnerability = {
                        "vulnerability_id": vuln.get("VulnerabilityID", ""),
                        "pkg_name": vuln.get("PkgName", ""),
                        "pkg_version": vuln.get("InstalledVersion", ""),
                        "severity": vuln.get("Severity", "").lower(),
                        "title": vuln.get("Title", ""),
                        "description": vuln.get("Description", ""),
                        "references": vuln.get("References", []),
                        "target": target,
                        "package_name": package_name,
                        "package_version": package_version,
                    }
                    
                    # Add CVSS scores if available
                    if "CVSS" in vuln:
                        cvss_data = vuln["CVSS"]
                        vulnerability["cvss_score"] = cvss_data.get("nvd", {}).get("V3Score", 0)
                        vulnerability["cvss_vector"] = cvss_data.get("nvd", {}).get("V3Vector", "")
                    
                    vulnerabilities.append(vulnerability)
                    
                    # Count by severity
                    severity = vuln.get("Severity", "").upper()
                    if severity == "CRITICAL":
                        summary["critical"] += 1
                    elif severity == "HIGH":
                        summary["high"] += 1
                    elif severity == "MEDIUM":
                        summary["medium"] += 1
                    elif severity == "LOW":
                        summary["low"] += 1
                    elif severity == "INFO":
                        summary["info"] += 1
                    
                    summary["total"] += 1

            return vulnerabilities, summary

        except Exception as e:
            logger.error(f"Error parsing Trivy results: {str(e)}")
            # Return empty results on parsing error
            return [], {
                "total": 0,
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
                "info": 0,
            }


    def _get_trivy_version(self) -> str:
        """Get Trivy version from the binary.

        Returns:
            Trivy version string or "unknown" if not available
        """
        try:
            import subprocess

            result = subprocess.run(
                ["trivy", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
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
        """Check if Trivy binary is available.

        Returns:
            True if Trivy binary is available, False otherwise
        """
        try:
            import subprocess

            result = subprocess.run(
                ["trivy", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except Exception as e:
            logger.warning(f"Trivy binary not available: {str(e)}")
            return False

    def _process_scan_results(
        self, security_scan_id: int, package_id: int, package_name: str, package_version: str, scan_result: Dict
    ) -> Dict:
        """Process and store scan results.

        Args:
            security_scan_id: ID of the security scan record
            package_id: ID of the package
            package_name: Name of the package
            package_version: Version of the package
            scan_result: Raw scan result from Trivy

        Returns:
            Processed scan result dictionary
        """
        try:
            # Extract vulnerability counts
            summary = scan_result.get("summary", {})

            # Update security scan record and package status in a new session
            with SessionHelper.get_session() as db:
                # Get the security scan record
                security_scan_ops = SecurityScanOperations(db.session)
                security_scan = security_scan_ops.get_by_id(security_scan_id)
                
                if not security_scan:
                    logger.error(f"Security scan record {security_scan_id} not found")
                    return {"status": "failed", "error": "Security scan record not found"}

                # Update security scan record
                security_scan.scan_result = scan_result
                security_scan.critical_count = summary.get("critical", 0)
                security_scan.high_count = summary.get("high", 0)
                security_scan.medium_count = summary.get("medium", 0)
                security_scan.low_count = summary.get("low", 0)
                security_scan.info_count = summary.get("info", 0)
                security_scan.scan_duration_ms = scan_result.get(
                    "scan_duration_ms", 0
                )
                security_scan.trivy_version = scan_result.get(
                    "trivy_version", "unknown"
                )
                security_scan.completed_at = datetime.utcnow()

                # Update package status with scan results
                status_ops = PackageStatusOperations(db.session)
                security_score = self._calculate_security_score_from_vulnerabilities(
                    security_scan
                )
                status_ops.update_status(package_id, "Security Scanned")
                status_ops.update_security_scan_status(package_id, "completed")
                status_ops.update_security_score(package_id, security_score)

                db.commit()

            total_vulnerabilities = security_scan.get_total_vulnerabilities()
            logger.info(
                f"Completed Trivy scan for {package_name}@{package_version}: {total_vulnerabilities} vulnerabilities found"
            )

            return {
                "status": "completed",
                "vulnerability_count": total_vulnerabilities,
                "critical_count": security_scan.critical_count,
                "high_count": security_scan.high_count,
                "medium_count": security_scan.medium_count,
                "low_count": security_scan.low_count,
                "security_score": security_score,
                "scan_duration_ms": security_scan.scan_duration_ms,
            }

        except Exception as e:
            logger.error(f"Error processing scan results: {str(e)}")
            return self._handle_scan_failure(
                security_scan_id, package_id, package_name, package_version, f"Error processing results: {str(e)}"
            )

    def _calculate_security_score_from_vulnerabilities(
        self, security_scan: SecurityScan
    ) -> int:
        """Calculate security score based on vulnerability counts.

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

    def _handle_scan_failure(
        self, security_scan_id: int, package_id: int, package_name: str, package_version: str, error_message: str
    ) -> Dict:
        """Handle scan failure.

        Args:
            security_scan_id: ID of the security scan record
            package_id: ID of the package
            package_name: Name of the package
            package_version: Version of the package
            error_message: Error message

        Returns:
            Error result dictionary
        """
        try:
            # Update security scan record and package status in a new session
            with SessionHelper.get_session() as db:
                # Get the security scan record
                security_scan_ops = SecurityScanOperations(db.session)
                security_scan = security_scan_ops.get_by_id(security_scan_id)
                
                if security_scan:
                    # Update security scan record
                    security_scan.scan_result = {"error": error_message}
                    security_scan.completed_at = datetime.utcnow()

                # Update package status
                status_ops = PackageStatusOperations(db.session)
                status_ops.update_status(package_id, "Security Scanned")  # Still mark as scanned even if failed
                status_ops.update_security_scan_status(package_id, "failed")

                db.commit()

            logger.error(
                f"Trivy scan failed for {package_name}@{package_version}: {error_message}"
            )

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
        """Get scan status for a package.

        Args:
            package_id: Package ID

        Returns:
            Scan status dictionary or None if not found
        """
        try:
            security_scan = (
                SecurityScan.query.filter_by(
                    package_id=package_id, scan_type="trivy"
                )
                .order_by(SecurityScan.created_at.desc())
                .first()
            )

            if not security_scan:
                return None

            return {
                "status": (
                    security_scan.status
                    if hasattr(security_scan, "status")
                    else "completed"
                ),
                "vulnerability_count": security_scan.vulnerability_count,
                "critical_count": security_scan.critical_count,
                "high_count": security_scan.high_count,
                "medium_count": security_scan.medium_count,
                "low_count": security_scan.low_count,
                "scan_duration_ms": security_scan.scan_duration_ms,
                "trivy_version": security_scan.trivy_version,
                "created_at": (
                    security_scan.created_at.isoformat()
                    if security_scan.created_at
                    else None
                ),
                "completed_at": (
                    security_scan.completed_at.isoformat()
                    if security_scan.completed_at
                    else None
                ),
            }

        except Exception as e:
            logger.error(
                f"Error getting scan status for package {package_id}: {str(e)}"
            )
            return None

    def get_scan_report(self, package_id: int) -> Optional[Dict]:
        """Get detailed scan report for a package.

        Args:
            package_id: Package ID

        Returns:
            Detailed scan report or None if not found
        """
        try:
            security_scan = (
                SecurityScan.query.filter_by(
                    package_id=package_id, scan_type="trivy"
                )
                .order_by(SecurityScan.created_at.desc())
                .first()
            )

            if not security_scan or not security_scan.scan_result:
                return None

            return {
                "scan_id": security_scan.id,
                "package_id": package_id,
                "status": (
                    security_scan.status
                    if hasattr(security_scan, "status")
                    else "completed"
                ),
                "scan_result": security_scan.scan_result,
                "vulnerability_count": security_scan.vulnerability_count,
                "critical_count": security_scan.critical_count,
                "high_count": security_scan.high_count,
                "medium_count": security_scan.medium_count,
                "low_count": security_scan.low_count,
                "scan_duration_ms": security_scan.scan_duration_ms,
                "trivy_version": security_scan.trivy_version,
                "created_at": (
                    security_scan.created_at.isoformat()
                    if security_scan.created_at
                    else None
                ),
                "completed_at": (
                    security_scan.completed_at.isoformat()
                    if security_scan.completed_at
                    else None
                ),
            }

        except Exception as e:
            logger.error(
                f"Error getting scan report for package {package_id}: {str(e)}"
            )
            return None

    def scan_package_data_only(self, package: Any) -> Dict[str, Any]:
        """Scan a package for security vulnerabilities using Trivy (no database operations).

        This method performs only the scanning work without creating database sessions.
        The calling service should handle database operations.

        Args:
            package: Package object to scan

        Returns:
            Dict containing scan results and status
        """
        try:
            # Extract package information
            package_id = package.id
            package_name = package.name
            package_version = package.version
            
            logger.info(
                f"Starting Trivy scan for package {package_name}@{package_version}"
            )

            # Download package if not already downloaded
            package_path = self._download_package_for_scanning(package)
            if not package_path:
                return {
                    "status": "failed",
                    "error": "Failed to download package for scanning",
                    "package_id": package_id
                }

            # Perform the scan
            scan_result = self._perform_trivy_scan(package_path, package_name, package_version)
            if not scan_result:
                return {
                    "status": "failed",
                    "error": "Trivy scan failed",
                    "package_id": package_id
                }

            # Process scan results (no database operations)
            processed_result = self._process_scan_results_data_only(scan_result, package_id)
            
            logger.info(
                f"Completed Trivy scan for package {package_name}@{package_version}"
            )
            
            return {
                "status": "success",
                "package_id": package_id,
                "scan_data": processed_result
            }

        except Exception as e:
            logger.error(f"Error scanning package {package_name}@{package_version}: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "package_id": package_id
            }

    def _process_scan_results_data_only(self, scan_result: Dict, package_id: int) -> Dict[str, Any]:
        """Process scan results without database operations."""
        try:
            # Extract vulnerability counts
            summary = scan_result.get("summary", {})

            # Calculate security score
            security_score = self._calculate_security_score_from_vulnerabilities_data_only(summary)

            return {
                "scan_result": scan_result,
                "critical_count": summary.get("critical", 0),
                "high_count": summary.get("high", 0),
                "medium_count": summary.get("medium", 0),
                "low_count": summary.get("low", 0),
                "info_count": summary.get("info", 0),
                "scan_duration_ms": scan_result.get("scan_duration_ms", 0),
                "trivy_version": scan_result.get("trivy_version", "unknown"),
                "security_score": security_score,
                "total_vulnerabilities": sum([
                    summary.get("critical", 0),
                    summary.get("high", 0),
                    summary.get("medium", 0),
                    summary.get("low", 0),
                    summary.get("info", 0)
                ])
            }

        except Exception as e:
            logger.error(f"Error processing scan results for package {package_id}: {str(e)}")
            return {
                "scan_result": scan_result,
                "critical_count": 0,
                "high_count": 0,
                "medium_count": 0,
                "low_count": 0,
                "info_count": 0,
                "scan_duration_ms": 0,
                "trivy_version": "unknown",
                "security_score": 0,
                "total_vulnerabilities": 0
            }

    def _calculate_security_score_from_vulnerabilities_data_only(self, summary: Dict) -> int:
        """Calculate security score from vulnerability summary without database operations."""
        try:
            critical = summary.get("critical", 0)
            high = summary.get("high", 0)
            medium = summary.get("medium", 0)
            low = summary.get("low", 0)
            info = summary.get("info", 0)

            # Calculate score (100 - weighted vulnerabilities)
            score = 100
            score -= critical * 20  # Critical vulnerabilities are very bad
            score -= high * 10      # High vulnerabilities are bad
            score -= medium * 5     # Medium vulnerabilities are concerning
            score -= low * 2        # Low vulnerabilities are minor
            score -= info * 1       # Info vulnerabilities are just informational

            return max(0, score)  # Don't go below 0

        except Exception as e:
            logger.error(f"Error calculating security score: {str(e)}")
            return 0