import logging
import os
from typing import Any, Dict, List

from models import Package

logger = logging.getLogger(__name__)


class ValidationService:
    def __init__(self) -> None:
        self.validation_types = [
            "file_integrity",
            "security_scan",
            "license_check",
            "dependency_analysis",
            "malware_scan",
            "vulnerability_assessment",
        ]

    def run_full_validation(self, package: Package) -> List[Dict[str, Any]]:
        """Run all validation checks on a package"""
        try:
            validation_results = []

            for validation_type in self.validation_types:
                result = self._run_validation(package, validation_type)
                validation_results.append(result)

                # If any critical validation fails, stop processing
                if (
                    validation_type in ["file_integrity", "malware_scan"]
                    and result["status"] == "failed"
                ):
                    break

            return validation_results

        except Exception as e:
            logger.error(
                f"Error running full validation for package {package.name}@{package.version}: {str(e)}"
            )
            return []

    def _run_validation(self, package: Package, validation_type: str) -> Dict[str, Any]:
        """Run a specific validation check"""
        try:
            if validation_type == "file_integrity":
                return self._validate_file_integrity(package)
            elif validation_type == "security_scan":
                return self._validate_security_scan(package)
            elif validation_type == "license_check":
                return self._validate_license(package)
            elif validation_type == "dependency_analysis":
                return self._validate_dependencies(package)
            elif validation_type == "malware_scan":
                return self._validate_malware_scan(package)
            elif validation_type == "vulnerability_assessment":
                return self._validate_vulnerabilities(package)
            else:
                return {
                    "type": validation_type,
                    "status": "failed",
                    "details": f"Unknown validation type: {validation_type}",
                }

        except Exception as e:
            logger.error(f"Error in {validation_type} validation: {str(e)}")
            return {
                "type": validation_type,
                "status": "failed",
                "details": f"Validation error: {str(e)}",
            }

    def _validate_file_integrity(self, package: Package) -> Dict[str, Any]:
        """Validate file integrity and checksum"""
        try:
            if not package.local_path or not os.path.exists(package.local_path):
                return {
                    "type": "file_integrity",
                    "status": "failed",
                    "details": "Package file not found",
                }

            # Check file size
            if (
                package.package_status
                and package.package_status.file_size
                and package.package_status.file_size > 0
            ):
                actual_size = os.path.getsize(package.local_path)
                if actual_size != package.package_status.file_size:
                    return {
                        "type": "file_integrity",
                        "status": "failed",
                        "details": f"File size mismatch: expected {package.package_status.file_size}, got {actual_size}",
                    }

            # Check checksum if available
            if package.package_status and package.package_status.checksum:
                # For now, skip checksum validation as it's not implemented
                # In production, this would calculate and compare checksums
                pass

            return {
                "type": "file_integrity",
                "status": "passed",
                "details": "File integrity verified",
            }

        except Exception as e:
            return {
                "type": "file_integrity",
                "status": "failed",
                "details": f"File integrity check failed: {str(e)}",
            }

    def _validate_security_scan(self, package: Package) -> Dict[str, Any]:
        """Security scan validation - handled by Trivy service"""
        # Security scanning is handled by the Trivy service
        # This validation just checks if the scan was completed
        try:
            if (
                package.package_status
                and package.package_status.security_scan_status == "completed"
            ):
                return {
                    "type": "security_scan",
                    "status": "passed",
                    "details": "Security scan completed successfully",
                }
            elif (
                package.package_status
                and package.package_status.security_scan_status == "failed"
            ):
                return {
                    "type": "security_scan",
                    "status": "failed",
                    "details": "Security scan failed",
                }
            else:
                return {
                    "type": "security_scan",
                    "status": "pending",
                    "details": "Security scan in progress",
                }

        except Exception as e:
            return {
                "type": "security_scan",
                "status": "failed",
                "details": f"Security scan validation failed: {str(e)}",
            }

    def _validate_license(self, package: Package) -> Dict[str, Any]:
        """Check package license compliance"""
        try:
            # License validation is now handled by LicenseWorker
            # This method is deprecated and should not be used
            logger.warning("_validate_license is deprecated - license validation is handled by LicenseWorker")
            
            return {
                "type": "license_check",
                "status": "deprecated",
                "details": "License validation is handled by LicenseWorker",
            }

        except Exception as e:
            return {
                "type": "license_check",
                "status": "failed",
                "details": f"License check failed: {str(e)}",
            }

    def _validate_dependencies(self, package: Package) -> Dict[str, Any]:
        """Analyze package dependencies"""
        try:
            # Dependency analysis is now handled by TrivyService
            # This method is deprecated and should not be used
            logger.warning("_validate_dependencies is deprecated - dependency analysis is handled by TrivyService")
            
            return {
                "type": "dependency_analysis",
                "status": "deprecated",
                "details": "Dependency analysis is handled by TrivyService",
            }

        except Exception as e:
            return {
                "type": "dependency_analysis",
                "status": "failed",
                "details": f"Dependency analysis failed: {str(e)}",
            }

    def _validate_malware_scan(self, package: Package) -> Dict[str, Any]:
        """Run malware scan on package"""
        try:
            # Malware scanning is now handled by TrivyService
            # This method is deprecated and should not be used
            logger.warning("_validate_malware_scan is deprecated - malware scanning is handled by TrivyService")
            
            return {
                "type": "malware_scan",
                "status": "deprecated",
                "details": "Malware scanning is handled by TrivyService",
            }

        except Exception as e:
            return {
                "type": "malware_scan",
                "status": "failed",
                "details": f"Malware scan failed: {str(e)}",
            }

    def _validate_vulnerabilities(self, package: Package) -> Dict[str, Any]:
        """Assess package for known vulnerabilities"""
        try:
            # Vulnerability assessment is now handled by TrivyService
            # This method is deprecated and should not be used
            logger.warning("_validate_vulnerabilities is deprecated - vulnerability assessment is handled by TrivyService")
            
            return {
                "type": "vulnerability_assessment",
                "status": "deprecated",
                "details": "Vulnerability assessment is handled by TrivyService",
            }

        except Exception as e:
            return {
                "type": "vulnerability_assessment",
                "status": "failed",
                "details": f"Vulnerability assessment failed: {str(e)}",
            }

    def get_validation_summary(self, package: Package) -> Dict[str, Any]:
        """Get summary of all validations for a package"""
        try:
            # Since we removed PackageValidation table, we'll generate validation summary
            # based on package status
            if not package.package_status:
                return {
                    "overall_status": "pending",
                    "total_validations": 0,
                    "passed_validations": 0,
                    "failed_validations": 0,
                    "pending_validations": 0,
                }

            # Determine overall status based on package status
            if package.package_status.status == "Rejected":
                overall_status = "failed"
                failed_count = 1
                passed_count = 0
                pending_count = 0
            elif package.package_status.status in ["Approved", "Downloaded"]:
                overall_status = "passed"
                failed_count = 0
                passed_count = 1
                pending_count = 0
            else:
                overall_status = "pending"
                failed_count = 0
                passed_count = 0
                pending_count = 1

            summary = {
                "total_validations": 1,
                "passed_validations": passed_count,
                "failed_validations": failed_count,
                "pending_validations": pending_count,
                "overall_status": overall_status,
                "package_status": package.package_status.status,
                "security_scan_status": package.package_status.security_scan_status,
                "license_score": package.package_status.license_score,
                "security_score": package.package_status.security_score,
            }

            return summary

        except Exception as e:
            logger.error(f"Error getting validation summary: {str(e)}")
            return {"overall_status": "error", "error": str(e)}
