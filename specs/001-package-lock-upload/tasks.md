# Tasks: Package Lock Upload

**Input**: Design documents from `/specs/001-package-lock-upload/`
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/

## Execution Flow (main)
```
1. Load plan.md from feature directory
   → If not found: ERROR "No implementation plan found"
   → Extract: tech stack, libraries, structure
2. Load optional design documents:
   → data-model.md: Extract entities → model tasks
   → contracts/: Each file → contract test task
   → research.md: Extract decisions → setup tasks
3. Generate tasks by category:
   → Setup: project init, dependencies, linting
   → Tests: contract tests, integration tests
   → Core: models, services, CLI commands
   → Integration: DB, middleware, logging
   → Polish: unit tests, performance, docs
4. Apply task rules:
   → Different files = mark [P] for parallel
   → Same file = sequential (no [P])
   → Tests before implementation (TDD)
5. Number tasks sequentially (T001, T002...)
6. Generate dependency graph
7. Create parallel execution examples
8. Validate task completeness:
   → All contracts have tests?
   → All entities have models?
   → All endpoints implemented?
9. Return: SUCCESS (tasks ready for execution)
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions
- **Web app**: `backend/`, `frontend/` at repository root
- **Backend**: `backend/routes/`, `backend/services/`, `backend/database/`
- **Frontend**: `frontend/src/`, `frontend/.storybook/`
- Paths shown below based on plan.md structure

## Phase 3.1: Setup
- [ ] T001 [P] Upgrade frontend dependencies to React 19.1.1, Node.js 20.x LTS, Vite 5.0+ in frontend/package.json
- [ ] T002 [P] Configure Storybook for component testing in frontend/.storybook/main.ts
- [ ] T003 [P] Setup MSW for API mocking in frontend/src/mocks/browser.ts
- [ ] T004 [P] Configure Zustand store structure in frontend/src/stores/uploadStore.ts
- [ ] T005 [P] Setup axe-core accessibility testing in frontend/tests/accessibility/a11y.test.tsx
- [ ] T006 [P] Configure ESLint and Prettier for frontend in frontend/.eslintrc.js and frontend/.prettierrc
- [ ] T007 [P] Configure Black, flake8, and mypy for backend in backend/pyproject.toml
- [ ] T008 [P] Update backend dependencies to latest stable versions in backend/requirements.txt

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**
- [ ] T009 [P] Contract test POST /api/packages/upload in backend/tests/contract/test_package_upload_post.py
- [ ] T010 [P] Contract test GET /api/packages/upload/{id} in backend/tests/contract/test_package_upload_get.py
- [ ] T011 [P] Integration test package upload flow in backend/tests/integration/test_package_upload_integration.py
- [ ] T012 [P] Integration test ADFS authentication in backend/tests/integration/test_adfs_auth.py
- [ ] T013 [P] Security test file upload validation in backend/tests/security/test_file_upload_security.py
- [ ] T014 [P] Security test authentication bypass in backend/tests/security/test_auth_bypass.py
- [ ] T015 [P] Frontend component test FileUpload in frontend/src/components/FileUpload/FileUpload.test.tsx
- [ ] T016 [P] Frontend component test PackageUpload in frontend/src/pages/PackageUpload/PackageUpload.test.tsx
- [ ] T017 [P] Frontend accessibility test WCAG compliance in frontend/tests/accessibility/test_wcag_aa.tsx
- [ ] T018 [P] Frontend integration test upload flow in frontend/tests/integration/test_upload_flow.test.tsx

## Phase 3.3: Core Implementation (ONLY after tests are failing)
- [ ] T019 [P] Enhanced Request model with validation in backend/database/models/request.py
- [ ] T020 [P] Enhanced User model with audit fields in backend/database/models/user.py
- [ ] T021 [P] Request operations CRUD in backend/database/operations/request_operations.py
- [ ] T022 [P] Package lock parsing service in backend/services/package_lock_parsing_service.py
- [ ] T023 [P] Upload state management in frontend/src/stores/uploadStore.ts
- [ ] T024 [P] File upload component in frontend/src/components/FileUpload/FileUpload.tsx
- [ ] T025 [P] Package upload page in frontend/src/pages/PackageUpload/PackageUpload.tsx
- [ ] T026 [P] Package service API client in frontend/src/services/packageService.ts
- [ ] T027 [P] MSW handlers for package service in frontend/src/services/packageService.mock.ts
- [ ] T028 [P] Storybook stories for FileUpload in frontend/src/components/FileUpload/FileUpload.stories.tsx
- [ ] T029 [P] Storybook stories for PackageUpload in frontend/src/pages/PackageUpload/PackageUpload.stories.tsx
- [ ] T030 POST /api/packages/upload endpoint with ADFS authentication
- [ ] T031 GET /api/packages/upload/{id} endpoint with authorization
- [ ] T032 Input validation and file size limits (100MB)
- [ ] T033 Error handling and security logging
- [ ] T034 Container configuration updates (Dockerfile, docker-compose)

## Phase 3.4: Integration
- [ ] T035 Connect RequestService to DB with connection pooling
- [ ] T036 ADFS authentication middleware with token validation
- [ ] T037 Request/response logging with structured format
- [ ] T038 CORS and security headers for file uploads
- [ ] T039 Environment configuration management for upload limits
- [ ] T040 Health check endpoints for upload service
- [ ] T041 Frontend authentication hook in frontend/src/hooks/useAuth.tsx
- [ ] T042 Frontend API service integration in frontend/src/services/api.ts
- [ ] T043 Frontend error boundary for upload errors in frontend/src/components/ErrorBoundary.tsx

## Phase 3.5: Polish
- [ ] T044 [P] Unit tests for Request model validation in backend/tests/database/models/test_request.py
- [ ] T045 [P] Unit tests for User model in backend/tests/database/models/test_user.py
- [ ] T046 [P] Unit tests for package lock parsing in backend/tests/services/test_package_lock_parsing_service.py
- [ ] T047 [P] Unit tests for upload store in frontend/src/stores/uploadStore.test.ts
- [ ] T048 [P] Unit tests for package service in frontend/src/services/packageService.test.ts
- [ ] T049 Performance tests (<5s for 100MB uploads)
- [ ] T050 [P] Update docs/api.md with upload endpoints
- [ ] T051 Remove code duplication (DRY principle)
- [ ] T052 Security vulnerability scanning with Trivy
- [ ] T053 Accessibility compliance verification with axe-core
- [ ] T054 Production deployment validation
- [ ] T055 Run manual-testing.md scenarios

## Dependencies
- Tests (T009-T018) before implementation (T019-T034)
- T019 blocks T021, T035
- T020 blocks T021, T035
- T021 blocks T030, T031
- T022 blocks T030, T032
- T023 blocks T025, T041
- T024 blocks T025, T028
- T025 blocks T029
- T026 blocks T025, T042
- T027 blocks T018, T048
- T030 blocks T031
- T036 blocks T038
- Implementation before polish (T044-T055)
- Security tests (T013-T014) before security implementation
- Accessibility tests (T015-T017) before UI implementation

## Parallel Example
```
# Launch T009-T018 together (all tests):
Task: "Contract test POST /api/packages/upload in backend/tests/contract/test_package_upload_post.py"
Task: "Contract test GET /api/packages/upload/{id} in backend/tests/contract/test_package_upload_get.py"
Task: "Integration test package upload flow in backend/tests/integration/test_package_upload_integration.py"
Task: "Integration test ADFS authentication in backend/tests/integration/test_adfs_auth.py"
Task: "Security test file upload validation in backend/tests/security/test_file_upload_security.py"
Task: "Security test authentication bypass in backend/tests/security/test_auth_bypass.py"
Task: "Frontend component test FileUpload in frontend/src/components/FileUpload/FileUpload.test.tsx"
Task: "Frontend component test PackageUpload in frontend/src/pages/PackageUpload/PackageUpload.test.tsx"
Task: "Frontend accessibility test WCAG compliance in frontend/tests/accessibility/test_wcag_aa.tsx"
Task: "Frontend integration test upload flow in frontend/tests/integration/test_upload_flow.test.tsx"
```

## Notes
- [P] tasks = different files, no dependencies
- Verify tests fail before implementing
- Commit after each task
- Security and accessibility tests are mandatory
- All code must be production-ready from first commit
- Avoid: vague tasks, same file conflicts, security shortcuts
- Frontend uses co-located tests and stories with components
- Backend uses mirrored test structure under tests/ folder
- MSW mocks are co-located with services

## Task Generation Rules
*Applied during main() execution*

1. **From Contracts**:
   - package-upload-api.yaml → contract test tasks T009-T010 [P]
   - Each endpoint → implementation tasks T030-T031
   
2. **From Data Model**:
   - Request entity → model task T019 [P]
   - User entity → model task T020 [P]
   - Relationships → service layer tasks T021-T022
   
3. **From User Stories**:
   - Upload flow → integration test T011 [P]
   - ADFS auth → integration test T012 [P]
   - Quickstart scenarios → validation tasks T055

4. **Ordering**:
   - Setup → Tests → Models → Services → Endpoints → Polish
   - Dependencies block parallel execution

## Validation Checklist
*GATE: Checked by main() before returning*

- [x] All contracts have corresponding tests (T009-T010)
- [x] All entities have model tasks (T019-T020)
- [x] All tests come before implementation
- [x] Security tests included for all authentication/authorization (T013-T014)
- [x] Accessibility tests included for all UI components (T015-T017)
- [x] Container configuration tasks included (T034)
- [x] Production readiness tasks included (T052-T054)
- [x] Parallel tasks truly independent
- [x] Each task specifies exact file path
- [x] No task modifies same file as another [P] task
- [x] No security shortcuts or "fix later" approaches
