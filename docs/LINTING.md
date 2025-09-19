# Code Quality and Linting Guide

This document explains how to maintain code quality and PEP 8 compliance in the Secure Package Manager project.

## Overview

We use several tools to ensure code quality:

- **flake8**: PEP 8 style guide enforcement
- **black**: Automatic code formatting
- **isort**: Import statement organization
- **mypy**: Static type checking
- **eslint**: TypeScript/JavaScript linting (frontend)

## Quick Start

### Check All Code Quality Issues
```bash
# Using the provided scripts
./scripts/lint.sh          # Linux/macOS
.\scripts\lint.ps1         # Windows PowerShell

# Or using npm (from frontend directory)
npm run python:all
```

### Fix Formatting Issues Automatically
```bash
# Using the provided scripts with fix flag
.\scripts\lint.ps1 -Fix    # Windows PowerShell

# Or manually
isort backend/ config/ tests/
black backend/ config/ tests/
```

## Individual Tools

### flake8 (PEP 8 Compliance)
```bash
flake8 backend/ config/ tests/
```

**Configuration**: `.flake8`
- Max line length: 88 characters
- Ignores conflicts with black formatter
- Excludes migrations and build directories

### black (Code Formatting)
```bash
black backend/ config/ tests/
black --check backend/ config/ tests/  # Check only
```

**Configuration**: `pyproject.toml`
- Line length: 88 characters
- Target Python versions: 3.8+
- Excludes migrations and build directories

### isort (Import Organization)
```bash
isort backend/ config/ tests/
isort --check-only backend/ config/ tests/  # Check only
```

**Configuration**: `pyproject.toml`
- Profile: "black" (compatible with black formatter)
- Multi-line output with trailing commas

### mypy (Type Checking)
```bash
mypy backend/ config/
```

**Configuration**: `pyproject.toml`
- Strict type checking enabled
- Ignores missing imports for third-party libraries

## Frontend Linting

### ESLint (TypeScript/JavaScript)
```bash
cd frontend
npm run lint        # Check for issues
npm run lint:fix    # Fix auto-fixable issues
```

## Pre-commit Hooks (Recommended)

To automatically run linting before commits, install pre-commit:

```bash
pip install pre-commit
pre-commit install
```

Create `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.11.0
    hooks:
      - id: black
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
  - repo: https://github.com/pycqa/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
```

## CI/CD Integration

Add to your CI pipeline:
```yaml
- name: Run Python linting
  run: |
    pip install flake8 black isort mypy
    isort --check-only backend/ config/ tests/
    black --check backend/ config/ tests/
    flake8 backend/ config/ tests/
    mypy backend/ config/
```

## Common Issues and Solutions

### Line Too Long (E501)
- **Solution**: Let black handle line length automatically
- **Manual fix**: Break long lines at logical points

### Import Order Issues
- **Solution**: Run `isort backend/ config/ tests/`
- **Manual fix**: Group imports: stdlib, third-party, local

### Type Checking Errors
- **Solution**: Add type hints to function parameters and return values
- **Example**: `def process_package(package: Package) -> bool:`

### Unused Imports (F401)
- **Solution**: Remove unused imports
- **Exception**: `__init__.py` files may have unused imports for exports

## Configuration Files

- `.flake8`: flake8 configuration
- `pyproject.toml`: black, isort, mypy, and pytest configuration
- `frontend/package.json`: ESLint configuration and scripts

## IDE Integration

### VS Code
Install extensions:
- Python
- Pylance
- Black Formatter
- isort

Add to `.vscode/settings.json`:
```json
{
  "python.formatting.provider": "black",
  "python.sortImports.args": ["--profile", "black"],
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.mypyEnabled": true
}
```

### PyCharm
- Enable black as external tool
- Configure flake8 as external tool
- Enable mypy integration

## Troubleshooting

### "No module named 'flake8'"
```bash
pip install -r backend/requirements.txt
```

### "Permission denied" on scripts
```bash
chmod +x scripts/lint.sh  # Linux/macOS
```

### Black and flake8 conflicts
- Use the provided `.flake8` configuration
- It ignores conflicts between black and flake8

### Type checking errors with third-party libraries
- These are ignored in `pyproject.toml` under `[tool.mypy.overrides]`
- Add new libraries to the ignore list if needed
