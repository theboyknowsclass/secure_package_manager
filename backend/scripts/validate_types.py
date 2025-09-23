#!/usr/bin/env python3
"""Type Validation Script.

This script provides comprehensive type checking and validation for the
secure package manager application. It runs multiple validation tools
and provides detailed reports on code quality issues.

Usage:
    python scripts/validate_types.py [--strict] [--fix] [--report]
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class TypeValidator:
    """Comprehensive type validation for the application."""

    def __init__(self, backend_path: str = "backend"):
        self.backend_path = Path(backend_path)
        self.validation_results = {
            "mypy": {"errors": 0, "warnings": 0, "issues": []},
            "flake8": {"errors": 0, "warnings": 0, "issues": []},
            "black": {"errors": 0, "warnings": 0, "issues": []},
            "isort": {"errors": 0, "warnings": 0, "issues": []},
            "pylint": {"errors": 0, "warnings": 0, "issues": []},
        }

    def run_mypy(self, strict: bool = False) -> Dict[str, Any]:
        """Run MyPy type checking."""
        print("🔍 Running MyPy type checking...")

        cmd = ["python", "-m", "mypy", str(self.backend_path)]

        if strict:
            cmd.extend(["--strict", "--show-error-codes"])
        else:
            cmd.extend(["--show-error-codes", "--ignore-missing-imports"])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.backend_path.parent,
            )

            if result.returncode == 0:
                print("✅ MyPy: No type errors found")
                return {"status": "success", "output": result.stdout}
            else:
                print(
                    f"❌ MyPy: Found {len(result.stderr.splitlines())} type errors"
                )
                self.validation_results["mypy"]["errors"] = len(
                    result.stderr.splitlines()
                )
                self.validation_results["mypy"][
                    "issues"
                ] = result.stderr.splitlines()
                return {"status": "error", "output": result.stderr}

        except Exception as e:
            print(f"❌ MyPy failed to run: {e}")
            return {"status": "error", "output": str(e)}

    def run_flake8(self) -> Dict[str, Any]:
        """Run Flake8 linting."""
        print("🔍 Running Flake8 linting...")

        cmd = [
            "python",
            "-m",
            "flake8",
            str(self.backend_path),
            "--max-line-length=79",
            "--extend-ignore=E203,W503",
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.backend_path.parent,
            )

            if result.returncode == 0:
                print("✅ Flake8: No style issues found")
                return {"status": "success", "output": result.stdout}
            else:
                issues = result.stdout.splitlines()
                print(f"❌ Flake8: Found {len(issues)} style issues")
                self.validation_results["flake8"]["errors"] = len(issues)
                self.validation_results["flake8"]["issues"] = issues
                return {"status": "error", "output": result.stdout}

        except Exception as e:
            print(f"❌ Flake8 failed to run: {e}")
            return {"status": "error", "output": str(e)}

    def run_black_check(self) -> Dict[str, Any]:
        """Run Black formatting check."""
        print("🔍 Running Black formatting check...")

        cmd = [
            "python",
            "-m",
            "black",
            "--check",
            "--diff",
            str(self.backend_path),
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.backend_path.parent,
            )

            if result.returncode == 0:
                print("✅ Black: Code formatting is correct")
                return {"status": "success", "output": result.stdout}
            else:
                print("❌ Black: Code formatting issues found")
                self.validation_results["black"]["errors"] = 1
                self.validation_results["black"]["issues"] = [result.stdout]
                return {"status": "error", "output": result.stdout}

        except Exception as e:
            print(f"❌ Black failed to run: {e}")
            return {"status": "error", "output": str(e)}

    def run_isort_check(self) -> Dict[str, Any]:
        """Run isort import check."""
        print("🔍 Running isort import check...")

        cmd = [
            "python",
            "-m",
            "isort",
            "--check-only",
            "--diff",
            str(self.backend_path),
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.backend_path.parent,
            )

            if result.returncode == 0:
                print("✅ isort: Import order is correct")
                return {"status": "success", "output": result.stdout}
            else:
                print("❌ isort: Import order issues found")
                self.validation_results["isort"]["errors"] = 1
                self.validation_results["isort"]["issues"] = [result.stdout]
                return {"status": "error", "output": result.stdout}

        except Exception as e:
            print(f"❌ isort failed to run: {e}")
            return {"status": "error", "output": str(e)}

    def run_pylint(self) -> Dict[str, Any]:
        """Run Pylint analysis."""
        print("🔍 Running Pylint analysis...")

        cmd = [
            "python",
            "-m",
            "pylint",
            str(self.backend_path),
            "--disable=C0114,C0116",
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.backend_path.parent,
            )

            # Pylint returns non-zero even for warnings, so we need to parse the output
            output_lines = result.stdout.splitlines()
            error_count = 0
            warning_count = 0

            for line in output_lines:
                if "error" in line.lower():
                    error_count += 1
                elif "warning" in line.lower():
                    warning_count += 1

            if error_count == 0 and warning_count == 0:
                print("✅ Pylint: No issues found")
                return {"status": "success", "output": result.stdout}
            else:
                print(
                    f"❌ Pylint: Found {error_count} errors, {warning_count} warnings"
                )
                self.validation_results["pylint"]["errors"] = error_count
                self.validation_results["pylint"]["warnings"] = warning_count
                self.validation_results["pylint"]["issues"] = output_lines
                return {"status": "error", "output": result.stdout}

        except Exception as e:
            print(f"❌ Pylint failed to run: {e}")
            return {"status": "error", "output": str(e)}

    def auto_fix_issues(self) -> None:
        """Automatically fix common issues."""
        print("🔧 Auto-fixing common issues...")

        # Run Black to fix formatting
        print("  - Fixing code formatting with Black...")
        try:
            subprocess.run(
                ["python", "-m", "black", str(self.backend_path)],
                check=True,
                cwd=self.backend_path.parent,
            )
            print("    ✅ Black formatting applied")
        except subprocess.CalledProcessError:
            print("    ❌ Black formatting failed")

        # Run isort to fix imports
        print("  - Fixing import order with isort...")
        try:
            subprocess.run(
                ["python", "-m", "isort", str(self.backend_path)],
                check=True,
                cwd=self.backend_path.parent,
            )
            print("    ✅ Import order fixed")
        except subprocess.CalledProcessError:
            print("    ❌ Import order fix failed")

    def generate_report(self, output_file: Optional[str] = None) -> None:
        """Generate a detailed validation report."""
        print("📊 Generating validation report...")

        total_errors = sum(
            tool["errors"] for tool in self.validation_results.values()
        )
        total_warnings = sum(
            tool["warnings"] for tool in self.validation_results.values()
        )

        report = {
            "summary": {
                "total_errors": total_errors,
                "total_warnings": total_warnings,
                "tools_run": len(self.validation_results),
            },
            "tools": self.validation_results,
            "recommendations": self._generate_recommendations(),
        }

        if output_file:
            with open(output_file, "w") as f:
                json.dump(report, f, indent=2)
            print(f"📄 Report saved to {output_file}")
        else:
            print("\n" + "=" * 60)
            print("VALIDATION REPORT")
            print("=" * 60)
            print(f"Total Errors: {total_errors}")
            print(f"Total Warnings: {total_warnings}")
            print("\nTool Results:")

            for tool_name, results in self.validation_results.items():
                print(f"  {tool_name.upper()}:")
                print(f"    Errors: {results['errors']}")
                print(f"    Warnings: {results['warnings']}")

            print("\nRecommendations:")
            for rec in report["recommendations"]:
                print(f"  - {rec}")

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []

        if self.validation_results["mypy"]["errors"] > 0:
            recommendations.append(
                "Fix MyPy type errors by adding proper type annotations"
            )

        if self.validation_results["flake8"]["errors"] > 0:
            recommendations.append(
                "Fix Flake8 style issues for better code consistency"
            )

        if self.validation_results["black"]["errors"] > 0:
            recommendations.append(
                "Run 'black .' to fix code formatting issues"
            )

        if self.validation_results["isort"]["errors"] > 0:
            recommendations.append("Run 'isort .' to fix import order issues")

        if self.validation_results["pylint"]["errors"] > 0:
            recommendations.append(
                "Address Pylint errors for better code quality"
            )

        if not recommendations:
            recommendations.append(
                "Code quality looks good! Consider adding more comprehensive tests."
            )

        return recommendations

    def run_validation(
        self,
        strict: bool = False,
        fix: bool = False,
        report: bool = False,
        output_file: Optional[str] = None,
    ) -> None:
        """Run complete validation process."""
        print("🛡️ Starting Type Validation Process...")
        print("=" * 60)

        # Run all validation tools
        self.run_mypy(strict=strict)
        self.run_flake8()
        self.run_black_check()
        self.run_isort_check()
        self.run_pylint()

        # Auto-fix if requested
        if fix:
            self.auto_fix_issues()

        # Generate report if requested
        if report:
            self.generate_report(output_file)

        print("=" * 60)
        total_errors = sum(
            tool["errors"] for tool in self.validation_results.values()
        )

        if total_errors == 0:
            print("🎉 All validations passed!")
        else:
            print(
                f"⚠️  Found {total_errors} total issues. Run with --fix to auto-fix some issues."
            )
            sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate types and code quality"
    )
    parser.add_argument(
        "--strict", action="store_true", help="Run strict type checking"
    )
    parser.add_argument(
        "--fix", action="store_true", help="Auto-fix common issues"
    )
    parser.add_argument(
        "--report", action="store_true", help="Generate detailed report"
    )
    parser.add_argument("--output", type=str, help="Output file for report")

    args = parser.parse_args()

    validator = TypeValidator()
    validator.run_validation(
        strict=args.strict,
        fix=args.fix,
        report=args.report,
        output_file=args.output,
    )


if __name__ == "__main__":
    main()
