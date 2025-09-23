#!/usr/bin/env python3
"""Focused Type Safety Fix Script.

This script systematically fixes the most critical type safety issues
identified in the MyPy output, focusing on:

1. Missing type annotations
2. Database operations inheritance issues
3. Optional parameter fixes
4. Test method annotations
5. Critical type mismatches

Usage:
    python scripts/fix_types.py [--critical] [--tests] [--all]
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class TypeFixer:
    """Focused type safety fixer."""

    def __init__(self, backend_path: str = "."):
        self.backend_path = Path(backend_path)
        self.fixes_applied = 0

    def fix_critical_types(self) -> None:
        """Fix critical type safety issues."""
        print("🔧 Fixing critical type safety issues...")

        # Fix database service type issues
        self._fix_database_service_types()

        # Fix package status operations
        self._fix_package_status_operations()

        # Fix database operations inheritance
        self._fix_database_operations_inheritance()

        # Fix model type issues
        self._fix_model_types()

    def _fix_database_service_types(self) -> None:
        """Fix database service type annotations."""
        service_file = self.backend_path / "database" / "service.py"

        with open(service_file, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # Fix type annotations
        content = re.sub(
            r"def __init__\(self, database_url: str\):",
            r"def __init__(self, database_url: str) -> None:",
            content,
        )

        content = re.sub(
            r"def _mask_database_url\(self\):",
            r"def _mask_database_url(self) -> str:",
            content,
        )

        # Fix variable type annotations
        content = re.sub(
            r"self\._engine = None",
            r"self._engine: Optional[Engine] = None",
            content,
        )

        content = re.sub(
            r"self\._SessionLocal = None",
            r"self._SessionLocal: Optional[sessionmaker] = None",
            content,
        )

        # Add missing imports
        if "from typing import" not in content:
            content = content.replace(
                "import logging",
                "import logging\nfrom typing import Optional\nfrom sqlalchemy import Engine\nfrom sqlalchemy.orm import sessionmaker",
            )

        if content != original_content:
            with open(service_file, "w", encoding="utf-8") as f:
                f.write(content)
            self.fixes_applied += 1
            print(f"✅ Fixed database service types")

    def _fix_package_status_operations(self) -> None:
        """Fix package status operations type issues."""
        ops_file = (
            self.backend_path
            / "database"
            / "operations"
            / "package_status_operations.py"
        )

        with open(ops_file, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # Fix method signatures
        content = re.sub(
            r"def update_status\(self, package_id: int, status: str\):",
            r"def update_status(self, package_id: int, status: str) -> bool:",
            content,
        )

        content = re.sub(
            r"def update_license_info\(self, package_id: int, license_score: int, license_status: str\):",
            r"def update_license_info(self, package_id: int, license_score: int, license_status: str) -> bool:",
            content,
        )

        # Fix inheritance issues - override get_all and get_by_id properly
        content = re.sub(
            r"def get_all\(self\) -> List\[PackageStatus\]:",
            r"def get_all(self, model_class: Type[PackageStatus]) -> List[PackageStatus]:",
            content,
        )

        # Add Type import if needed
        if (
            "Type[" in content
            and "Type" not in content.split("from typing import")[0]
        ):
            content = content.replace(
                "from typing import", "from typing import Type,"
            )

        if content != original_content:
            with open(ops_file, "w", encoding="utf-8") as f:
                f.write(content)
            self.fixes_applied += 1
            print(f"✅ Fixed package status operations types")

    def _fix_database_operations_inheritance(self) -> None:
        """Fix database operations inheritance issues."""
        operations_files = [
            "user_operations.py",
            "request_operations.py",
            "request_package_operations.py",
            "security_scan_operations.py",
            "supported_license_operations.py",
        ]

        for ops_file in operations_files:
            file_path = (
                self.backend_path / "database" / "operations" / ops_file
            )

            if not file_path.exists():
                continue

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            original_content = content

            # Fix get_all method signatures
            content = re.sub(
                r"def get_all\(self\) -> List\[(\w+)\]:",
                r"def get_all(self, model_class: Type[\1]) -> List[\1]:",
                content,
            )

            # Fix get_by_id method signatures
            content = re.sub(
                r"def get_by_id\(self, (\w+_id): int\) -> (\w+ \| None):",
                r"def get_by_id(self, model_class: Type[\2], \1: int) -> Optional[\2]:",
                content,
            )

            # Add Type import if needed
            if (
                "Type[" in content
                and "Type" not in content.split("from typing import")[0]
            ):
                content = content.replace(
                    "from typing import", "from typing import Type,"
                )

            if content != original_content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.fixes_applied += 1
                print(f"✅ Fixed {ops_file} inheritance")

    def _fix_model_types(self) -> None:
        """Fix model type issues."""
        # Fix user model
        user_model = self.backend_path / "database" / "models" / "user.py"
        if user_model.exists():
            with open(user_model, "r", encoding="utf-8") as f:
                content = f.read()

            original_content = content

            # Fix the dict.get issue
            content = re.sub(
                r"roles\.get\(self\.role, \[\]\)",
                r"roles.get(str(self.role), [])",
                content,
            )

            if content != original_content:
                with open(user_model, "w", encoding="utf-8") as f:
                    f.write(content)
                self.fixes_applied += 1
                print(f"✅ Fixed user model types")

        # Fix package status model
        status_model = (
            self.backend_path / "database" / "models" / "package_status.py"
        )
        if status_model.exists():
            with open(status_model, "r", encoding="utf-8") as f:
                content = f.read()

            original_content = content

            # Fix the dict.get issue
            content = re.sub(
                r'status_descriptions\.get\(self\.status, "Unknown"\)',
                r'status_descriptions.get(str(self.status), "Unknown")',
                content,
            )

            if content != original_content:
                with open(status_model, "w", encoding="utf-8") as f:
                    f.write(content)
                self.fixes_applied += 1
                print(f"✅ Fixed package status model types")

    def fix_test_annotations(self) -> None:
        """Fix test method type annotations."""
        print("🧪 Fixing test method annotations...")

        test_files = list(self.backend_path.glob("tests/**/*.py"))

        for test_file in test_files:
            if test_file.name == "__init__.py":
                continue

            self._fix_test_file_annotations(test_file)

    def _fix_test_file_annotations(self, test_file: Path) -> None:
        """Fix type annotations in a test file."""
        try:
            with open(test_file, "r", encoding="utf-8") as f:
                content = f.read()

            original_content = content

            # Fix test method signatures
            content = re.sub(
                r"def (test_\w+)\([^)]*\):\s*$",
                r"def \1() -> None:",
                content,
                flags=re.MULTILINE,
            )

            # Fix setUp and tearDown methods
            content = re.sub(
                r"def (setUp|tearDown)\([^)]*\):\s*$",
                r"def \1() -> None:",
                content,
                flags=re.MULTILINE,
            )

            # Fix helper method signatures
            content = re.sub(
                r"def (_\w+)\([^)]*\):\s*$",
                r"def \1() -> None:",
                content,
                flags=re.MULTILINE,
            )

            if content != original_content:
                with open(test_file, "w", encoding="utf-8") as f:
                    f.write(content)
                self.fixes_applied += 1
                print(f"✅ Fixed test annotations in {test_file.name}")

        except Exception as e:
            print(f"❌ Error fixing test annotations in {test_file}: {e}")

    def fix_service_annotations(self) -> None:
        """Fix service method type annotations."""
        print("🔧 Fixing service method annotations...")

        service_files = list(self.backend_path.glob("services/*.py"))

        for service_file in service_files:
            self._fix_service_file_annotations(service_file)

    def _fix_service_file_annotations(self, service_file: Path) -> None:
        """Fix type annotations in a service file."""
        try:
            with open(service_file, "r", encoding="utf-8") as f:
                content = f.read()

            original_content = content

            # Fix __init__ methods
            content = re.sub(
                r"def __init__\(self\):\s*$",
                r"def __init__(self) -> None:",
                content,
                flags=re.MULTILINE,
            )

            # Fix methods without return types
            content = re.sub(
                r"def (\w+)\([^)]*\):\s*$",
                r"def \1() -> None:",
                content,
                flags=re.MULTILINE,
            )

            # Add missing imports
            if "from typing import" not in content and (
                "Optional[" in content
                or "List[" in content
                or "Dict[" in content
            ):
                content = content.replace(
                    "import logging",
                    "import logging\nfrom typing import Any, Dict, List, Optional",
                )

            if content != original_content:
                with open(service_file, "w", encoding="utf-8") as f:
                    f.write(content)
                self.fixes_applied += 1
                print(f"✅ Fixed service annotations in {service_file.name}")

        except Exception as e:
            print(
                f"❌ Error fixing service annotations in {service_file}: {e}"
            )

    def fix_worker_annotations(self) -> None:
        """Fix worker type annotations."""
        print("🔧 Fixing worker type annotations...")

        worker_files = list(self.backend_path.glob("workers/*.py"))

        for worker_file in worker_files:
            if worker_file.name == "__init__.py":
                continue

            self._fix_worker_file_annotations(worker_file)

    def _fix_worker_file_annotations(self, worker_file: Path) -> None:
        """Fix type annotations in a worker file."""
        try:
            with open(worker_file, "r", encoding="utf-8") as f:
                content = f.read()

            original_content = content

            # Fix service attribute type annotations
            if "self.service = None" in content:
                # Extract service class name
                service_match = re.search(r"(\w+Service)", content)
                if service_match:
                    service_class = service_match.group(1)
                    content = content.replace(
                        "self.service = None",
                        f"self.service: Optional[{service_class}] = None",
                    )

            # Add Optional import if needed
            if (
                "Optional[" in content
                and "Optional" not in content.split("from typing import")[0]
            ):
                content = content.replace(
                    "from typing import", "from typing import Optional,"
                )

            if content != original_content:
                with open(worker_file, "w", encoding="utf-8") as f:
                    f.write(content)
                self.fixes_applied += 1
                print(f"✅ Fixed worker annotations in {worker_file.name}")

        except Exception as e:
            print(f"❌ Error fixing worker annotations in {worker_file}: {e}")

    def run_fixes(
        self,
        critical: bool = False,
        tests: bool = False,
        services: bool = False,
        workers: bool = False,
        all_fixes: bool = False,
    ) -> None:
        """Run type fixes."""
        print("🛡️ Starting Type Safety Fixes...")
        print("=" * 60)

        if all_fixes or critical:
            self.fix_critical_types()

        if all_fixes or tests:
            self.fix_test_annotations()

        if all_fixes or services:
            self.fix_service_annotations()

        if all_fixes or workers:
            self.fix_worker_annotations()

        print("=" * 60)
        print(f"✅ Type fixes complete!")
        print(f"   Fixes applied: {self.fixes_applied}")

        if self.fixes_applied > 0:
            print("🎉 Type safety has been improved!")
        else:
            print("ℹ️  No fixes were needed.")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Fix type safety issues")
    parser.add_argument(
        "--critical", action="store_true", help="Fix critical type issues"
    )
    parser.add_argument(
        "--tests", action="store_true", help="Fix test annotations"
    )
    parser.add_argument(
        "--services", action="store_true", help="Fix service annotations"
    )
    parser.add_argument(
        "--workers", action="store_true", help="Fix worker annotations"
    )
    parser.add_argument("--all", action="store_true", help="Run all fixes")

    args = parser.parse_args()

    if not any(
        [args.critical, args.tests, args.services, args.workers, args.all]
    ):
        parser.print_help()
        sys.exit(1)

    fixer = TypeFixer()
    fixer.run_fixes(
        critical=args.critical,
        tests=args.tests,
        services=args.services,
        workers=args.workers,
        all_fixes=args.all,
    )


if __name__ == "__main__":
    main()
