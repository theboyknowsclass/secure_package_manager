#!/usr/bin/env python3
"""
Test runner for worker module unit tests.
Runs all unit tests in the workers test package.
"""

import os
import sys
import unittest

# Add the parent directory to the path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def run_worker_tests():
    """Run all worker unit tests"""
    print("🚀 Starting Worker Unit Tests...")
    print("=" * 50)

    # Discover and run all tests in the workers test package
    loader = unittest.TestLoader()
    workers_dir = os.path.join(os.path.dirname(__file__), "workers")
    suite = loader.discover(workers_dir, pattern="test_*.py")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "=" * 50)
    if result.wasSuccessful():
        print("🎉 All worker unit tests passed!")
        return True
    else:
        print(f"❌ {len(result.failures)} test(s) failed, {len(result.errors)} error(s)")
        return False


if __name__ == "__main__":
    success = run_worker_tests()
    sys.exit(0 if success else 1)
