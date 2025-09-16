# Secure Package Manager

A secure package management system that processes package-lock.json files, validates packages, and manages approval workflows before publishing to secure repositories.

## ✨ Features

- **🔐 Authentication**: ADFS integration with mock IDP for development
- **📦 Package Processing**: Upload and parse package-lock.json files
- **🔍 Security Scanning**: Trivy integration for vulnerability detection
- **✅ Validation Pipeline**: Download packages from npm and perform security validations
- **📋 Workflow Management**: Track packages through requested → validated → approved → published states
- **👨‍💼 Admin Interface**: Approve packages and manage the workflow
- **🚀 Secure Publishing**: Publish approved packages to configurable secure repositories
- **📊 License Management**: 4-tier license system (always_allowed, allowed, avoid, blocked)
- **📝 Audit Logging**: Complete audit trail of all actions

## 🏗️ Architecture

- **Backend**: Flask API with ADFS authentication and Trivy security scanning
- **Frontend**: React application with Vite and Material-UI
- **Database**: PostgreSQL with role-based access control
- **Security**: Trivy container for vulnerability scanning
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

### Admin Routes (`/api/admin/*`)
- `GET /api/admin/packages/validated` - Get validated packages
- `POST /api/admin/packages/approve/<id>` - Approve package
- `POST /api/admin/packages/publish/<id>` - Publish package
- `GET /api/admin/licenses` - List supported licenses
- `POST /api/admin/licenses` - Create license
- `PUT /api/admin/licenses/<id>` - Update license
- `DELETE /api/admin/licenses/<id>` - Delete license

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
│   ├── services/           # Business logic
│   └── models.py           # Database models
├── frontend/               # React application
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── pages/          # Page components
│   │   └── services/       # API services
├── database/               # Database scripts
│   ├── init.sql           # Production schema
│   └── init-dev.sql       # Development schema
├── mock-idp/              # Mock authentication service
├── mock-npm-registry/     # Mock package registry
├── scripts/               # Startup scripts
└── docker-compose*.yml    # Docker configurations
```

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