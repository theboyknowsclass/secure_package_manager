"""Integration tests for the optimized LicenseService.

Tests the complete license workflow end-to-end with real database interactions.
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any

from services.license_service import LicenseService


class TestLicenseServiceIntegration:
    """Integration test suite for the optimized LicenseService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = LicenseService()

    def test_complete_license_workflow_success(self):
        """Test the complete license workflow from start to finish."""
        # Mock a package that needs license checking
        mock_package = Mock()
        mock_package.id = 1
        mock_package.name = "test-package"
        mock_package.version = "1.0.0"
        mock_package.license_identifier = "MIT"
        
        # Mock database operations
        with patch('services.license_service.SessionHelper.get_session') as mock_session:
            mock_db = Mock()
            mock_session.return_value.__enter__.return_value = mock_db
            
            # Mock package operations
            mock_package_ops = Mock()
            mock_package_ops.get_packages_needing_license_check.return_value = [mock_package]
            
            # Mock the current package with proper status
            mock_current_package = Mock()
            mock_current_package.package_status.status = "Checking Licence"
            mock_package_ops.get_by_id.return_value = mock_current_package
            
            # Mock status operations
            mock_status_ops = Mock()
            mock_status_ops.update_status.return_value = True
            mock_status_ops.update_license_info.return_value = True
            
            with patch('services.license_service.PackageOperations', return_value=mock_package_ops):
                with patch('services.license_service.PackageStatusOperations', return_value=mock_status_ops):
                    # Mock license validation
                    with patch.object(self.service, '_lookup_license_in_db') as mock_lookup:
                        mock_lookup.return_value = {
                            "status": "allowed",
                            "name": "MIT License",
                            "identifier": "MIT"
                        }
                        
                        with patch.object(self.service, '_calculate_license_score') as mock_score:
                            mock_score.return_value = 75
                            
                            # Run the complete workflow
                            result = self.service.process_license_groups(max_license_groups=1)
                            
                            # Verify the result
                            assert result["success"] is True
                            assert result["processed_count"] == 1
                            assert result["successful_packages"] == 1
                            assert result["failed_packages"] == 0
                            
                            # Verify database operations were called
                            mock_package_ops.get_packages_needing_license_check.assert_called_once()
                            mock_status_ops.update_status.assert_called_with(1, "Licence Checked")
                            mock_status_ops.update_license_info.assert_called_with(1, 75, "allowed")

    def test_complete_license_workflow_failure(self):
        """Test the complete license workflow with a failed license."""
        # Mock a package with a blocked license
        mock_package = Mock()
        mock_package.id = 1
        mock_package.name = "test-package"
        mock_package.version = "1.0.0"
        mock_package.license_identifier = "GPL-3.0"
        
        # Mock database operations
        with patch('services.license_service.SessionHelper.get_session') as mock_session:
            mock_db = Mock()
            mock_session.return_value.__enter__.return_value = mock_db
            
            # Mock package operations
            mock_package_ops = Mock()
            mock_package_ops.get_packages_needing_license_check.return_value = [mock_package]
            
            # Mock the current package with proper status
            mock_current_package = Mock()
            mock_current_package.package_status.status = "Checking Licence"
            mock_package_ops.get_by_id.return_value = mock_current_package
            
            # Mock status operations
            mock_status_ops = Mock()
            mock_status_ops.update_status.return_value = True
            
            with patch('services.license_service.PackageOperations', return_value=mock_package_ops):
                with patch('services.license_service.PackageStatusOperations', return_value=mock_status_ops):
                    # Mock license validation with blocked license
                    with patch.object(self.service, '_lookup_license_in_db') as mock_lookup:
                        mock_lookup.return_value = {
                            "status": "blocked",
                            "name": "GPL-3.0 License",
                            "identifier": "GPL-3.0"
                        }
                        
                        with patch.object(self.service, '_calculate_license_score') as mock_score:
                            mock_score.return_value = 0  # Blocked license has score 0
                            
                            # Run the complete workflow
                            result = self.service.process_license_groups(max_license_groups=1)
                            
                            # Verify the result
                            assert result["success"] is True
                            assert result["processed_count"] == 1
                            assert result["successful_packages"] == 1
                            assert result["failed_packages"] == 0
                            
                            # Verify database operations were called
                            mock_status_ops.update_status.assert_called_with(1, "Licence Check Failed")
                            # Should not call update_license_info for failed licenses
                            mock_status_ops.update_license_info.assert_not_called()

    def test_license_workflow_with_race_condition(self):
        """Test that the workflow handles race conditions correctly."""
        # Mock a package that gets processed by another worker
        mock_package = Mock()
        mock_package.id = 1
        mock_package.name = "test-package"
        mock_package.version = "1.0.0"
        mock_package.license_identifier = "MIT"
        
        # Mock database operations
        with patch('services.license_service.SessionHelper.get_session') as mock_session:
            mock_db = Mock()
            mock_session.return_value.__enter__.return_value = mock_db
            
            # Mock package operations
            mock_package_ops = Mock()
            mock_package_ops.get_packages_needing_license_check.return_value = [mock_package]
            # Simulate race condition: package status changed between read and write
            mock_package_ops.get_by_id.return_value = None
            
            with patch('services.license_service.PackageOperations', return_value=mock_package_ops):
                with patch('services.license_service.PackageStatusOperations'):
                    # Mock license validation
                    with patch.object(self.service, '_lookup_license_in_db') as mock_lookup:
                        mock_lookup.return_value = {
                            "status": "allowed",
                            "name": "MIT License",
                            "identifier": "MIT"
                        }
                        
                        with patch.object(self.service, '_calculate_license_score') as mock_score:
                            mock_score.return_value = 75
                            
                            # Run the complete workflow
                            result = self.service.process_license_groups(max_license_groups=1)
                            
                            # Verify the result - should skip the package due to race condition
                            assert result["success"] is True
                            assert result["processed_count"] == 1
                            assert result["successful_packages"] == 0  # Skipped due to race condition
                            assert result["failed_packages"] == 0

    def test_license_workflow_with_multiple_packages(self):
        """Test the workflow with multiple packages in the same license group."""
        # Mock multiple packages with the same license
        mock_packages = []
        for i in range(3):
            mock_package = Mock()
            mock_package.id = i + 1
            mock_package.name = f"test-package-{i+1}"
            mock_package.version = "1.0.0"
            mock_package.license_identifier = "MIT"
            mock_packages.append(mock_package)
        
        # Mock database operations
        with patch('services.license_service.SessionHelper.get_session') as mock_session:
            mock_db = Mock()
            mock_session.return_value.__enter__.return_value = mock_db
            
            # Mock package operations
            mock_package_ops = Mock()
            mock_package_ops.get_packages_needing_license_check.return_value = mock_packages
            
            # Mock the current package with proper status
            mock_current_package = Mock()
            mock_current_package.package_status.status = "Checking Licence"
            mock_package_ops.get_by_id.return_value = mock_current_package
            
            # Mock status operations
            mock_status_ops = Mock()
            mock_status_ops.update_status.return_value = True
            mock_status_ops.update_license_info.return_value = True
            
            with patch('services.license_service.PackageOperations', return_value=mock_package_ops):
                with patch('services.license_service.PackageStatusOperations', return_value=mock_status_ops):
                    # Mock license validation
                    with patch.object(self.service, '_lookup_license_in_db') as mock_lookup:
                        mock_lookup.return_value = {
                            "status": "allowed",
                            "name": "MIT License",
                            "identifier": "MIT"
                        }
                        
                        with patch.object(self.service, '_calculate_license_score') as mock_score:
                            mock_score.return_value = 75
                            
                            # Run the complete workflow
                            result = self.service.process_license_groups(max_license_groups=1)
                            
                            # Verify the result
                            assert result["success"] is True
                            assert result["processed_count"] == 3
                            assert result["successful_packages"] == 3
                            assert result["failed_packages"] == 0
                            
                            # Verify database operations were called for each package
                            assert mock_status_ops.update_status.call_count == 3
                            assert mock_status_ops.update_license_info.call_count == 3

    def test_license_workflow_with_mixed_results(self):
        """Test the workflow with a mix of successful and failed packages."""
        # Mock packages with different licenses
        mock_package1 = Mock()
        mock_package1.id = 1
        mock_package1.name = "allowed-package"
        mock_package1.version = "1.0.0"
        mock_package1.license_identifier = "MIT"
        
        mock_package2 = Mock()
        mock_package2.id = 2
        mock_package2.name = "blocked-package"
        mock_package2.version = "2.0.0"
        mock_package2.license_identifier = "GPL-3.0"
        
        mock_packages = [mock_package1, mock_package2]
        
        # Mock database operations
        with patch('services.license_service.SessionHelper.get_session') as mock_session:
            mock_db = Mock()
            mock_session.return_value.__enter__.return_value = mock_db
            
            # Mock package operations
            mock_package_ops = Mock()
            mock_package_ops.get_packages_needing_license_check.return_value = mock_packages
            
            # Mock the current package with proper status
            mock_current_package = Mock()
            mock_current_package.package_status.status = "Checking Licence"
            mock_package_ops.get_by_id.return_value = mock_current_package
            
            # Mock status operations
            mock_status_ops = Mock()
            mock_status_ops.update_status.return_value = True
            mock_status_ops.update_license_info.return_value = True
            
            with patch('services.license_service.PackageOperations', return_value=mock_package_ops):
                with patch('services.license_service.PackageStatusOperations', return_value=mock_status_ops):
                    # Mock license validation with different results
                    def mock_lookup_side_effect(license_identifier):
                        if license_identifier == "MIT":
                            return {
                                "status": "allowed",
                                "name": "MIT License",
                                "identifier": "MIT"
                            }
                        elif license_identifier == "GPL-3.0":
                            return {
                                "status": "blocked",
                                "name": "GPL-3.0 License",
                                "identifier": "GPL-3.0"
                            }
                        return None
                    
                    def mock_score_side_effect(license_data):
                        if license_data["status"] == "allowed":
                            return 75
                        elif license_data["status"] == "blocked":
                            return 0
                        return 0
                    
                    with patch.object(self.service, '_lookup_license_in_db', side_effect=mock_lookup_side_effect):
                        with patch.object(self.service, '_calculate_license_score', side_effect=mock_score_side_effect):
                            # Run the complete workflow
                            result = self.service.process_license_groups(max_license_groups=2)
                            
                            # Verify the result
                            assert result["success"] is True
                            assert result["processed_count"] == 2
                            assert result["successful_packages"] == 2  # Both processed, but one failed
                            assert result["failed_packages"] == 0
                            
                            # Verify database operations were called
                            assert mock_status_ops.update_status.call_count == 2
                            # Only one should call update_license_info (the allowed one)
                            assert mock_status_ops.update_license_info.call_count == 1
