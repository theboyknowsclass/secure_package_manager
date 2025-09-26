#!/bin/bash
# Linting script for the secure package manager backend

echo "Running linting checks..."

# Change to backend directory
cd backend

# Run flake8 for syntax and style checking
echo "Running flake8..."
python -m flake8 . --max-line-length=130 --extend-ignore=E203,W503

if [ $? -ne 0 ]; then
    echo "Flake8 found issues!"
    flake8_failed=true
else
    echo "Flake8 passed!"
fi

# Run black for code formatting check
echo "Running black (format check)..."
python -m black --check --diff .

if [ $? -ne 0 ]; then
    echo "Black found formatting issues!"
    black_failed=true
else
    echo "Black formatting is correct!"
fi

# Run isort for import sorting check
echo "Running isort (import check)..."
python -m isort --check-only --diff .

if [ $? -ne 0 ]; then
    echo "isort found import issues!"
    isort_failed=true
else
    echo "isort imports are correct!"
fi

# Run mypy for type checking
echo "Running mypy..."
python -m mypy .

if [ $? -ne 0 ]; then
    echo "mypy found type issues!"
    mypy_failed=true
else
    echo "mypy type checking passed!"
fi

# Check for multi-line f-string issues (custom check)
echo "Checking for multi-line f-string issues..."
fstring_issues=$(find . -name "*.py" -exec grep -l 'f"[^"]*{[^}]*[[:space:]]*$' {} \; 2>/dev/null | xargs -I {} sh -c 'if grep -q "f\".*{[^}]*[[:space:]]*$" "{}" && grep -A1 "f\".*{[^}]*[[:space:]]*$" "{}" | grep -q "}"; then echo "{}"; fi')

if [ -n "$fstring_issues" ]; then
    echo "Found multi-line f-string issues in:"
    echo "$fstring_issues"
    fstring_failed=true
else
    echo "No multi-line f-string issues found!"
fi

# Return to original directory
cd ..

# Summary
echo ""
echo "Linting Summary:"
if [ "$flake8_failed" = true ] || [ "$black_failed" = true ] || [ "$isort_failed" = true ] || [ "$mypy_failed" = true ] || [ "$fstring_failed" = true ]; then
    echo "❌ Some linting checks failed!"
    echo "Run 'scripts/fix.sh' to automatically fix formatting issues."
    exit 1
else
    echo "✅ All linting checks passed!"
    exit 0
fi
