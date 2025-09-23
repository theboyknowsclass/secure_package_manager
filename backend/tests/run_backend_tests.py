#!/usr/bin/env python3
"""Test runner for backend tests.

Run this to verify all backend functionality including services,
workers, and integrations.
"""

import logging
import subprocess
import sys
import unittest
from pathlib import Path

logger = logging.getLogger(__name__)


def run_backend_tests() -> bool:
    """Run all backend tests."""
    logger.info("🚀 Starting Backend Tests...")
    logger.info("=" * 50)

    # Get the directory containing this script
    test_dir = Path(__file__).parent

    # Discover and run tests
    loader = unittest.TestLoader()
    start_dir = test_dir
    suite = loader.discover(str(start_dir), pattern="test_*.py")

    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    logger.info("\n" + "=" * 50)
    if result.wasSuccessful():
        logger.info("🎉 All backend tests passed!")
        return True
    else:
        logger.error(
            f"❌ {len(result.failures)} test(s) failed, {len(result.errors)} error(s)"
        )
        return False


def run_specific_test(test_file: str) -> bool:
    """Run a specific test file."""
    logger.info(f"🚀 Running {test_file}...")
    logger.info("=" * 50)

    # Get the directory containing this script
    test_dir = Path(__file__).parent
    test_path = test_dir / test_file

    if not test_path.exists():
        logger.error(f"❌ Test file not found: {test_path}")
        return False

    # Run the specific test
    result = subprocess.run(
        [sys.executable, str(test_path)], capture_output=False, text=True
    )

    if result.returncode == 0:
        logger.info(f"\n🎉 {test_file} passed!")
        return True
    else:
        logger.error(f"\n❌ {test_file} failed!")
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run specific test file
        test_file = sys.argv[1]
        success = run_specific_test(test_file)
    else:
        # Run all tests
        success = run_backend_tests()

    sys.exit(0 if success else 1)
