<!--
Sync Impact Report:
Version change: 1.0.0 → 1.1.0 (major update)
Modified principles: Added Latest Stable Versions, Code Quality and Linting Standards
Added sections: Frontend Development Standards, Backend Development Standards, Enhanced Quality Assurance
Removed sections: N/A
Templates requiring updates:
  ✅ .specify/templates/plan-template.md - Constitution Check section updated
  ✅ .specify/templates/spec-template.md - Security requirements added
  ✅ .specify/templates/tasks-template.md - TDD and security testing tasks added
Follow-up TODOs: Update plan templates to include new linting and version requirements
-->

# Secure Package Manager Constitution

## Core Principles

### I. Security-First Architecture (NON-NEGOTIABLE)
Every component MUST be designed with security as the primary concern. All code, configurations, and deployments MUST follow security best practices from day one. No security shortcuts or "we'll fix it later" approaches are acceptable. This includes input validation, authentication, authorization, data encryption, secure communication, and vulnerability management.

### II. Production-Ready Development (NON-NEGOTIABLE)
All code MUST be production-ready from the first commit. No dummy services, hardcoded test data, or development-only code in production paths. Use mock containers for development (mock-idp, mock-npm-registry) but ensure code works in production with only configuration changes. All services MUST be containerized and configurable via environment variables.

### III. Test-Driven Development (NON-NEGOTIABLE)
TDD is mandatory: Tests written → User approved → Tests fail → Then implement. Red-Green-Refactor cycle strictly enforced. All features MUST have comprehensive test coverage including unit tests, integration tests, and security tests. No code goes to production without passing all tests.

### IV. SOLID and DRY Principles
Code MUST follow SOLID principles (Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion) and DRY (Don't Repeat Yourself) where possible. Complex code MUST be justified with clear documentation of why simpler alternatives were insufficient.

### V. Container-First Architecture
All components MUST be fully dockerized with multi-environment support (dev/prod). No local development dependencies outside containers. Use Docker Compose for orchestration with proper separation of concerns and environment-specific configurations.

### VI. Accessibility and UX Standards
User interfaces MUST use commonplace UI libraries with minimal custom code. All interfaces MUST meet WCAG AA accessibility standards. Focus on usability, responsive design, and inclusive user experience. No custom UI components without strong justification.

### VII. Latest Stable Versions (NON-NEGOTIABLE)
All dependencies MUST use the latest stable versions available. This includes Python, Node.js, React, Flask, and all other libraries. Regular updates are mandatory to ensure security, performance, and access to latest features. No outdated dependencies are acceptable in production.

### VIII. Code Quality and Linting Standards (NON-NEGOTIABLE)
All code MUST follow established linting and formatting standards. Python code MUST follow PEP8 standards with Black for formatting and flake8 for linting. JavaScript/TypeScript code MUST use ESLint and Prettier for consistent formatting. All code MUST be automatically formatted and linted before commits.

## Security Requirements

### Authentication and Authorization
- ADFS integration for production authentication
- Role-based access control (user, approver, admin)
- JWT token management with proper expiration
- No hardcoded credentials or secrets
- All API endpoints MUST be protected

### Data Protection
- All sensitive data MUST be encrypted at rest and in transit
- Input validation and sanitization on all user inputs
- SQL injection protection through parameterized queries
- XSS protection in all user-facing interfaces
- Audit logging for all security-relevant actions

### Vulnerability Management
- Trivy integration for container and dependency scanning
- Regular security updates and dependency management
- No known vulnerabilities in production dependencies
- Security scanning in CI/CD pipeline

## Production Readiness Standards

### Performance and Scalability
- Background worker architecture for processing
- Batch processing for performance optimization
- Database connection pooling and optimization
- Resource limits and monitoring in production
- Graceful degradation under load

### Monitoring and Observability
- Comprehensive logging with structured format
- Health check endpoints for all services
- Performance metrics and monitoring
- Error tracking and alerting
- Audit trail for all operations

### Deployment and Operations
- Zero-downtime deployment capability
- Environment-specific configurations
- Database migration strategy (init scripts approach)
- Backup and recovery procedures
- Disaster recovery planning

## Quality Assurance

### Testing Standards
- Unit tests for all business logic
- Integration tests for API endpoints
- Contract tests for service interfaces
- Security tests for authentication and authorization
- Performance tests for critical paths
- End-to-end tests for user workflows
- **Accessibility tests**: Automated WCAG AA compliance testing with axe-core
- **Component testing**: Storybook for isolated component development and visual regression testing

### Code Quality and Linting
- **Python**: PEP8 compliance with Black formatting and flake8 linting
- **JavaScript/TypeScript**: ESLint and Prettier for consistent formatting
- **Automated formatting**: All code MUST be automatically formatted before commits
- Code review requirements for all changes
- Static analysis and security scanning
- Documentation requirements for complex logic
- Performance profiling for optimization

### Documentation Standards
- All documentation MUST reflect the CURRENT state
- NO historical information or change logs in documentation
- README files describe what the system does NOW
- Inline code comments explain current functionality
- Remove outdated documentation immediately when making changes

## Frontend Development Standards

### Component Development
- **Storybook**: All UI components MUST have Storybook stories for isolated development and testing
- **Co-location**: Tests and stories MUST be co-located with their components
- **Accessibility**: All components MUST pass automated accessibility testing with axe-core
- **Responsive Design**: All components MUST be responsive and mobile-friendly

### State Management
- **Zustand**: Use Zustand for global state management (simple, performant)
- **Local State**: Use React hooks for component-local state
- **No Redux**: Avoid Redux complexity unless absolutely necessary

### API Integration
- **MSW**: Use Mock Service Worker for API mocking in development and tests
- **Co-located Mocks**: Mock files MUST be co-located with their corresponding services
- **Type Safety**: All API calls MUST be fully typed with TypeScript

### Build and Development
- **Vite**: Use Vite for fast development and optimized builds
- **Latest React**: Always use the latest stable version of React
- **TypeScript**: All frontend code MUST be written in TypeScript

## Backend Development Standards

### Code Quality
- **PEP8**: All Python code MUST follow PEP8 standards
- **Black**: Use Black for automatic code formatting
- **flake8**: Use flake8 for linting and style checking
- **isort**: Use isort for import organization
- **mypy**: Use mypy for static type checking

### Testing Organization
- **Mirror Structure**: Tests MUST mirror source structure under `tests/` folder
- **Co-location**: Test files MUST be in corresponding `tests/` subdirectories
- **pytest**: Use pytest for all Python testing
- **Coverage**: Maintain high test coverage for all business logic

### API Development
- **Flask**: Use latest stable Flask version
- **Type Hints**: All Python functions MUST have proper type hints
- **Documentation**: All API endpoints MUST be documented with OpenAPI/Swagger
- **Validation**: All inputs MUST be validated and sanitized

### Database
- **SQLAlchemy**: Use latest stable SQLAlchemy version
- **Migrations**: Use init scripts approach (no migration files)
- **Connection Pooling**: Implement proper database connection pooling
- **Transactions**: Use proper transaction management

## Development Workflow

### Git and Version Control
- Feature branch workflow with pull requests
- Meaningful commit messages with conventional format
- No direct commits to main branch
- Automated testing on all pull requests
- Security scanning in CI/CD pipeline

### Environment Management
- Clear separation between development and production
- Mock services for development (mock-idp, mock-npm-registry)
- Environment-specific Docker configurations
- No production secrets in development code
- Configuration via environment variables only

### Service Management
- Use PowerShell scripts (.ps1) on Windows and shell scripts (.sh) on *nix
- Default to using scripts for starting, stopping, and managing services
- Scripts handle both development and production environments
- No manual Docker commands in production

## Governance

This constitution supersedes all other practices and MUST be followed by all team members. Amendments require:
- Documentation of the change and rationale
- Approval from project maintainers
- Migration plan for existing code
- Update to all dependent templates and documentation

All pull requests and code reviews MUST verify compliance with this constitution. Complexity MUST be justified with clear documentation. Use the project README and documentation for runtime development guidance.

**Version**: 1.1.0 | **Ratified**: 2025-01-27 | **Last Amended**: 2024-12-19