#!/usr/bin/env python3
"""
Simple test runner for the secure package manager.
Run this to verify all admin API endpoints are working correctly.
"""

import os
import subprocess
import sys


def run_tests():
    """Run the admin API tests"""
    print("🚀 Starting Admin API Tests...")
    print("=" * 50)

    # Check if tests directory exists
    if not os.path.exists("tests"):
        print("❌ Tests directory not found. Creating it...")
        os.makedirs("tests")

    # Run the test
    try:
        result = subprocess.run(
            [sys.executable, "tests/test_admin_api.py"], capture_output=False, text=True
        )

        if result.returncode == 0:
            print("\n🎉 All tests passed!")
            return True
        else:
            print("\n❌ Some tests failed!")
            return False
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
