#!/usr/bin/env python3
"""
Test runner for backend license service tests.
Run this to verify license validation functionality.
"""

import os
import subprocess
import sys
import unittest


def run_license_tests():
    """Run the license service tests"""
    print("🚀 Starting License Service Tests...")
    print("=" * 50)

    # Get the directory containing this script
    test_dir = os.path.dirname(os.path.abspath(__file__))

    # Discover and run tests
    loader = unittest.TestLoader()
    start_dir = test_dir
    suite = loader.discover(start_dir, pattern="test_*.py")

    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "=" * 50)
    if result.wasSuccessful():
        print("🎉 All license tests passed!")
        return True
    else:
        print(
            f"❌ {len(result.failures)} test(s) failed, {len(result.errors)} error(s)"
        )
        return False


def run_specific_test(test_file):
    """Run a specific test file"""
    print(f"🚀 Running {test_file}...")
    print("=" * 50)

    # Get the directory containing this script
    test_dir = os.path.dirname(os.path.abspath(__file__))
    test_path = os.path.join(test_dir, test_file)

    if not os.path.exists(test_path):
        print(f"❌ Test file not found: {test_path}")
        return False

    # Run the specific test
    result = subprocess.run(
        [sys.executable, test_path], capture_output=False, text=True
    )

    if result.returncode == 0:
        print(f"\n🎉 {test_file} passed!")
        return True
    else:
        print(f"\n❌ {test_file} failed!")
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run specific test file
        test_file = sys.argv[1]
        success = run_specific_test(test_file)
    else:
        # Run all tests
        success = run_license_tests()

    sys.exit(0 if success else 1)
