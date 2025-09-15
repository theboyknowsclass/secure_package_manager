#!/bin/bash

# Lint script for Secure Package Manager
# This script runs all linting tools to ensure PEP 8 compliance

set -e

echo "🔍 Running Python linting tools..."

# Change to project root
cd "$(dirname "$0")/.."

# Check if we're in a virtual environment
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  Warning: No virtual environment detected. Consider using one for better dependency management."
fi

# Install linting tools if not already installed
echo "📦 Installing/updating linting tools..."
pip install -q flake8 black isort mypy

# Run isort to check import ordering
echo "📋 Checking import order with isort..."
isort --check-only --diff backend/ tests/ || {
    echo "❌ Import order issues found. Run 'isort backend/ tests/' to fix."
    exit 1
}

# Run black to check code formatting
echo "🎨 Checking code formatting with black..."
black --check --diff backend/ tests/ || {
    echo "❌ Code formatting issues found. Run 'black backend/ tests/' to fix."
    exit 1
}

# Run flake8 for PEP 8 compliance
echo "🔍 Checking PEP 8 compliance with flake8..."
flake8 backend/ tests/ || {
    echo "❌ PEP 8 violations found. See output above for details."
    exit 1
}

# Run mypy for type checking
echo "🔬 Running type checking with mypy..."
mypy backend/ || {
    echo "❌ Type checking issues found. See output above for details."
    exit 1
}

echo "✅ All linting checks passed!"
echo ""
echo "💡 To automatically fix formatting issues, run:"
echo "   isort backend/ tests/"
echo "   black backend/ tests/"
