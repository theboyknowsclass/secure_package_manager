#!/usr/bin/env python3
"""Test runner for worker module unit tests.

Runs all unit tests in the workers test package.
"""

import logging
import os
import sys
import unittest

logger = logging.getLogger(__name__)

# Add the parent directory to the path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def run_worker_tests():
    """Run all worker unit tests."""
    logger.info("🚀 Starting Worker Unit Tests...")
    logger.info("=" * 50)

    # Discover and run all tests in the workers test package
    loader = unittest.TestLoader()
    workers_dir = os.path.join(os.path.dirname(__file__), "workers")
    suite = loader.discover(workers_dir, pattern="test_*.py")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    logger.info("\n" + "=" * 50)
    if result.wasSuccessful():
        logger.info("🎉 All worker unit tests passed!")
        return True
    else:
        logger.error(
            f"❌ {len(result.failures)} test(s) failed, {len(result.errors)} error(s)"
        )
        return False


if __name__ == "__main__":
    success = run_worker_tests()
    sys.exit(0 if success else 1)
