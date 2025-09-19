#!/usr/bin/env python3
"""Test suite for admin API endpoints.

This helps prevent regressions in the admin dashboard.
"""

import os
import sys
from typing import Optional

import requests

# Add the backend directory to the path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

BASE_URL = "http://localhost:5000"


class AdminAPITester:
    def __init__(self):
        self.token: Optional[str] = None
        self.session = requests.Session()

    def test_login(self) -> bool:
        """Test admin login and return token."""
        print("Testing admin login...")
        try:
            response = self.session.post(
                f"{BASE_URL}/api/auth/login",
                json={"username": "admin", "password": "admin"},
                headers={"Content-Type": "application/json"},
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                self.token = data.get("token")
                if self.token:
                    print(f"✅ Login successful, token: {self.token[:20]}...")
                    return True
                else:
                    print("❌ Login response missing token")
                    return False
            else:
                print(
                    f"❌ Login failed: {response.status_code} - {response.text}"
                )
                return False
        except Exception as e:
            print(f"❌ Login error: {str(e)}")
            return False

    def test_validated_packages(self) -> bool:
        """Test validated packages endpoint."""
        print("\nTesting validated packages endpoint...")
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = self.session.get(
                f"{BASE_URL}/api/admin/packages/validated",
                headers=headers,
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                packages = data.get("packages", [])
                print(
                    f"✅ Validated packages endpoint working - found {len(packages)} packages"
                )

                # Check if response has expected structure
                if packages:
                    first_pkg = packages[0]
                    required_fields = [
                        "id",
                        "name",
                        "version",
                        "security_score",
                        "license_score",
                        "license_identifier",
                    ]
                    missing_fields = [
                        field
                        for field in required_fields
                        if field not in first_pkg
                    ]
                    if missing_fields:
                        print(
                            f"⚠️  Missing fields in package data: {missing_fields}")
                        return False
                    else:
                        print("✅ Package data structure is correct")
                else:
                    print(
                        "ℹ️  No packages found (this is expected for empty database)"
                    )

                return True
            else:
                print(
                    f"❌ Validated packages endpoint failed: {response.status_code} - {response.text}"
                )
                return False
        except Exception as e:
            print(f"❌ Validated packages error: {str(e)}")
            return False

    def test_config(self) -> bool:
        """Test config endpoint."""
        print("\nTesting config endpoint...")
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = self.session.get(
                f"{BASE_URL}/api/admin/config", headers=headers, timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                config = data.get("config", {})
                status = data.get("status", {})
                print(
                    f"✅ Config endpoint working - config sections: {list(config.keys())}"
                )

                # Check if we have the expected config sections
                expected_sections = {
                    "repository",
                    "services",
                    "security",
                    "trivy",
                    "environment",
                }
                actual_sections = set(config.keys())
                if expected_sections.issubset(actual_sections):
                    print("✅ Config has expected sections")
                else:
                    print(
                        (
                            f"⚠️  Missing expected config sections. Expected: {expected_sections}, "
                            f"Found: {actual_sections}"
                        )
                    )

                # Check status information
                is_complete = status.get("is_complete", False)
                missing_keys = status.get("missing_keys", [])
                print(
                    f"✅ Config status - complete: {is_complete}, missing: {missing_keys}")

                return True
            else:
                print(
                    f"❌ Repository config endpoint failed: {response.status_code} - {response.text}"
                )
                return False
        except Exception as e:
            print(f"❌ Repository config error: {str(e)}")
            return False

    def test_licenses(self) -> bool:
        """Test licenses endpoint."""
        print("\nTesting licenses endpoint...")
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = self.session.get(
                f"{BASE_URL}/api/admin/licenses", headers=headers, timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                licenses = data.get("licenses", [])
                print(
                    f"✅ Licenses endpoint working - found {len(licenses)} licenses"
                )

                # Check if we have some expected licenses
                if licenses:
                    expected_identifiers = {"MIT", "Apache-2.0", "GPL"}
                    actual_identifiers = {
                        license.get("identifier") for license in licenses
                    }
                    if expected_identifiers.intersection(actual_identifiers):
                        print("✅ Licenses contain expected identifiers")
                    else:
                        print(
                            (
                                f"⚠️  Missing expected license identifiers. Expected: {expected_identifiers}, "
                                f"Found: {actual_identifiers}"
                            )
                        )

                return True
            else:
                print(
                    f"❌ Licenses endpoint failed: {response.status_code} - {response.text}"
                )
                return False
        except Exception as e:
            print(f"❌ Licenses error: {str(e)}")
            return False

    def run_all_tests(self) -> bool:
        """Run all tests and return success status."""
        print("🧪 Running Admin API Tests")
        print("=" * 50)

        # Test login first
        if not self.test_login():
            print("\n❌ Cannot proceed without authentication")
            return False

        # Test all endpoints
        tests = [
            self.test_validated_packages,
            self.test_config,
            self.test_licenses,
        ]

        passed = 0
        total = len(tests)

        for test in tests:
            if test():
                passed += 1

        print("\n" + "=" * 50)
        print(f"📊 Test Results: {passed}/{total} tests passed")

        if passed == total:
            print("🎉 All tests passed! Admin API is working correctly.")
            return True
        else:
            print("❌ Some tests failed. Check the output above.")
            return False


def main():
    """Main test runner."""
    tester = AdminAPITester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
