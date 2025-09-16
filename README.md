# Secure Package Manager

A secure package management system that processes package-lock.json files, validates packages, and manages approval workflows before publishing to secure repositories.

## ✨ Features

- **🔐 Authentication**: ADFS integration with mock IDP for development
- **📦 Package Processing**: Upload and parse package-lock.json files with batch processing
- **🔍 Security Scanning**: Trivy integration for vulnerability detection
- **✅ Validation Pipeline**: Download packages from npm and perform security validations
- **📋 Workflow Management**: Track packages through requested → validated → approved → published states
- **👨‍💼 Admin Interface**: Approve packages and manage the workflow
- **🚀 Secure Publishing**: Publish approved packages to configurable secure repositories
- **📊 License Management**: 4-tier license system (always_allowed, allowed, avoid, blocked) with complex expression support
- **📝 Audit Logging**: Complete audit trail of all actions
- **⚡ High Performance**: Batch processing with license caching for 5-10x performance improvements
- **🔄 Background Workers**: Resilient background processing with automatic retry and stuck package recovery

## 🏗️ Architecture

- **Backend**: Flask API with ADFS authentication and Trivy security scanning
- **Frontend**: React application with Vite and Material-UI
- **Database**: PostgreSQL with role-based access control
- **Security**: Trivy container for vulnerability scanning
- **Background Workers**: Specialized workers for license validation, package processing, and publishing
- **Containerization**: Multi-environment Docker setup (dev/prod)

## 🚀 Quick Start

### Development (Recommended)
```bash
# Windows PowerShell
.\scripts\dev-start.ps1

# Linux/Mac
./scripts/dev-start.sh
```

### Production
```bash
# Copy and configure environment file
cp env.production.example .env.production
# Edit .env.production with your values

# Windows PowerShell
.\scripts\prod-start.ps1

# Linux/Mac
./scripts/prod-start.sh
```

## 🌐 Access Points

### Development
- **Frontend**: http://localhost:3000
- **API**: http://localhost:5000
- **Database**: localhost:5432
- **Mock IDP**: http://localhost:8081
- **Mock NPM Registry**: http://localhost:8080
- **Trivy**: http://localhost:4954

### Production
- **No exposed ports** - Use reverse proxy (nginx/traefik)
- **Internal networking only** - Services communicate via Docker network

## 👥 Default Users (Development)

| Username | Password | Role | Description |
|----------|----------|------|-------------|
| admin | admin | admin | System Administrator |
| approver | admin | approver | Package Approver |
| developer | admin | user | Package Developer |
| tester | admin | user | QA Tester |

## ⚙️ Configuration

### Environment Variables

#### Required for Production
```bash
POSTGRES_PASSWORD=your_secure_password
ADFS_ENTITY_ID=https://your-domain.com
ADFS_SSO_URL=https://your-adfs-server.com/adfs/ls/
```

#### Optional
```bash
SOURCE_REPOSITORY_URL=https://registry.npmjs.org
TARGET_REPOSITORY_URL=https://your-secure-registry.com
FRONTEND_API_URL=https://your-api-domain.com
TRIVY_TIMEOUT=300
TRIVY_MAX_RETRIES=3
```

### Configuration Files
- **`env.development.example`** - Development environment template
- **`env.production.example`** - Production environment template
- **`database/init.sql`** - Production database schema
- **`database/init-dev.sql`** - Development database with seed data

## 🐳 Docker Configuration

### Configuration Files
- **`docker-compose.yml`** - Base production configuration (no mock services)
- **`docker-compose.dev.yml`** - Development overrides (includes mock services)
- **`docker-compose.prod.yml`** - Production optimizations and security

### Scripts
- **`scripts/dev-start.*`** - Start development environment
- **`scripts/dev-stop.*`** - Stop development environment
- **`scripts/dev-reset.*`** - Complete development reset
- **`scripts/prod-start.*`** - Start production environment
- **`scripts/prod-stop.*`** - Stop production environment
- **`scripts/cleanup.*`** - Complete Docker cleanup

### Key Differences

| Feature | Development | Production |
|---------|-------------|------------|
| Mock Services | ✅ Included | ❌ Excluded |
| Source Mounting | ✅ Hot Reload | ❌ No Mounting |
| Port Exposure | ✅ All Ports | ❌ No Ports |
| Database | Dev DB + Seed Data | Production DB |
| Resource Limits | ❌ None | ✅ Configured |
| Restart Policy | Manual | unless-stopped |

## 🗄️ Database Management

### Files
- **`database/init.sql`** - Main production database schema with all tables, indexes, triggers, and default data
- **`database/init-dev.sql`** - Development database initialization (extends init.sql with dev users and sample data)
- **`database/cleanup-dev.sql`** - Development cleanup script (removes package data but keeps users and schema)

### Schema Features
- **Role-based access control** (user, approver, admin)
- **Package validation pipeline** with status tracking
- **Security scanning integration** (Trivy)
- **License management** with 4-tier system (always_allowed, allowed, avoid, blocked)
- **Audit logging** for all actions
- **Repository configuration** management

### Database Access
```bash
# Connect to development database
docker exec -it secure_package_manager-db-1 psql -U postgres -d secure_package_manager_dev

# Connect to production database
docker exec -it secure_package_manager-db-1 psql -U postgres -d secure_package_manager
```

## 🔌 API Endpoints

### Auth Routes (`/api/auth/*`)
- `POST /api/auth/login` - User login
- `GET /api/auth/userinfo` - Get current user information

### Package Routes (`/api/packages/*`)
- `POST /api/packages/upload` - Upload package-lock.json
- `GET /api/packages/requests` - List package requests
- `GET /api/packages/requests/<id>` - Get specific package request
- `GET /api/packages/<id>/security-scan/status` - Get security scan status

### Admin Routes (`/api/admin/*`)
- `GET /api/admin/licenses` - List supported licenses
- `POST /api/admin/licenses` - Create license
- `PUT /api/admin/licenses/<id>` - Update license
- `DELETE /api/admin/licenses/<id>` - Delete license
- `GET /api/admin/config` - Get system configuration

### Approver Routes (`/api/approver/*`)
- `POST /api/approver/packages/batch-approve` - Batch approve packages
- `POST /api/approver/packages/batch-reject` - Batch reject packages
- `POST /api/approver/packages/publish/<id>` - Publish approved package
- `GET /api/approver/packages/validated` - Get validated packages
- `GET /api/approver/packages/pending-approval` - Get packages pending approval

## 🧪 Testing

### Test Files
- **`tests/run_tests.py`** - Test runner for admin API endpoints
- **`tests/test_admin_api.py`** - Admin API test suite
- **`tests/test-mock-registry.js`** - Mock NPM registry tests
- **`tests/test-package-lock.json`** - Test package data

### Running Tests
```bash
# Run admin API tests
python tests/run_tests.py

# Test mock registry (requires registry to be running)
node tests/test-mock-registry.js
```

## 🔄 Background Workers

The system uses specialized background workers for processing packages through the validation pipeline. Each worker is designed for specific tasks and includes automatic retry mechanisms and stuck package recovery.

### Worker Architecture

#### Base Worker (`BaseWorker`)
- **Purpose**: Common functionality for all workers
- **Features**: Signal handling, graceful shutdown, error handling, database connection management
- **Lifecycle**: Initialize → Process Cycle → Cleanup

#### License Worker (`LicenseWorker`)
- **Purpose**: License validation with high-performance batch processing
- **Processing**: Up to 10 packages per cycle (15-second intervals)
- **Features**: 
  - License caching for 5-10x performance improvement
  - Batch database operations
  - Complex license expression support (MIT OR Apache-2.0)
  - Automatic fallback to individual processing
- **Status Tracking**: Requested → Checking Licence → Licence Checked/License Check Failed

#### Package Worker (`PackageWorker`)
- **Purpose**: Complete package validation pipeline
- **Processing**: Up to 5 packages per cycle (10-second intervals)
- **Pipeline**: License Check → Download → Security Scan → Pending Approval
- **Features**: Stuck package recovery (30-minute timeout)

#### Publish Worker (`PublishWorker`)
- **Purpose**: Publishing approved packages to secure repositories
- **Processing**: Up to 3 packages per cycle (30-second intervals)
- **Features**: Long timeout handling (2-hour timeout for publishing operations)

### Performance Optimizations

#### Batch Processing
- **License Validation**: Process multiple packages simultaneously
- **Database Operations**: Bulk updates instead of individual commits
- **License Caching**: In-memory cache with variation support (MIT, mit, MIT License)

#### Complex License Expression Support
- **OR Expressions**: `(MIT OR Apache-2.0)` - Uses best (highest scoring) license
- **AND Expressions**: `(GPL-2.0 AND LGPL-2.1)` - Uses worst (most restrictive) license
- **Nested Parentheses**: `((MIT OR Apache-2.0) AND (GPL-2.0 OR LGPL-2.1))`
- **Edge Cases**: Empty expressions, malformed syntax, unrecognized licenses

### Worker Management
```bash
# Start individual workers
python backend/worker.py --worker license
python backend/worker.py --worker package
python backend/worker.py --worker publish

# Start all workers
python backend/worker.py --worker all
```

## 🏗️ Service Architecture

The backend is organized into specialized services that handle different aspects of the package management system.

### Core Services

#### License Service (`LicenseService`)
- **Purpose**: License validation and management
- **Features**: 
  - 4-tier license system (always_allowed, allowed, avoid, blocked)
  - Complex license expression parsing and validation
  - Batch processing with license caching
  - License variation support (MIT, mit, MIT License, etc.)
- **Performance**: 5-10x improvement through caching and batch operations

#### Package Service (`PackageService`)
- **Purpose**: Package lifecycle management
- **Features**:
  - Package-lock.json parsing and validation
  - Package record creation and management
  - Repository configuration management
  - Asynchronous package processing coordination

#### Package Processor (`PackageProcessor`)
- **Purpose**: Individual package validation pipeline
- **Pipeline**: License Check → Download → Security Scan → Status Update
- **Features**: Error handling, status tracking, validation coordination

#### Package Request Status Manager (`PackageRequestStatusManager`)
- **Purpose**: Request-level status management
- **Features**: 
  - Derives request status from package statuses
  - Calculates completion percentages
  - Provides status summaries for UI

#### Trivy Service (`TrivyService`)
- **Purpose**: Security vulnerability scanning
- **Features**: Container-based scanning, vulnerability reporting, security score calculation

#### Auth Service (`AuthService`)
- **Purpose**: Authentication and authorization
- **Features**: JWT token validation, role-based access control, ADFS integration

### Service Dependencies

```
PackageService
├── LicenseService (batch processing)
├── TrivyService (security scanning)
├── PackageProcessor (validation pipeline)
└── PackageRequestStatusManager (status tracking)

LicenseWorker
└── LicenseService (batch validation)

PackageWorker
├── LicenseService
└── TrivyService

PublishWorker
└── PackageService (publishing)
```

## 📦 Package Processing Pipeline

The system processes packages through a multi-stage validation pipeline with background workers handling each stage.

### Processing Stages

#### 1. Upload & Parsing
- **Trigger**: User uploads package-lock.json
- **Process**: Parse JSON, extract package dependencies
- **Output**: Create Request and Package records with "Requested" status

#### 2. License Validation (License Worker)
- **Input**: Packages with "Requested" status
- **Process**: 
  - Batch license validation (up to 10 packages per cycle)
  - License caching for performance
  - Complex expression parsing (MIT OR Apache-2.0)
- **Output**: "Licence Checked" or "License Check Failed" status

#### 3. Package Processing (Package Worker)
- **Input**: License-validated packages
- **Process**:
  - Package download simulation
  - Security scanning with Trivy
  - Complete validation pipeline
- **Output**: "Pending Approval" status

#### 4. Approval (Manual)
- **Input**: Packages with "Pending Approval" status
- **Process**: Admin/Approver reviews and approves/rejects
- **Output**: "Approved" or "Rejected" status

#### 5. Publishing (Publish Worker)
- **Input**: Approved packages
- **Process**: Publish to secure repository
- **Output**: "Published" status

### Status Flow Diagram

```
Requested → Checking Licence → Licence Checked → Downloaded → Security Scanned → Pending Approval
    ↓              ↓                ↓              ↓              ↓                    ↓
License Check  License Check    Package       Package       Package            Approval
Failed         Failed          Processing    Processing    Processing         (Manual)
    ↓              ↓              ↓              ↓              ↓                    ↓
Rejected      Rejected        Failed        Failed        Failed            Approved/Rejected
                                                                                ↓
                                                                          Publishing
                                                                                ↓
                                                                          Published/Failed
```

### Performance Characteristics

| Stage | Worker | Batch Size | Interval | Timeout | Performance |
|-------|--------|------------|----------|---------|-------------|
| License Check | License Worker | 10 packages | 15s | 15min | 5-10x faster with batching |
| Package Processing | Package Worker | 5 packages | 10s | 30min | Sequential pipeline |
| Publishing | Publish Worker | 3 packages | 30s | 2h | I/O intensive |

## 🎭 Mock Services (Development Only)

### Mock IDP
- **Purpose**: Development authentication service
- **URL**: http://localhost:8081
- **Features**: OAuth2/SAML simulation, user management

### Mock NPM Registry
- **Purpose**: Development package registry
- **URL**: http://localhost:8080
- **Features**: Package publishing, installation, search, metadata storage
- **API Endpoints**:
  - `GET /` - Registry information
  - `GET /health` - Health check
  - `GET /:package` - Get package information
  - `PUT /:package` - Publish package
  - `GET /-/v1/search` - Search packages

## 📁 Project Structure

```
├── backend/                 # Flask API
│   ├── routes/             # API endpoints
│   │   ├── admin_routes.py     # Admin operations (licenses, config)
│   │   ├── approver_routes.py  # Package approval operations
│   │   ├── auth_routes.py      # Authentication endpoints
│   │   └── package_routes.py   # Package upload and management
│   ├── services/           # Business logic
│   │   ├── auth_service.py              # Authentication service
│   │   ├── license_service.py           # License validation with batch processing
│   │   ├── package_service.py           # Package management
│   │   ├── package_processor.py         # Package validation pipeline
│   │   ├── package_request_status_manager.py # Request status management
│   │   ├── trivy_service.py             # Security scanning
│   │   └── validation_service.py        # Input validation
│   ├── workers/            # Background workers
│   │   ├── base_worker.py       # Base worker class
│   │   ├── license_worker.py    # License validation worker (batch processing)
│   │   ├── package_worker.py    # Package processing worker
│   │   └── publish_worker.py    # Package publishing worker
│   ├── config/             # Configuration
│   │   └── constants.py         # Environment constants
│   ├── tests/              # Backend tests
│   ├── models.py           # Database models
│   ├── app.py              # Flask application
│   └── worker.py           # Worker entry point
├── frontend/               # React application
│   ├── src/
│   │   ├── components/     # React components (atoms, molecules, organisms)
│   │   ├── pages/          # Page components
│   │   ├── services/       # API services
│   │   ├── stores/         # State management
│   │   ├── types/          # TypeScript definitions
│   │   └── utils/          # Utility functions
├── database/               # Database scripts
│   ├── init.sql           # Production schema
│   └── init-dev.sql       # Development schema
├── mock-idp/              # Mock authentication service
├── mock-npm-registry/     # Mock package registry
├── scripts/               # Startup scripts
└── docker-compose*.yml    # Docker configurations
```

## 🚀 Recent Improvements

### Performance Enhancements
- **Batch License Processing**: 5-10x performance improvement through license caching and batch database operations
- **Complex License Expressions**: Support for `(MIT OR Apache-2.0)`, `(GPL-2.0 AND LGPL-2.1)`, and nested expressions
- **Background Worker Architecture**: Specialized workers with automatic retry and stuck package recovery
- **Database Optimization**: Bulk updates and single-transaction commits

### Architectural Improvements
- **Service Separation**: Clear separation of concerns with specialized services
- **Worker Resilience**: Automatic fallback mechanisms and error isolation
- **Status Management**: Derived request statuses from package statuses for consistency
- **API Restructuring**: Separated admin and approver endpoints for better organization

### License Management
- **4-Tier System**: always_allowed, allowed, avoid, blocked with scoring
- **Expression Parsing**: Advanced boolean logic for complex license combinations
- **Variation Support**: Handles license variations (MIT, mit, MIT License, etc.)
- **Edge Case Handling**: Robust handling of malformed expressions and unknown licenses

## 🔍 Troubleshooting

### Development Issues
```bash
# Reset everything
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down -v
docker system prune -f
./scripts/dev-start.sh
```

### Production Issues
```bash
# Check logs
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs

# Check service status
docker-compose -f docker-compose.yml -f docker-compose.prod.yml ps
```

### Worker Issues
```bash
# Check worker logs
docker-compose logs worker

# Restart specific worker
docker-compose restart worker

# Check stuck packages
docker exec -it secure_package_manager-db-1 psql -U postgres -d secure_package_manager_dev -c "
SELECT p.name, p.version, ps.status, ps.updated_at 
FROM packages p 
JOIN package_statuses ps ON p.id = ps.package_id 
WHERE ps.updated_at < NOW() - INTERVAL '30 minutes' 
AND ps.status IN ('Checking Licence', 'Processing', 'Publishing');"
```

### Performance Monitoring
```bash
# Check license cache performance
docker exec -it secure_package_manager-backend-1 python -c "
from services.license_service import LicenseService
service = LicenseService()
service._load_license_cache()
print(f'License cache loaded: {len(service._license_cache)} entries')
"

# Monitor batch processing
docker exec -it secure_package_manager-db-1 psql -U postgres -d secure_package_manager_dev -c "
SELECT 
    status,
    COUNT(*) as count,
    MIN(updated_at) as oldest,
    MAX(updated_at) as newest
FROM package_statuses 
GROUP BY status 
ORDER BY count DESC;
"
```

### Manual Docker Commands

#### Development
```bash
# Start with fresh database and mock services
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Stop and clean
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down -v
```

#### Production
```bash
# Start production services (no mock services)
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# View logs
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f
```