# Secure Package Manager - Backend

A Flask-based backend service for secure package management with background workers for processing package requests through a multi-stage pipeline.

## 🏗️ Architecture Overview

The backend follows a modular architecture with clear separation of concerns:

- **API Layer**: Flask REST API with role-based authentication
- **Service Layer**: Business logic and external service integrations  
- **Database Layer**: SQLAlchemy models with both Flask-SQLAlchemy and pure SQLAlchemy support
- **Worker Layer**: Background workers for asynchronous package processing
- **Configuration**: Environment-based configuration management

## 📁 Folder Structure

```
backend/
├── app.py                          # Main Flask application entry point
├── worker.py                       # Background worker entry point
├── requirements.txt                # Python dependencies
├── Dockerfile                      # Main API container
├── Dockerfile.worker               # Worker container
│
├── config/                         # Configuration management
│   ├── __init__.py
│   └── constants.py                # Environment variables and constants
│
├── database/                       # Database layer
│   ├── __init__.py                 # Flask-SQLAlchemy setup
│   ├── models.py                   # Pure SQLAlchemy models
│   ├── service.py                  # Database service (pure SQLAlchemy)
│   ├── operations.py               # Shared database operations
│   ├── example_usage.py            # Usage examples
│   └── models/                     # Individual model files
│       ├── user.py                 # User model
│       ├── package.py              # Package model
│       ├── request.py              # Package request model
│       ├── package_status.py       # Package status tracking
│       ├── security_scan.py        # Security scan results
│       ├── supported_license.py    # License management
│       ├── audit_log.py            # Audit logging
│       └── request_package.py      # Request-package relationships
│
├── routes/                         # API endpoints
│   ├── __init__.py
│   ├── auth_routes.py              # Authentication endpoints
│   ├── package_routes.py           # Package management endpoints
│   ├── admin_routes.py             # Admin-only endpoints
│   └── approver_routes.py          # Package approval endpoints
│
├── services/                       # Business logic layer
│   ├── __init__.py
│   ├── auth_service.py             # Authentication & authorization
│   ├── package_service.py          # Package management logic
│   ├── license_service.py          # License validation
│   ├── trivy_service.py            # Security scanning integration
│   ├── download_service.py         # Package downloading
│   ├── validation_service.py       # Input validation
│   ├── package_request_status_manager.py  # Status management
│   └── queue_interface.py          # Queue management
│
├── workers/                        # Background workers
│   ├── __init__.py
│   ├── base_worker.py              # Base worker class
│   ├── parse_worker.py             # Package parsing
│   ├── license_worker.py           # License checking
│   ├── download_worker.py          # Package downloading
│   ├── security_worker.py          # Security scanning
│   ├── approval_worker.py          # Package approval
│   └── publish_worker.py           # Package publishing
│
├── tests/                          # Test suite
│   ├── __init__.py
│   ├── README.md                   # Test documentation
│   ├── run_backend_tests.py        # API tests runner
│   ├── run_worker_tests.py         # Worker tests runner
│   ├── test_license_integration.py # License service tests
│   ├── test_license_service.py     # License validation tests
│   ├── test_npm_license_formats.py # NPM license format tests
│   ├── test_scoped_package_parsing.py # Scoped package tests
│   ├── test_data/                  # Test data files
│   │   └── package_locks/          # Sample package-lock.json files
│   └── workers/                    # Worker-specific tests
│       └── test_parse_worker.py    # Parse worker tests
│
├── certs/                          # SSL certificates
└── package_cache/                  # Local package cache
```

## 🔄 Package Processing Pipeline

The system processes package requests through a multi-stage pipeline using background workers:

```
Package Request → Parse → License Check → Download → Security Scan → Approval → Publish
     ↓              ↓           ↓            ↓            ↓           ↓         ↓
parse-worker → license-worker → download-worker → security-worker → approval-worker → publish-worker
```

### Worker Details

| Worker | Purpose | Input Status | Output Status | Key Features |
|--------|---------|--------------|---------------|--------------|
| **parse-worker** | Parse package-lock.json | `Submitted` | `Parsed` | Validates JSON, extracts dependencies |
| **license-worker** | Validate licenses | `Parsed` | `License Checked` | Checks against allowed licenses |
| **download-worker** | Download packages | `License Checked` | `Downloaded` | Downloads from source registry |
| **security-worker** | Security scanning | `Downloaded` | `Security Scanned` | Trivy vulnerability scanning |
| **approval-worker** | Manual approval | `Security Scanned` | `Pending Approval` | Transitions to approval queue |
| **publish-worker** | Publish to secure repo | `Approved` | `Published` | Publishes to target registry |

## 🐳 Docker Services

The backend runs in multiple Docker containers:

### Core Services
- **`api`** - Main Flask API server
- **`db`** - PostgreSQL database

### Background Workers
- **`parse-worker`** - Package parsing service
- **`license-worker`** - License validation service  
- **`download-worker`** - Package downloading service
- **`security-worker`** - Security scanning service
- **`approval-worker`** - Package approval service
- **`publish-worker`** - Package publishing service

### External Services
- **`trivy`** - Security vulnerability scanner

### Development Services
- **`mock-idp`** - Mock identity provider
- **`mock-npm-registry`** - Mock NPM registry
- **`pgadmin`** - Database management UI
- **`portainer`** - Docker management UI

## 🚀 Getting Started

### Prerequisites
- Docker and Docker Compose
- Python 3.11+ (for local development)
- PostgreSQL (for local development)

### Environment Setup
1. Copy `example.env.development` to `.env`
2. Update environment variables as needed
3. Ensure all required services are configured

### Running with Docker

#### Development
```bash
# Start all services (including development tools)
docker compose -f docker-compose.base.yml -f docker-compose.dev.yml up

# Start only core services
docker compose -f docker-compose.base.yml up
```

#### Production
```bash
docker compose -f docker-compose.base.yml -f docker-compose.prod.yml up
```

### Local Development

#### Backend API
```bash
cd backend
pip install -r requirements.txt
python app.py
```

#### Background Workers
```bash
cd backend
export WORKER_TYPE=parse_worker  # or license_worker, download_worker, etc.
python worker.py
```

## 🔧 Configuration

### Environment Variables

#### Core Configuration
- `DATABASE_URL` - Database connection string
- `JWT_SECRET` - JWT signing secret
- `FLASK_SECRET_KEY` - Flask session secret
- `FLASK_ENV` - Environment (development/production)
- `FLASK_DEBUG` - Debug mode (0/1)

#### External Services
- `TRIVY_URL` - Trivy security scanner URL
- `SOURCE_REPOSITORY_URL` - Source NPM registry
- `TARGET_REPOSITORY_URL` - Target secure registry

#### Worker Configuration
- `WORKER_TYPE` - Type of worker to run
- `WORKER_SLEEP_INTERVAL` - Worker polling interval
- `WORKER_MAX_PACKAGES_PER_CYCLE` - Batch size per cycle

## 🧪 Testing

### Run All Tests
```bash
cd backend
python -m pytest tests/
```

### Run Specific Test Suites
```bash
# API tests
python tests/run_backend_tests.py

# Worker tests  
python tests/run_worker_tests.py

# License service tests
python -m pytest tests/test_license_service.py -v
```

### Test Coverage
```bash
pip install coverage
coverage run -m pytest tests/
coverage report
coverage html  # Generates HTML report
```

## 📊 Monitoring & Logging

### Logs
- **API Logs**: Available in container logs
- **Worker Logs**: Stored in `/app/logs/worker.log`
- **Database Logs**: PostgreSQL logs in container

### Health Checks
All services include health checks:
- **API**: HTTP endpoint health check
- **Workers**: Python import validation
- **Database**: PostgreSQL connection check
- **Trivy**: Version command check

### Metrics
- Package processing statistics via API endpoints
- Worker status and performance metrics
- Database connection and query metrics

## 🔒 Security Features

- **JWT Authentication**: Secure token-based authentication
- **Role-Based Access Control**: Admin, Approver, User roles
- **Input Validation**: Comprehensive request validation
- **SQL Injection Protection**: SQLAlchemy ORM protection
- **Security Scanning**: Trivy vulnerability scanning
- **Audit Logging**: Complete audit trail of actions

## 🛠️ Development

### Code Quality
- **Linting**: flake8, black, isort
- **Type Checking**: mypy
- **Testing**: pytest with comprehensive coverage

### Adding New Workers
1. Create worker class inheriting from `BaseWorker`
2. Implement required methods (`process_cycle`, `initialize`)
3. Add to worker registry in `worker.py`
4. Add Docker service configuration
5. Add tests

### Database Migrations
- Use SQLAlchemy migrations for schema changes
- Update both Flask-SQLAlchemy and pure SQLAlchemy models
- Test migrations in development environment

## 📚 API Documentation

### Authentication
- **POST** `/api/auth/login` - User login
- **POST** `/api/auth/oauth2/callback` - OAuth2 callback
- **GET** `/api/auth/me` - Current user info

### Package Management
- **POST** `/api/packages/requests` - Submit package request
- **GET** `/api/packages/requests` - List package requests
- **GET** `/api/packages/requests/{id}` - Get request details
- **PUT** `/api/packages/requests/{id}/approve` - Approve request
- **PUT** `/api/packages/requests/{id}/reject` - Reject request

### Admin Operations
- **GET** `/api/admin/stats` - System statistics
- **GET** `/api/admin/workers` - Worker status
- **POST** `/api/admin/workers/{type}/restart` - Restart worker

## 🤝 Contributing

1. Follow the existing code structure and patterns
2. Add comprehensive tests for new features
3. Update documentation for API changes
4. Ensure all linting checks pass
5. Test with both development and production configurations

## 📄 License

This project is part of the Secure Package Manager system. See the main project README for license information.
