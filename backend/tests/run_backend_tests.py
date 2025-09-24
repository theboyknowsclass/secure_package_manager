#!/usr/bin/env python3
"""Test runner for backend service tests.

Run this to verify all backend service functionality.
"""

import logging
import os
import subprocess
import sys
import unittest
from pathlib import Path

logger = logging.getLogger(__name__)

# Add the parent directory to the path so we can import modules
sys.path.insert(0, str(Path(__file__).parent.parent))


def setup_test_environment() -> None:
    """Set up environment variables for testing."""
    # Set default database URL for testing if not already set
    if not os.getenv("DATABASE_URL"):
        test_db_path = Path(__file__).parent.parent / "instance" / "test.db"
        os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path.absolute()}"
        logger.info(f"Set DATABASE_URL to: {os.environ['DATABASE_URL']}")
    
    # Set other required environment variables for testing
    os.environ.setdefault("FLASK_ENV", "testing")
    os.environ.setdefault("FLASK_DEBUG", "1")


def run_backend_tests() -> bool:
    """Run all backend service tests."""
    # Use the services-only approach since it works reliably
    return run_service_tests_only()


def run_specific_test(test_file: str) -> bool:
    """Run a specific test file."""
    logger.info(f"🚀 Running {test_file}...")
    logger.info("=" * 50)
    
    # Set up test environment
    setup_test_environment()

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


def run_service_tests_only() -> bool:
    """Run only the service tests."""
    logger.info("🚀 Starting Service Tests Only...")
    logger.info("=" * 50)
    
    # Set up test environment
    setup_test_environment()

    # Get the directory containing this script
    test_dir = Path(__file__).parent
    services_dir = test_dir / "services"

    if not services_dir.exists():
        logger.error("❌ Services test directory not found!")
        return False

    # Discover and run service tests
    loader = unittest.TestLoader()
    suite = loader.discover(str(services_dir), pattern="test_*.py")

    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    logger.info("\n" + "=" * 50)
    if result.wasSuccessful():
        logger.info("🎉 All service tests passed!")
        return True
    else:
        logger.error(
            f"❌ {len(result.failures)} test(s) failed, {len(result.errors)} error(s)"
        )
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--services-only":
            # Run only service tests
            success = run_service_tests_only()
        else:
            # Run specific test file
            test_file = sys.argv[1]
            success = run_specific_test(test_file)
    else:
        # Run all tests
        success = run_backend_tests()

    sys.exit(0 if success else 1)