# Backend Tests

This directory contains comprehensive test suites for the Secure Package Manager backend services.

## Test Structure

```
backend/tests/
├── README.md                           # This file
├── run_backend_tests.py               # Main test runner for all backend tests
├── __init__.py                        # Test package initialization
├── test_data/                         # Test data files
│   ├── __init__.py
│   └── package_locks/                 # Real package-lock.json files for testing
│       ├── simple_app.json            # Simple app with lodash dependency
│       ├── scoped_packages.json       # App with @angular and @types packages
│       ├── duplicate_packages.json    # App with duplicate package versions
│       ├── invalid_version.json       # Invalid lockfile version (v1)
│       ├── missing_lockfile_version.json # Missing lockfile version
│       └── empty_packages.json        # App with no dependencies
├── services/                          # Service module tests
│   ├── __init__.py
│   ├── test_download_service.py       # DownloadService tests
│   ├── test_license_service.py        # LicenseService unit tests
│   ├── test_license_service_integration.py # LicenseService integration tests
│   ├── test_package_cache_service.py  # PackageCacheService tests
│   └── test_package_lock_parsing_service.py # PackageLockParsingService tests
└── test_scoped_package_parsing.py     # Scoped package parsing tests
```

## Quick Start

### Run All Tests
```bash
cd backend/tests
python run_backend_tests.py
```

### Run Specific Test File
```bash
cd backend/tests
python run_backend_tests.py services/test_download_service.py
```

## Test Categories

### 🔧 Service Tests (`services/`)

**DownloadService Tests** - Test package downloading functionality:
- **`test_download_service.py`** - URL construction, download logic, registry handling

**LicenseService Tests** - Test license validation and processing:
- **`test_license_service.py`** - Unit tests for license processing methods
- **`test_license_service_integration.py`** - Integration tests for license workflows

**PackageCacheService Tests** - Test local package caching:
- **`test_package_cache_service.py`** - Cache storage, retrieval, management

**PackageLockParsingService Tests** - Test package-lock.json parsing:
- **`test_package_lock_parsing_service.py`** - JSON parsing, validation, extraction

### 📄 Package Parsing Tests
- **`test_scoped_package_parsing.py`** - Scoped package name extraction and parsing

## Test Runners

### `run_backend_tests.py`
- **Purpose**: Main test runner for all backend service tests
- **Usage**: `python run_backend_tests.py [test_file]`
- **Features**: 
  - Discovers all `test_*.py` files
  - Can run specific test files
  - Verbose output with pass/fail summary

## Development Workflow

### For Service Development:
1. **Run All Tests**: `python run_backend_tests.py`
2. **Run Specific Service**: `python run_backend_tests.py services/test_<service_name>.py`

## Test Requirements

### Environment Setup Required
- **Database URL**: Tests require `DATABASE_URL` environment variable
- **Dependencies**: All service dependencies must be available
- **Test Data**: Uses real package-lock.json files for testing

### Test Data
- Tests use realistic package-lock.json structures from `test_data/package_locks/`
- Covers various scenarios: simple apps, scoped packages, edge cases

## Best Practices

1. **Service Focus**: Tests focus on service functionality rather than worker orchestration
2. **Test Coverage**: Each service has comprehensive test coverage
3. **Isolation**: Tests are independent and don't rely on external state
4. **Realistic Data**: Tests use realistic package-lock.json structures
5. **Error Scenarios**: Both happy path and error conditions are tested

## Adding New Tests

### For Service Modules:
1. Create test file in `services/` directory
2. Follow naming convention: `test_<service_name>.py`
3. Use `Test<ServiceClassName>` for test classes
4. Tests will be automatically discovered by `run_backend_tests.py`

## Troubleshooting

### Environment Issues:
- Set `DATABASE_URL` environment variable (e.g., `sqlite:///./test.db`)
- Ensure all service dependencies are installed
- Check that required environment variables are set

### Import Issues:
- Tests require proper Python path configuration
- Services must be importable from the backend directory
- Check that all dependencies are installed

## Test Results

### Current Status:
- Service tests require proper environment setup
- Tests focus on core service functionality
- Database configuration needed for full test execution

### Coverage:
- **DownloadService**: URL construction, registry handling, download logic
- **LicenseService**: License validation, processing, complex expressions
- **PackageCacheService**: Cache operations, storage, retrieval
- **PackageLockParsingService**: JSON parsing, validation, package extraction
- **Package Parsing**: Scoped packages, edge cases, name extraction