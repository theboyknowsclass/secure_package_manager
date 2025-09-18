# Backend Tests

This directory contains comprehensive test suites for the Secure Package Manager backend.

## Test Structure

```
backend/tests/
├── README.md                           # This file
├── run_backend_tests.py               # Main test runner for all backend tests
├── run_worker_tests.py                # Worker-specific test runner
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
├── workers/                           # Worker module unit tests
│   ├── __init__.py
│   └── test_parse_worker.py           # ✅ ParseWorker unit tests (12 tests)
├── test_license_service.py            # License service tests
├── test_license_integration.py        # License integration tests
├── test_npm_license_formats.py        # NPM license format tests
└── test_scoped_package_parsing.py     # Scoped package parsing tests
```

## Quick Start

### Run All Tests
```bash
cd backend/tests
python run_backend_tests.py
```

### Run Worker Unit Tests Only
```bash
cd backend/tests
python run_worker_tests.py
```

### Run Specific Test File
```bash
cd backend/tests
python run_backend_tests.py workers/test_parse_worker_standalone.py
```

## Test Categories

### 🚀 Worker Tests (`workers/`)

**ParseWorker Tests** - Test package-lock.json parsing and validation:

- **`test_parse_worker.py`** ✅ **12 passing tests**
  - **Validation Tests**: package-lock.json validation logic using real files
  - **Extraction Tests**: Package extraction from JSON using real files
  - **Name Parsing Tests**: Package name extraction from paths using real files
  - **Edge Cases**: Tests invalid versions, missing fields, empty packages
  - **Real Scenarios**: Tests scoped packages, duplicate packages, complex structures
  - **No Dependencies**: Runs without Flask app setup
  - **Real Data**: Uses actual package-lock.json files from `test_data/package_locks/`

**Usage:**
```bash
# Run all worker unit tests (fast, no dependencies)
python run_worker_tests.py
```

### 📄 License Tests

- **`test_license_service.py`** - License validation service tests
- **`test_license_integration.py`** - License integration tests  
- **`test_npm_license_formats.py`** - NPM license format parsing tests
- **`test_scoped_package_parsing.py`** - Scoped package parsing tests

## Test Runners

### `run_backend_tests.py`
- **Purpose**: Main test runner for all backend tests
- **Usage**: `python run_backend_tests.py [test_file]`
- **Features**: 
  - Discovers all `test_*.py` files
  - Can run specific test files
  - Verbose output with pass/fail summary

### `run_worker_tests.py`
- **Purpose**: Worker unit test runner
- **Usage**: `python run_worker_tests.py` - Run all worker unit tests
- **Features**:
  - Focused on worker module unit tests
  - Fast execution with no dependencies
  - No environment setup required

## Development Workflow

### For ParseWorker Development:
1. **Unit Testing**: `python run_worker_tests.py` (fast, no dependencies)
2. **All Tests**: `python run_backend_tests.py`

### For License Service Development:
1. **License Tests**: `python run_backend_tests.py test_license_service.py`
2. **All Tests**: `python run_backend_tests.py`

## Test Requirements

### Unit Tests (No Setup Required)
- ✅ `test_parse_worker.py` - 12 tests
- Pure unit tests with no external dependencies
- Fast execution, perfect for development
- Use real package-lock.json files for testing

### Other Tests (May Require Setup)
- License service tests
- NPM license format tests
- Scoped package parsing tests

## Best Practices

1. **Start with Unit Tests**: Use `python run_worker_tests.py` for quick development feedback
2. **Test Coverage**: Each module has comprehensive test coverage
3. **Isolation**: Tests are independent and don't rely on external state
4. **Realistic Data**: Tests use realistic package-lock.json structures
5. **Error Scenarios**: Both happy path and error conditions are tested

## Adding New Tests

### For Worker Modules:
1. Create test file in `workers/` directory
2. Follow naming convention: `test_<module_name>.py`
3. Use `Test<ClassName>` for test classes
4. Add to `run_worker_tests.py` if needed

### For Other Modules:
1. Create test file in root `tests/` directory
2. Follow same naming conventions
3. Tests will be automatically discovered by `run_backend_tests.py`

## Troubleshooting

### Environment Issues:
- Worker unit tests require no environment setup
- Check that all required environment variables are set for other tests
- Ensure database is running for integration tests

### Import Issues:
- Unit tests don't require Flask app setup
- Other tests require proper Python path configuration
- Check that all dependencies are installed

## Test Results

### Current Status:
- ✅ **12/12** ParseWorker unit tests passing
- ✅ License service tests passing
- ✅ NPM license format tests passing
- ✅ Scoped package parsing tests passing

### Coverage:
- **ParseWorker**: Validation, extraction, name parsing, integration scenarios
- **License Service**: Various license formats, complex expressions
- **Package Parsing**: Scoped packages, edge cases
- **Integration**: End-to-end workflows