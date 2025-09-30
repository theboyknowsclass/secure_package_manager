# Research: Package Lock Upload

**Feature**: Package Lock Upload  
**Date**: 2024-12-19  
**Branch**: 001-package-lock-upload

## Research Summary

This feature extends the existing package upload functionality with enhanced security, validation, and user experience. All technical decisions are based on the existing codebase architecture and constitutional requirements.

## Technical Decisions

### Frontend Architecture Enhancement
**Decision**: Upgrade to React 19.1.1, Node.js 20.x LTS, Vite 5.0+, and modern tooling stack  
**Rationale**: Current system uses React 18.2.0 and Vite 7.1.7. Upgrade to React 19.1.1 (latest stable) and Node.js 20.x LTS (supported until April 2026) for better performance, latest features, and improved developer experience.  
**Alternatives considered**: 
- Keep current versions: Rejected due to missing modern features
- Use Create React App: Rejected due to Vite's superior performance
- Use Next.js: Rejected due to existing Vite setup
- Use Node.js 22.x LTS: Rejected in favor of current stable LTS (20.x)

### Component Testing Strategy
**Decision**: Implement Storybook for UI component testing and documentation  
**Rationale**: Storybook provides isolated component development, visual testing, and documentation. Essential for maintaining component quality and accessibility.  
**Alternatives considered**: 
- Manual component testing: Rejected due to lack of isolation
- Enzyme/Jest only: Rejected due to limited visual testing
- Playwright component tests: Rejected due to complexity

### API Mocking Strategy
**Decision**: Use MSW (Mock Service Worker) for backend API mocking  
**Rationale**: MSW provides realistic API mocking that works in both tests and development. Better than traditional mock libraries for integration testing.  
**Alternatives considered**: 
- Jest mocks: Rejected due to limited integration testing
- JSON Server: Rejected due to setup complexity
- Manual fetch mocking: Rejected due to maintenance overhead

### State Management
**Decision**: Use Zustand for global state management  
**Rationale**: Current system already uses Zustand 5.0.8. Continue using it for upload state management due to its simplicity and performance.  
**Alternatives considered**: 
- Redux Toolkit: Rejected due to complexity for simple state
- Context API: Rejected due to performance concerns
- Local state only: Rejected due to need for global upload state

### Accessibility Testing
**Decision**: Implement automated accessibility testing with axe-core  
**Rationale**: WCAG AA compliance is constitutional requirement. Automated testing ensures consistent accessibility standards across components.  
**Alternatives considered**: 
- Manual testing only: Rejected due to inconsistency
- Lighthouse CI: Rejected due to limited component-level testing
- Pa11y: Rejected due to axe-core's better integration

### File Upload Architecture
**Decision**: Extend existing Flask multipart upload with enhanced validation  
**Rationale**: The current system already has working upload functionality in `package_routes.py`. We'll enhance it with the new requirements rather than rebuild.  
**Alternatives considered**: 
- New upload service: Rejected due to duplication
- Direct file system storage: Rejected due to security concerns
- Cloud storage integration: Rejected as out of scope

### Authentication Integration
**Decision**: Leverage existing ADFS/OAuth2 integration via AuthService  
**Rationale**: The system already has working ADFS authentication through mock-idp in development and OAuth2 flow. No changes needed to auth architecture.  
**Alternatives considered**:
- New authentication system: Rejected due to complexity
- Session-based auth: Rejected due to existing JWT implementation

### File Validation Strategy
**Decision**: Multi-layer validation (size, format, content) with specific error messages  
**Rationale**: Based on clarifications, users need specific technical error messages for debugging. The existing `package_lock_parsing_service.py` already handles content validation.  
**Alternatives considered**:
- Generic error messages: Rejected per clarifications
- Client-side only validation: Rejected due to security requirements

### Concurrency Management
**Decision**: Single upload per user with queuing mechanism  
**Rationale**: Clarification specified one upload at a time per user. This prevents resource conflicts and ensures predictable behavior.  
**Alternatives considered**:
- Unlimited concurrent uploads: Rejected due to resource concerns
- Multiple uploads with limits: Rejected per clarifications

### Error Handling Strategy
**Decision**: Complete current upload on token expiration, require re-auth for next  
**Rationale**: Balances user experience (don't lose work) with security (ensure fresh authentication).  
**Alternatives considered**:
- Cancel upload on expiration: Rejected due to poor UX
- Auto-refresh tokens: Rejected due to complexity

### Database Integration
**Decision**: Use existing Request model with raw_request_blob field  
**Rationale**: The current system already stores raw package-lock.json content in the Request model. No schema changes needed.  
**Alternatives considered**:
- New storage model: Rejected due to existing functionality
- Separate file storage: Rejected due to complexity

## Implementation Approach

### Backend Enhancements
1. **Enhanced Upload Endpoint**: Extend existing `/api/packages/upload` with new validation rules
2. **File Size Validation**: Add 100MB limit check before processing
3. **Concurrency Control**: Implement user-level upload locking mechanism
4. **Error Message Enhancement**: Provide specific technical error messages
5. **Token Expiration Handling**: Complete current upload, require re-auth for next

### Frontend Enhancements
1. **Modern React Setup**: Upgrade to React 19.1.1 with Node.js 20.x LTS and Vite 5.0+ for better performance and latest features
2. **Component Library**: Implement Storybook for isolated component development and testing
3. **State Management**: Use Zustand for upload state management with proper TypeScript support
4. **API Mocking**: Implement MSW for realistic API mocking in development and tests
5. **Upload Progress**: Enhance existing progress tracking for large files
6. **Error Display**: Show specific technical error messages with proper error boundaries
7. **Concurrency Feedback**: Inform users when upload is queued
8. **Authentication Flow**: Handle token expiration gracefully

### Testing Strategy
1. **Backend Unit Tests**: Mirror source structure under `tests/` folder (Python convention)
   - Route tests: `tests/routes/test_package_routes.py` mirrors `routes/package_routes.py`
   - Service tests: `tests/services/test_auth_service.py` mirrors `services/auth_service.py`
   - Model tests: `tests/database/models/test_request.py` mirrors `database/models/request.py`
2. **Frontend Unit Tests**: Co-located with components (React convention)
   - Component tests: `FileUpload.test.tsx` next to `FileUpload.tsx`
3. **Component Tests**: Storybook stories co-located with components
4. **Integration Tests**: End-to-end upload flow with authentication using MSW
5. **Accessibility Tests**: Automated WCAG AA compliance testing with axe-core
6. **Security Tests**: Authentication bypass attempts, file injection
7. **Performance Tests**: Large file uploads, concurrent user scenarios
8. **API Contract Tests**: Validate API responses match OpenAPI specification

## Dependencies and Integrations

### Existing Services (No Changes)
- `AuthService`: ADFS authentication and JWT token management
- `PackageLockParsingService`: Content validation and parsing
- `RequestOperations`: Database operations for request storage
- `AuditLogOperations`: Activity logging

### New Components
- Upload concurrency manager
- Enhanced error message formatting
- File size validation service
- Token expiration handling logic
- Storybook configuration and stories
- MSW handlers for API mocking
- Zustand store for upload state
- Automated accessibility testing setup

## Risk Assessment

### Low Risk
- File size validation (standard Flask feature)
- Error message enhancement (string formatting)
- Progress tracking (existing implementation)

### Medium Risk
- Concurrency control (requires careful state management)
- Token expiration handling (edge case complexity)

### Mitigation Strategies
- Comprehensive testing of concurrency scenarios
- Clear error messages for debugging
- Graceful degradation on failures

## Performance Considerations

### File Size Limits
- 100MB maximum per file (worst case scenario)
- Streaming upload for large files
- Progress feedback for user experience

### Concurrency
- Single upload per user prevents resource conflicts
- Queue mechanism for additional uploads
- Database connection pooling for concurrent users

### Memory Management
- Stream large files to avoid memory issues
- Clean up temporary files on errors
- Monitor memory usage during uploads

## Security Considerations

### Input Validation
- File type validation (JSON only)
- File size limits (100MB max)
- Content validation (package-lock.json structure)
- SQL injection protection (existing parameterized queries)

### Authentication
- ADFS integration for production
- JWT token validation
- Role-based access control
- Audit logging for all uploads

### Data Protection
- Raw file content stored securely
- User association with requests
- Encrypted data transmission
- Secure file handling

## Conclusion

The research confirms that this feature can be implemented by enhancing the existing upload functionality rather than building new systems. All constitutional requirements are met, and the technical approach leverages existing, proven components while adding the necessary security and user experience improvements.
