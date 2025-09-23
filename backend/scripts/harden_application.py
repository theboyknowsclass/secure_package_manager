#!/usr/bin/env python3
"""Application Hardening Script.

This script systematically addresses the major code quality issues identified
in the secure package manager application:

1. Type annotation fixes
2. Deprecated code removal
3. Database operations standardization
4. Test infrastructure improvements
5. Runtime validation enhancements

Usage:
    python scripts/harden_application.py [--fix-types] [--remove-deprecated] [--standardize-ops] [--all]
"""

import argparse
import ast
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class ApplicationHardener:
    """Main class for hardening the application."""

    def __init__(self, backend_path: str = "backend"):
        self.backend_path = Path(backend_path)
        self.fixes_applied = 0
        self.errors_found = 0

    def fix_type_annotations(self) -> None:
        """Fix missing type annotations throughout the codebase."""
        print("🔧 Fixing type annotations...")

        # Common patterns to fix
        type_fixes = [
            # Function definitions without return types
            (
                r"def (\w+)\([^)]*\):\s*$",
                r'def \1() -> None:\n    """TODO: Add docstring."""',
            ),
            # Optional parameters
            (r"(\w+): (\w+) = None", r"\1: Optional[\2] = None"),
            # Missing imports
        ]

        # Files to process
        python_files = list(self.backend_path.rglob("*.py"))

        for file_path in python_files:
            if self._should_skip_file(file_path):
                continue

            try:
                self._fix_file_type_annotations(file_path)
            except Exception as e:
                print(f"❌ Error processing {file_path}: {e}")
                self.errors_found += 1

    def _fix_file_type_annotations(self, file_path: Path) -> None:
        """Fix type annotations in a specific file."""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # Add missing imports
        if "Optional" in content and "from typing import" not in content:
            content = self._add_typing_imports(content)

        # Fix function signatures
        content = self._fix_function_signatures(content)

        # Fix variable annotations
        content = self._fix_variable_annotations(content)

        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            self.fixes_applied += 1
            print(f"✅ Fixed type annotations in {file_path}")

    def _add_typing_imports(self, content: str) -> str:
        """Add necessary typing imports."""
        imports_to_add = []

        if (
            "Optional" in content
            and "Optional" not in content.split("from typing import")[0]
        ):
            imports_to_add.append("Optional")
        if (
            "List" in content
            and "List" not in content.split("from typing import")[0]
        ):
            imports_to_add.append("List")
        if (
            "Dict" in content
            and "Dict" not in content.split("from typing import")[0]
        ):
            imports_to_add.append("Dict")
        if (
            "Any" in content
            and "Any" not in content.split("from typing import")[0]
        ):
            imports_to_add.append("Any")

        if imports_to_add:
            # Find existing typing import
            typing_import_pattern = r"from typing import ([^\n]+)"
            match = re.search(typing_import_pattern, content)

            if match:
                # Add to existing import
                existing_imports = match.group(1)
                new_imports = ", ".join(imports_to_add)
                content = content.replace(
                    f"from typing import {existing_imports}",
                    f"from typing import {existing_imports}, {new_imports}",
                )
            else:
                # Add new import after other imports
                import_section = self._find_import_section(content)
                if import_section:
                    content = content.replace(
                        import_section,
                        f"{import_section}\nfrom typing import {', '.join(imports_to_add)}",
                    )

        return content

    def _fix_function_signatures(self, content: str) -> str:
        """Fix function signatures without return types."""
        # Pattern for functions without return types
        pattern = r"def (\w+)\(([^)]*)\):\s*$"

        def replace_func(match):
            func_name = match.group(1)
            params = match.group(2)

            # Skip if already has return type
            if "->" in match.group(0):
                return match.group(0)

            # Add return type based on function name
            if func_name.startswith("test_"):
                return f"def {func_name}({params}) -> None:"
            elif func_name.startswith("_"):
                return f"def {func_name}({params}) -> None:"
            else:
                return f"def {func_name}({params}) -> None:"

        return re.sub(pattern, replace_func, content, flags=re.MULTILINE)

    def _fix_variable_annotations(self, content: str) -> str:
        """Fix variable annotations."""
        # Fix None default parameters
        content = re.sub(
            r"(\w+): (\w+) = None", r"\1: Optional[\2] = None", content
        )

        return content

    def _find_import_section(self, content: str) -> Optional[str]:
        """Find the import section of a file."""
        lines = content.split("\n")
        import_lines = []

        for line in lines:
            if line.strip().startswith(("import ", "from ")):
                import_lines.append(line)
            elif line.strip() and not line.strip().startswith("#"):
                break

        return "\n".join(import_lines) if import_lines else None

    def remove_deprecated_code(self) -> None:
        """Remove or update deprecated code patterns."""
        print("🗑️ Removing deprecated code...")

        deprecated_patterns = [
            # Deprecated malware scanning
            {
                "file_pattern": "**/validation_service.py",
                "code_pattern": r'def _validate_malware_scan.*?return \{[^}]*"deprecated"[^}]*\}',
                "replacement": "# Malware scanning removed - handled by TrivyService",
                "flags": re.DOTALL,
            },
            # Deprecated vulnerability assessment
            {
                "file_pattern": "**/validation_service.py",
                "code_pattern": r'def _validate_vulnerabilities.*?return \{[^}]*"deprecated"[^}]*\}',
                "replacement": "# Vulnerability assessment removed - handled by TrivyService",
                "flags": re.DOTALL,
            },
        ]

        for pattern in deprecated_patterns:
            files = list(self.backend_path.glob(pattern["file_pattern"]))
            for file_path in files:
                self._remove_deprecated_from_file(file_path, pattern)

    def _remove_deprecated_from_file(
        self, file_path: Path, pattern: Dict[str, Any]
    ) -> None:
        """Remove deprecated code from a specific file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            original_content = content

            # Remove deprecated code
            content = re.sub(
                pattern["code_pattern"],
                pattern["replacement"],
                content,
                flags=pattern.get("flags", 0),
            )

            if content != original_content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.fixes_applied += 1
                print(f"✅ Removed deprecated code from {file_path}")

        except Exception as e:
            print(f"❌ Error removing deprecated code from {file_path}: {e}")
            self.errors_found += 1

    def standardize_database_operations(self) -> None:
        """Standardize database operations patterns."""
        print("🔧 Standardizing database operations...")

        # Fix inheritance issues in operations classes
        operations_files = list(
            self.backend_path.glob("database/operations/*_operations.py")
        )

        for file_path in operations_files:
            if file_path.name == "base_operations.py":
                continue

            self._standardize_operations_file(file_path)

    def _standardize_operations_file(self, file_path: Path) -> None:
        """Standardize a specific operations file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            original_content = content

            # Fix method signatures to match base class
            content = self._fix_operations_method_signatures(content)

            # Add proper type annotations
            content = self._add_operations_type_annotations(content)

            if content != original_content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.fixes_applied += 1
                print(f"✅ Standardized {file_path}")

        except Exception as e:
            print(f"❌ Error standardizing {file_path}: {e}")
            self.errors_found += 1

    def _fix_operations_method_signatures(self, content: str) -> str:
        """Fix method signatures in operations files."""
        # Fix get_by_id methods
        content = re.sub(
            r"def get_by_id\(self, (\w+_id): int\) -> (\w+ \| None):",
            r"def get_by_id(self, model_class: Type[\2], \1: int) -> Optional[\2]:",
            content,
        )

        # Fix get_all methods
        content = re.sub(
            r"def get_all\(self\) -> List\[(\w+)\]:",
            r"def get_all(self, model_class: Type[\1]) -> List[\1]:",
            content,
        )

        return content

    def _add_operations_type_annotations(self, content: str) -> str:
        """Add type annotations to operations files."""
        # Add Type import if needed
        if (
            "Type[" in content
            and "Type" not in content.split("from typing import")[0]
        ):
            content = self._add_typing_imports(content)

        return content

    def improve_test_infrastructure(self) -> None:
        """Improve test infrastructure and fix import issues."""
        print("🧪 Improving test infrastructure...")

        # Fix test import issues
        test_files = list(self.backend_path.glob("tests/**/*.py"))

        for test_file in test_files:
            self._fix_test_imports(test_file)

    def _fix_test_imports(self, test_file: Path) -> None:
        """Fix import issues in test files."""
        try:
            with open(test_file, "r", encoding="utf-8") as f:
                content = f.read()

            original_content = content

            # Fix relative imports
            content = self._fix_relative_imports(content, test_file)

            # Add missing type annotations to test methods
            content = self._fix_test_method_annotations(content)

            if content != original_content:
                with open(test_file, "w", encoding="utf-8") as f:
                    f.write(content)
                self.fixes_applied += 1
                print(f"✅ Fixed test imports in {test_file}")

        except Exception as e:
            print(f"❌ Error fixing test imports in {test_file}: {e}")
            self.errors_found += 1

    def _fix_relative_imports(self, content: str, test_file: Path) -> str:
        """Fix relative imports in test files."""
        # Calculate relative path from test file to backend root
        relative_path = test_file.relative_to(self.backend_path)
        depth = len(relative_path.parts) - 1

        # Add sys.path modification if needed
        if "sys.path.insert" not in content and "import sys" not in content:
            sys_path_line = f'sys.path.insert(0, os.path.join(os.path.dirname(__file__), {".." * depth}))'
            content = f"import os\nimport sys\n{sys_path_line}\n\n{content}"

        return content

    def _fix_test_method_annotations(self, content: str) -> None:
        """Fix test method annotations."""
        # Add -> None to test methods
        content = re.sub(
            r"def (test_\w+)\([^)]*\):\s*$",
            r"def \1() -> None:",
            content,
            flags=re.MULTILINE,
        )

        return content

    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped."""
        skip_patterns = [
            "__pycache__",
            ".git",
            "migrations",
            "node_modules",
            ".pytest_cache",
        ]

        return any(pattern in str(file_path) for pattern in skip_patterns)

    def run_hardening(
        self,
        fix_types: bool = False,
        remove_deprecated: bool = False,
        standardize_ops: bool = False,
        all_fixes: bool = False,
    ) -> None:
        """Run the hardening process."""
        print("🛡️ Starting Application Hardening Process...")
        print("=" * 60)

        if all_fixes or fix_types:
            self.fix_type_annotations()

        if all_fixes or remove_deprecated:
            self.remove_deprecated_code()

        if all_fixes or standardize_ops:
            self.standardize_database_operations()

        if all_fixes:
            self.improve_test_infrastructure()

        print("=" * 60)
        print(f"✅ Hardening complete!")
        print(f"   Fixes applied: {self.fixes_applied}")
        print(f"   Errors found: {self.errors_found}")

        if self.errors_found > 0:
            print(
                "⚠️  Some errors were encountered. Please review the output above."
            )
            sys.exit(1)
        else:
            print("🎉 All hardening steps completed successfully!")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Harden the secure package manager application"
    )
    parser.add_argument(
        "--fix-types", action="store_true", help="Fix type annotations"
    )
    parser.add_argument(
        "--remove-deprecated",
        action="store_true",
        help="Remove deprecated code",
    )
    parser.add_argument(
        "--standardize-ops",
        action="store_true",
        help="Standardize database operations",
    )
    parser.add_argument(
        "--all", action="store_true", help="Run all hardening steps"
    )

    args = parser.parse_args()

    if not any(
        [
            args.fix_types,
            args.remove_deprecated,
            args.standardize_ops,
            args.all,
        ]
    ):
        parser.print_help()
        sys.exit(1)

    hardener = ApplicationHardener()
    hardener.run_hardening(
        fix_types=args.fix_types,
        remove_deprecated=args.remove_deprecated,
        standardize_ops=args.standardize_ops,
        all_fixes=args.all,
    )


if __name__ == "__main__":
    main()
