"""Unit tests for the optimized LicenseService.

Tests the new 3-phase pattern implementation with proper data validation.
"""

from typing import Any, Dict, List, Union
from unittest.mock import MagicMock, Mock, patch

import pytest
from services.license_service import LicenseService


class TestLicenseServiceOptimized:
    """Test suite for the optimized LicenseService."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.service = LicenseService()

    def test_validate_package_license_returns_correct_structure(self) -> None:
        """Test that validate_package_license returns the expected data structure."""
        # Mock the license cache and database lookup
        with patch.object(
            self.service, "_lookup_license_in_db"
        ) as mock_lookup:
            mock_lookup.return_value = {
                "status": "allowed",
                "name": "MIT License",
                "identifier": "MIT",
            }

            with patch.object(
                self.service, "_calculate_license_score"
            ) as mock_score:
                mock_score.return_value = 75

                result = self.service.validate_package_license(
                    {"license": "MIT"}
                )

                # Validate structure
                assert isinstance(result, dict)
                assert "valid" in result
                assert "score" in result
                assert "license_status" in result
                assert "license_identifier" in result
                assert "license_name" in result
                assert "errors" in result

                # Validate types
                assert isinstance(result["valid"], bool)
                assert isinstance(result["score"], int)
                assert isinstance(result["license_status"], str)
                assert isinstance(result["license_identifier"], str)
                assert isinstance(result["license_name"], str)
                assert isinstance(result["errors"], list)

                # Validate values
                assert result["valid"] is True
                assert result["score"] == 75
                assert result["license_status"] == "allowed"
                assert result["license_identifier"] == "MIT"
                assert result["license_name"] == "MIT License"
                assert result["errors"] == []

    def test_validate_package_license_handles_missing_license(self) -> None:
        """Test that validate_package_license handles missing license correctly."""
        with patch.object(
            self.service, "_create_no_license_result"
        ) as mock_no_license:
            mock_no_license.return_value = {
                "valid": True,
                "score": 50,
                "license_identifier": "No License",
                "license_status": "unknown",
                "license_name": "No License",
                "errors": [],
            }

            result = self.service.validate_package_license(
                {"name": "test-package"}
            )

            assert result["valid"] is True
            assert result["score"] == 50
            assert result["license_status"] == "unknown"
            assert result["license_identifier"] == "No License"

    def test_validate_package_license_handles_unknown_license(self) -> None:
        """Test that validate_package_license handles unknown license correctly."""
        with patch.object(
            self.service, "_lookup_license_in_db"
        ) as mock_lookup:
            mock_lookup.return_value = None

            with patch.object(
                self.service, "_create_unknown_license_result"
            ) as mock_unknown:
                mock_unknown.return_value = {
                    "valid": False,
                    "score": 0,
                    "license_identifier": "Unknown-License",
                    "license_status": "unknown",
                    "license_name": "Unknown License",
                    "errors": ["Unknown license: Unknown-License"],
                }

                result = self.service.validate_package_license(
                    {"license": "Unknown-License"}
                )

                assert result["valid"] is False
                assert result["score"] == 0
                errors = result["errors"]
                if isinstance(errors, list) and errors:
                    assert "Unknown license" in errors[0]
                else:
                    assert "Unknown license" in str(errors)

    def test_process_license_group_work_returns_correct_structure(
        self,
    ) -> None:
        """Test that _process_license_group_work returns the expected data structure."""
        # Mock packages
        mock_package1 = Mock()
        mock_package1.id = 1
        mock_package1.name = "test-package-1"
        mock_package1.version = "1.0.0"

        mock_package2 = Mock()
        mock_package2.id = 2
        mock_package2.name = "test-package-2"
        mock_package2.version = "2.0.0"

        packages = [mock_package1, mock_package2]

        # Mock license validation
        with patch.object(
            self.service, "validate_package_license"
        ) as mock_validate:
            mock_validate.return_value = {
                "valid": True,
                "score": 75,
                "license_status": "allowed",
                "license_identifier": "MIT",
                "license_name": "MIT License",
                "errors": [],
            }

            results = self.service._process_license_group_work("MIT", packages)

            # Validate structure
            assert isinstance(results, list)
            assert len(results) == 2

            for package, result in results:
                assert isinstance(result, dict)
                assert "status" in result
                assert "license_status" in result
                assert "score" in result

                # Validate types
                assert isinstance(result["status"], str)
                assert isinstance(result["license_status"], str)
                assert isinstance(result["score"], int)

                # Validate values
                assert result["status"] == "success"
                assert result["license_status"] == "allowed"
                assert result["score"] == 75

    def test_process_license_group_work_handles_validation_failure(
        self,
    ) -> None:
        """Test that _process_license_group_work handles validation failure correctly."""
        mock_package = Mock()
        mock_package.id = 1
        mock_package.name = "test-package"
        mock_package.version = "1.0.0"

        packages = [mock_package]

        # Mock license validation failure
        with patch.object(
            self.service, "validate_package_license"
        ) as mock_validate:
            mock_validate.return_value = {
                "valid": False,
                "score": 0,
                "license_status": "unknown",
                "license_identifier": "Unknown-License",
                "license_name": "Unknown License",
                "errors": ["Unknown license: Unknown-License"],
            }

            results = self.service._process_license_group_work(
                "Unknown-License", packages
            )

            assert len(results) == 1
            package, result = results[0]

            assert result["status"] == "failed"
            assert "error" in result
            assert isinstance(result["error"], str)

    def test_update_license_results_data_validation(self) -> None:
        """Test that _update_license_results validates data correctly."""
        # Test with invalid package object
        invalid_package = Mock()
        del invalid_package.id  # Remove required attribute

        # Test with invalid result object
        invalid_result: Dict[str, Union[str, int]] = {"invalid": "data", "score": 0}  # Missing "status" field but has score

        license_results = [(invalid_package, invalid_result)]

        with patch(
            "services.license_service.SessionHelper.get_session"
        ) as mock_session:
            mock_db = Mock()
            mock_session.return_value.__enter__.return_value = mock_db

            mock_package_ops = Mock()
            mock_status_ops = Mock()

            with patch(
                "services.license_service.PackageOperations",
                return_value=mock_package_ops,
            ):
                with patch(
                    "services.license_service.PackageStatusOperations",
                    return_value=mock_status_ops,
                ):
                    result = self.service._update_license_results(
                        license_results
                    )

                    # Should handle invalid data gracefully
                    assert result["success"] is True
                    assert result["failed_packages"] == 1
                    assert result["successful_packages"] == 0

    def test_update_license_results_score_validation(self) -> None:
        """Test that _update_license_results validates score types correctly."""
        mock_package = Mock()
        mock_package.id = 1
        mock_package.name = "test-package"
        mock_package.version = "1.0.0"

        # Test with invalid score type
        invalid_score_result: Dict[str, Union[str, int]] = {
            "status": "success",
            "score": "invalid_score",  # String instead of int
            "license_status": "allowed",
        }

        license_results = [(mock_package, invalid_score_result)]

        with patch(
            "services.license_service.SessionHelper.get_session"
        ) as mock_session:
            mock_db = Mock()
            mock_session.return_value.__enter__.return_value = mock_db

            mock_package_ops = Mock()
            mock_status_ops = Mock()

            # Mock package lookup
            mock_current_package = Mock()
            mock_current_package.package_status.status = "Checking Licence"
            mock_package_ops.get_by_id.return_value = mock_current_package

            with patch(
                "services.license_service.PackageOperations",
                return_value=mock_package_ops,
            ):
                with patch(
                    "services.license_service.PackageStatusOperations",
                    return_value=mock_status_ops,
                ):
                    result = self.service._update_license_results(
                        license_results
                    )

                    # Should handle invalid score gracefully
                    assert result["success"] is True
                    # Should still process the package (with score=0)
                    assert result["successful_packages"] == 1

    def test_process_license_groups_integration(self) -> None:
        """Test the complete process_license_groups workflow."""
        # Mock packages
        mock_package = Mock()
        mock_package.id = 1
        mock_package.name = "test-package"
        mock_package.version = "1.0.0"
        mock_package.license_identifier = "MIT"

        with patch.object(
            self.service, "_get_packages_for_license_check"
        ) as mock_get_packages:
            mock_get_packages.return_value = [mock_package]

            with patch.object(
                self.service, "_perform_license_validation_batch"
            ) as mock_validate_batch:
                mock_validate_batch.return_value = [
                    (
                        mock_package,
                        {
                            "status": "success",
                            "score": 75,
                            "license_status": "allowed",
                        },
                    )
                ]

                with patch.object(
                    self.service, "_update_license_results"
                ) as mock_update:
                    mock_update.return_value = {
                        "success": True,
                        "processed_count": 1,
                        "successful_packages": 1,
                        "failed_packages": 0,
                        "license_groups_processed": 1,
                    }

                    result = self.service.process_license_groups(
                        max_license_groups=1
                    )

                    # Validate result structure
                    assert isinstance(result, dict)
                    assert "success" in result
                    assert "processed_count" in result
                    assert "successful_packages" in result
                    assert "failed_packages" in result
                    assert "license_groups_processed" in result

                    # Validate values
                    assert result["success"] is True
                    assert result["processed_count"] == 1
                    assert result["successful_packages"] == 1
                    assert result["failed_packages"] == 0
                    assert result["license_groups_processed"] == 1

    def test_process_license_groups_no_packages(self) -> None:
        """Test process_license_groups when no packages need processing."""
        with patch.object(
            self.service, "_get_packages_for_license_check"
        ) as mock_get_packages:
            mock_get_packages.return_value = []

            result = self.service.process_license_groups(max_license_groups=1)

            assert result["success"] is True
            assert result["processed_count"] == 0
            assert result["successful_packages"] == 0
            assert result["failed_packages"] == 0
            assert result["license_groups_processed"] == 0

    def test_process_license_groups_exception_handling(self) -> None:
        """Test that process_license_groups handles exceptions gracefully."""
        with patch.object(
            self.service, "_get_packages_for_license_check"
        ) as mock_get_packages:
            mock_get_packages.side_effect = Exception("Database error")

            result = self.service.process_license_groups(max_license_groups=1)

            assert result["success"] is False
            assert "error" in result
            assert result["error"] == "Database error"
            assert result["processed_count"] == 0
            assert result["successful_packages"] == 0
            assert result["failed_packages"] == 0
            assert result["license_groups_processed"] == 0
