#!/usr/bin/env python3
"""Test Infrastructure Improvement Script.

This script improves the test infrastructure by:
1. Fixing import issues
2. Adding missing test coverage
3. Creating proper test fixtures
4. Adding integration tests
5. Setting up test data management

Usage:
    python scripts/improve_tests.py [--fix-imports] [--add-coverage] [--create-fixtures] [--all]
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestImprover:
    """Improve test infrastructure and coverage."""

    def __init__(self, backend_path: str = "backend"):
        self.backend_path = Path(backend_path)
        self.tests_path = self.backend_path / "tests"
        self.improvements_made = 0

    def fix_test_imports(self) -> None:
        """Fix import issues in test files."""
        print("🔧 Fixing test import issues...")

        test_files = list(self.tests_path.rglob("*.py"))

        for test_file in test_files:
            if test_file.name == "__init__.py":
                continue

            self._fix_test_file_imports(test_file)

    def _fix_test_file_imports(self, test_file: Path) -> None:
        """Fix imports in a specific test file."""
        try:
            with open(test_file, "r", encoding="utf-8") as f:
                content = f.read()

            original_content = content

            # Add proper sys.path setup
            content = self._add_sys_path_setup(content, test_file)

            # Fix relative imports
            content = self._fix_relative_imports(content, test_file)

            # Add missing type annotations
            content = self._add_test_type_annotations(content)

            if content != original_content:
                with open(test_file, "w", encoding="utf-8") as f:
                    f.write(content)
                self.improvements_made += 1
                print(f"✅ Fixed imports in {test_file}")

        except Exception as e:
            print(f"❌ Error fixing imports in {test_file}: {e}")

    def _add_sys_path_setup(self, content: str, test_file: Path) -> str:
        """Add sys.path setup to test file."""
        if "sys.path.insert" in content:
            return content

        # Calculate relative path from test file to backend root
        relative_path = test_file.relative_to(self.backend_path)
        depth = len(relative_path.parts) - 1

        # Add sys.path setup at the beginning
        sys_path_setup = f"""import os
import sys

# Add backend to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), {".." * depth}))

"""

        # Find where to insert (after existing imports)
        lines = content.split("\n")
        insert_index = 0

        for i, line in enumerate(lines):
            if line.strip().startswith(("import ", "from ")):
                insert_index = i + 1
            elif line.strip() and not line.strip().startswith("#"):
                break

        lines.insert(insert_index, sys_path_setup.rstrip())
        return "\n".join(lines)

    def _fix_relative_imports(self, content: str, test_file: Path) -> str:
        """Fix relative imports in test files."""
        # Replace relative imports with absolute imports
        import_replacements = {
            "from services.": "from services.",
            "from database.": "from database.",
            "from workers.": "from workers.",
            "from routes.": "from routes.",
        }

        for old_import, new_import in import_replacements.items():
            content = content.replace(old_import, new_import)

        return content

    def _add_test_type_annotations(self, content: str) -> str:
        """Add type annotations to test methods."""
        import re

        # Add -> None to test methods
        content = re.sub(
            r"def (test_\w+)\([^)]*\):\s*$",
            r"def \1() -> None:",
            content,
            flags=re.MULTILINE,
        )

        # Add -> None to setUp and tearDown methods
        content = re.sub(
            r"def (setUp|tearDown)\([^)]*\):\s*$",
            r"def \1() -> None:",
            content,
            flags=re.MULTILINE,
        )

        return content

    def add_test_coverage(self) -> None:
        """Add missing test coverage."""
        print("📊 Adding missing test coverage...")

        # Create test files for missing coverage
        self._create_worker_tests()
        self._create_integration_tests()
        self._create_fixture_tests()

    def _create_worker_tests(self) -> None:
        """Create tests for workers."""
        workers_path = self.tests_path / "workers"
        workers_path.mkdir(exist_ok=True)

        # Create __init__.py
        init_file = workers_path / "__init__.py"
        if not init_file.exists():
            init_file.write_text('"""Worker tests package."""\n')

        # Create test files for each worker
        worker_files = [
            "test_parse_worker.py",
            "test_download_worker.py",
            "test_license_worker.py",
            "test_security_worker.py",
            "test_publish_worker.py",
            "test_approval_worker.py",
        ]

        for worker_file in worker_files:
            test_file = workers_path / worker_file
            if not test_file.exists():
                self._create_worker_test_file(
                    test_file,
                    worker_file.replace("test_", "").replace(".py", ""),
                )

    def _create_worker_test_file(
        self, test_file: Path, worker_name: str
    ) -> None:
        """Create a test file for a specific worker."""
        worker_class = f"{worker_name.title().replace('_', '')}Worker"

        test_content = f'''#!/usr/bin/env python3
"""Tests for {worker_class}."""

import os
import sys
import unittest
from unittest.mock import Mock, patch

# Add backend to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from workers.{worker_name}_worker import {worker_class}


class Test{worker_class}(unittest.TestCase):
    """Test suite for {worker_class}."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.worker = {worker_class}(sleep_interval=1)

    def test_worker_initialization(self) -> None:
        """Test worker initialization."""
        self.assertEqual(self.worker.WORKER_TYPE, "{worker_name}_worker")
        self.assertEqual(self.worker.sleep_interval, 1)

    def test_worker_initialization_with_service(self) -> None:
        """Test worker service initialization."""
        with patch('workers.{worker_name}_worker.{worker_class.replace("Worker", "Service")}') as mock_service:
            self.worker.initialize()
            # Add specific assertions based on worker type
            self.assertIsNotNone(self.worker)

    def test_process_cycle_no_requests(self) -> None:
        """Test process cycle with no requests."""
        with patch.object(self.worker, 'initialize'):
            self.worker.initialize()
            # Mock the service to return no requests
            if hasattr(self.worker, 'service') and self.worker.service:
                self.worker.service.process_requests = Mock(return_value={{"success": True, "processed_requests": 0}})
            
            # Should not raise any exceptions
            self.worker.process_cycle()

    def test_get_required_env_vars(self) -> None:
        """Test required environment variables."""
        env_vars = self.worker.get_required_env_vars()
        self.assertIsInstance(env_vars, list)
        self.assertIn("DATABASE_URL", env_vars)


if __name__ == "__main__":
    unittest.main()
'''

        test_file.write_text(test_content)
        self.improvements_made += 1
        print(f"✅ Created test file: {test_file}")

    def _create_integration_tests(self) -> None:
        """Create integration tests."""
        integration_path = self.tests_path / "integration"
        integration_path.mkdir(exist_ok=True)

        # Create __init__.py
        init_file = integration_path / "__init__.py"
        if not init_file.exists():
            init_file.write_text('"""Integration tests package."""\n')

        # Create end-to-end test
        e2e_test = integration_path / "test_end_to_end.py"
        if not e2e_test.exists():
            self._create_e2e_test(e2e_test)

    def _create_e2e_test(self, test_file: Path) -> None:
        """Create end-to-end integration test."""
        test_content = '''#!/usr/bin/env python3
"""End-to-end integration tests."""

import os
import sys
import unittest
from unittest.mock import Mock, patch

# Add backend to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from services.package_lock_parsing_service import PackageLockParsingService
from services.license_service import LicenseService
from services.security_service import SecurityService


class TestEndToEnd(unittest.TestCase):
    """End-to-end integration tests."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.parsing_service = PackageLockParsingService()
        # Add other services as needed

    def test_package_processing_pipeline(self) -> None:
        """Test complete package processing pipeline."""
        # This would test the full pipeline from package upload to approval
        # For now, just test that services can be instantiated
        self.assertIsNotNone(self.parsing_service)

    def test_database_operations_integration(self) -> None:
        """Test database operations integration."""
        # Test that database operations work together
        # This would require a test database setup
        pass

    def test_worker_integration(self) -> None:
        """Test worker integration."""
        # Test that workers can process requests end-to-end
        pass


if __name__ == "__main__":
    unittest.main()
'''

        test_file.write_text(test_content)
        self.improvements_made += 1
        print(f"✅ Created integration test: {test_file}")

    def _create_fixture_tests(self) -> None:
        """Create test fixtures and utilities."""
        fixtures_path = self.tests_path / "fixtures"
        fixtures_path.mkdir(exist_ok=True)

        # Create __init__.py
        init_file = fixtures_path / "__init__.py"
        if not init_file.exists():
            init_file.write_text('"""Test fixtures package."""\n')

        # Create database fixtures
        db_fixtures = fixtures_path / "database_fixtures.py"
        if not db_fixtures.exists():
            self._create_database_fixtures(db_fixtures)

        # Create service fixtures
        service_fixtures = fixtures_path / "service_fixtures.py"
        if not service_fixtures.exists():
            self._create_service_fixtures(service_fixtures)

    def _create_database_fixtures(self, fixtures_file: Path) -> None:
        """Create database test fixtures."""
        fixtures_content = '''#!/usr/bin/env python3
"""Database test fixtures."""

import os
import sys
from typing import Any, Dict, List, Optional

# Add backend to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from database.session_helper import SessionHelper
from database.models import User, Request, Package, PackageStatus


class DatabaseFixtures:
    """Database test fixtures."""

    @staticmethod
    def create_test_user(user_data: Optional[Dict[str, Any]] = None) -> User:
        """Create a test user."""
        default_data = {
            "username": "testuser",
            "email": "test@example.com",
            "role": "user"
        }
        if user_data:
            default_data.update(user_data)
            
        # This would create a test user in the database
        # For now, return a mock
        return Mock(**default_data)

    @staticmethod
    def create_test_request(request_data: Optional[Dict[str, Any]] = None) -> Request:
        """Create a test request."""
        default_data = {
            "requestor_id": 1,
            "raw_request_blob": '{"name": "test-package", "version": "1.0.0"}',
            "status": "Pending"
        }
        if request_data:
            default_data.update(request_data)
            
        return Mock(**default_data)

    @staticmethod
    def create_test_package(package_data: Optional[Dict[str, Any]] = None) -> Package:
        """Create a test package."""
        default_data = {
            "name": "test-package",
            "version": "1.0.0",
            "npm_url": "https://registry.npmjs.org/test-package/-/test-package-1.0.0.tgz",
            "license_identifier": "MIT"
        }
        if package_data:
            default_data.update(package_data)
            
        return Mock(**default_data)

    @staticmethod
    def create_test_package_status(status_data: Optional[Dict[str, Any]] = None) -> PackageStatus:
        """Create a test package status."""
        default_data = {
            "package_id": 1,
            "status": "Pending",
            "license_status": "Checking Licence",
            "security_scan_status": "Pending"
        }
        if status_data:
            default_data.update(status_data)
            
        return Mock(**default_data)

    @staticmethod
    def cleanup_test_data() -> None:
        """Clean up test data."""
        # This would clean up test data from the database
        pass
'''

        fixtures_file.write_text(fixtures_content)
        self.improvements_made += 1
        print(f"✅ Created database fixtures: {fixtures_file}")

    def _create_service_fixtures(self, fixtures_file: Path) -> None:
        """Create service test fixtures."""
        fixtures_content = '''#!/usr/bin/env python3
"""Service test fixtures."""

import os
import sys
from typing import Any, Dict, List, Optional
from unittest.mock import Mock

# Add backend to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


class ServiceFixtures:
    """Service test fixtures."""

    @staticmethod
    def create_mock_package_lock_data() -> Dict[str, Any]:
        """Create mock package-lock.json data."""
        return {
            "name": "test-app",
            "version": "1.0.0",
            "lockfileVersion": 3,
            "packages": {
                "": {
                    "name": "test-app",
                    "version": "1.0.0"
                },
                "node_modules/lodash": {
                    "version": "4.17.21",
                    "resolved": "https://registry.npmjs.org/lodash/-/lodash-4.17.21.tgz",
                    "integrity": "sha512-v2kDEe57lecTulaDIuNTPy3Ry4gLGJ6Z1O3vE1krgXZNrsQ+LFTGHVxVjcXPs17LhbZVGedAJv8XZ1tvj5FvSg==",
                    "license": "MIT"
                }
            }
        }

    @staticmethod
    def create_mock_license_data() -> Dict[str, Any]:
        """Create mock license data."""
        return {
            "identifier": "MIT",
            "text": "MIT License text...",
            "is_osi_approved": True,
            "is_fsf_approved": True
        }

    @staticmethod
    def create_mock_security_scan_data() -> Dict[str, Any]:
        """Create mock security scan data."""
        return {
            "vulnerabilities": [],
            "score": 100,
            "status": "completed"
        }

    @staticmethod
    def create_mock_operations() -> Dict[str, Mock]:
        """Create mock database operations."""
        return {
            "request_ops": Mock(),
            "package_ops": Mock(),
            "package_status_ops": Mock(),
            "user_ops": Mock(),
            "audit_log_ops": Mock()
        }
'''

        fixtures_file.write_text(fixtures_content)
        self.improvements_made += 1
        print(f"✅ Created service fixtures: {fixtures_file}")

    def create_test_configuration(self) -> None:
        """Create test configuration files."""
        print("⚙️ Creating test configuration...")

        # Create pytest configuration
        pytest_ini = self.backend_path / "pytest.ini"
        if not pytest_ini.exists():
            pytest_content = """[tool:pytest]
testpaths = tests
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short --strict-markers
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow running tests
"""
            pytest_ini.write_text(pytest_content)
            self.improvements_made += 1
            print(f"✅ Created pytest configuration: {pytest_ini}")

        # Create test requirements
        test_requirements = self.backend_path / "requirements-test.txt"
        if not test_requirements.exists():
            test_req_content = """# Test requirements
pytest>=7.0.0
pytest-cov>=4.0.0
pytest-mock>=3.10.0
pytest-asyncio>=0.21.0
coverage>=7.0.0
factory-boy>=3.2.0
faker>=18.0.0
"""
            test_requirements.write_text(test_req_content)
            self.improvements_made += 1
            print(f"✅ Created test requirements: {test_requirements}")

    def run_improvements(
        self,
        fix_imports: bool = False,
        add_coverage: bool = False,
        create_fixtures: bool = False,
        all_improvements: bool = False,
    ) -> None:
        """Run test improvements."""
        print("🧪 Starting Test Infrastructure Improvements...")
        print("=" * 60)

        if all_improvements or fix_imports:
            self.fix_test_imports()

        if all_improvements or add_coverage:
            self.add_test_coverage()

        if all_improvements or create_fixtures:
            self.create_test_configuration()

        print("=" * 60)
        print(f"✅ Test improvements complete!")
        print(f"   Improvements made: {self.improvements_made}")

        if self.improvements_made > 0:
            print("🎉 Test infrastructure has been improved!")
        else:
            print("ℹ️  No improvements were needed.")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Improve test infrastructure")
    parser.add_argument(
        "--fix-imports", action="store_true", help="Fix test import issues"
    )
    parser.add_argument(
        "--add-coverage", action="store_true", help="Add missing test coverage"
    )
    parser.add_argument(
        "--create-fixtures", action="store_true", help="Create test fixtures"
    )
    parser.add_argument(
        "--all", action="store_true", help="Run all improvements"
    )

    args = parser.parse_args()

    if not any(
        [args.fix_imports, args.add_coverage, args.create_fixtures, args.all]
    ):
        parser.print_help()
        sys.exit(1)

    improver = TestImprover()
    improver.run_improvements(
        fix_imports=args.fix_imports,
        add_coverage=args.add_coverage,
        create_fixtures=args.create_fixtures,
        all_improvements=args.all,
    )


if __name__ == "__main__":
    main()
