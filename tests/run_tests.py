#!/usr/bin/env python3
"""Simple test runner for the secure package manager.

Run this to verify all admin API endpoints are working correctly.
"""

import os
import subprocess
import sys


def run_tests():
    """Run all tests (admin API and backend license tests)"""
    print("🚀 Starting All Tests...")
    print("=" * 50)

    # Check if tests directory exists
    if not os.path.exists("tests"):
        print("❌ Tests directory not found. Creating it...")
        os.makedirs("tests")

    all_passed = True

    # Run admin API tests
    print("\n📋 Running Admin API Tests...")
    try:
        result = subprocess.run(
            [sys.executable, "tests/test_admin_api.py"],
            capture_output=False,
            text=True,
        )
        if result.returncode != 0:
            all_passed = False
    except Exception as e:
        print(f"❌ Error running admin API tests: {e}")
        all_passed = False

    # Run backend license tests
    print("\n🔍 Running Backend License Tests...")
    try:
        result = subprocess.run(
            [sys.executable, "backend/tests/run_backend_tests.py"],
            capture_output=False,
            text=True,
        )
        if result.returncode != 0:
            all_passed = False
    except Exception as e:
        print(f"❌ Error running backend license tests: {e}")
        all_passed = False

    if all_passed:
        print("\n🎉 All tests passed!")
        return True
    else:
        print("\n❌ Some tests failed!")
        return False


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
