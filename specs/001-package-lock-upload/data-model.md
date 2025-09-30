# Data Model: Package Lock Upload

**Feature**: Package Lock Upload  
**Date**: 2024-12-19  
**Branch**: 001-package-lock-upload

## Entity Overview

This feature extends the existing data model with enhanced validation and user experience. No new database entities are required as the existing `Request`, `User`, and related models already support the required functionality. However, new frontend state management entities are introduced for upload state, component testing, and API mocking.

## Existing Entities (Enhanced)

### Request Entity
**Purpose**: Stores package-lock.json upload requests with metadata and raw content

**Current Fields**:
- `id`: Primary key (Integer)
- `application_name`: Name from package-lock.json (String, 255 chars)
- `version`: Version from package-lock.json (String, 100 chars)
- `requestor_id`: Foreign key to User (Integer)
- `raw_request_blob`: Complete package-lock.json content (Text)
- `created_at`: Timestamp (DateTime)

**Enhanced Validation Rules**:
- `raw_request_blob`: Must be valid JSON with lockfileVersion >= 3
- `application_name`: Required, extracted from package-lock.json
- `version`: Required, extracted from package-lock.json
- `requestor_id`: Must reference existing authenticated user

**State Transitions**:
- `created` → `processing` → `completed` (via existing package processing pipeline)
- `created` → `failed` (on validation errors)

### User Entity
**Purpose**: Represents authenticated users who can upload package-lock.json files

**Current Fields**:
- `id`: Primary key (Integer)
- `username`: Unique username (String, 255 chars)
- `email`: Unique email (String, 255 chars)
- `full_name`: Display name (String, 255 chars)
- `role`: Access level (String, 20 chars: "user", "approver", "admin")
- `created_at`: Account creation timestamp (DateTime)
- `updated_at`: Last update timestamp (DateTime)

**Upload Permissions**:
- All authenticated users can upload package-lock.json files
- Role-based access for viewing/approving requests (existing functionality)

### AuditLog Entity
**Purpose**: Tracks all upload activities for security and compliance

**Current Fields**:
- `id`: Primary key (Integer)
- `user_id`: Foreign key to User (Integer)
- `action`: Action performed (String)
- `resource_type`: Type of resource (String)
- `resource_id`: ID of affected resource (Integer)
- `details`: Additional information (Text)
- `created_at`: Timestamp (DateTime)

**Upload-Related Actions**:
- `create_request`: Package-lock.json upload initiated
- `upload_completed`: Upload successfully processed
- `upload_failed`: Upload failed validation or processing
- `upload_cancelled`: Upload cancelled by user or system

## Frontend State Entities

### Upload State (Zustand Store)
**Purpose**: Manages upload state, progress, and error handling in the frontend

**State Fields**:
- `isUploading`: Boolean indicating if upload is in progress
- `uploadProgress`: Number (0-100) representing upload progress percentage
- `uploadError`: String containing error message if upload fails
- `uploadSuccess`: Boolean indicating if upload completed successfully
- `currentRequestId`: String/Number ID of current upload request
- `isQueued`: Boolean indicating if upload is queued due to concurrency

**State Actions**:
- `startUpload()`: Initialize upload state
- `updateProgress(progress)`: Update upload progress
- `setError(error)`: Set upload error state
- `setSuccess(requestId)`: Mark upload as successful
- `resetState()`: Reset to initial state
- `setQueued()`: Mark upload as queued

### Component Story (Storybook)
**Purpose**: Defines component variations and test scenarios for Storybook, co-located with components

**File Structure**:
```
components/FileUpload/
├── FileUpload.tsx           # Main component
├── FileUpload.test.tsx      # Unit tests
└── FileUpload.stories.tsx   # Storybook stories
```

**Story Fields**:
- `title`: String component title for Storybook navigation
- `component`: React component reference
- `args`: Object containing component props
- `parameters`: Object containing Storybook configuration
- `play`: Function containing interaction tests

**Story Variants**:
- Default state
- Upload in progress
- Upload error states
- Upload success state
- Queued upload state
- Accessibility test scenarios

### API Mock Handler (MSW)
**Purpose**: Defines mock API responses for development and testing, co-located with services

**File Structure**:
```
services/
├── packageService.ts      # Main service
├── packageService.mock.ts # MSW handlers for package service
├── authService.ts         # Auth service
└── authService.mock.ts    # MSW handlers for auth service
```

**Handler Fields**:
- `method`: HTTP method (GET, POST, PUT, DELETE)
- `url`: String URL pattern to match
- `response`: Function returning mock response
- `status`: HTTP status code
- `delay`: Optional delay for realistic testing

**Mock Scenarios**:
- Successful upload response
- Validation error responses
- Authentication error responses
- File too large error
- Concurrency conflict error
- Network error scenarios

## Data Flow

### Upload Process
1. **Authentication**: User authenticates via ADFS/OAuth2
2. **File Upload**: User uploads package-lock.json file
3. **Validation**: System validates file size, format, and content
4. **Request Creation**: System creates Request record with raw content
5. **Audit Logging**: System logs upload activity
6. **Processing**: Background workers process the request (existing pipeline)

### Validation Rules

#### File Size Validation
- Maximum file size: 100MB
- Validation occurs before content processing
- Error message: "File size exceeds 100MB limit"

#### File Format Validation
- Must be valid JSON
- Must contain `lockfileVersion` field
- Must contain `packages` field
- Error messages: Specific technical errors per validation failure

#### Content Validation
- `lockfileVersion` must be >= 3
- `packages` must be a valid object
- Error messages: "Invalid lockfileVersion: expected 3+, got {actual}"

#### User Validation
- User must be authenticated
- User must have valid JWT token
- Token expiration handled gracefully during upload

## Relationships

### Request → User
- **Type**: Many-to-One
- **Constraint**: Each request belongs to exactly one user
- **Cascade**: Delete requests when user is deleted (if required by business rules)

### Request → AuditLog
- **Type**: One-to-Many
- **Constraint**: Each request can have multiple audit log entries
- **Purpose**: Track all activities related to a specific request

### User → Request
- **Type**: One-to-Many
- **Constraint**: Each user can have multiple requests
- **Purpose**: Track all uploads by a specific user

## Data Integrity

### Constraints
- `requestor_id` must reference existing user
- `raw_request_blob` must be valid JSON
- `application_name` and `version` must be non-empty
- `created_at` must be valid timestamp

### Indexes
- `requests.requestor_id` (for user request queries)
- `requests.created_at` (for chronological queries)
- `audit_logs.user_id` (for user activity queries)
- `audit_logs.resource_id` (for request activity queries)

## Security Considerations

### Data Protection
- Raw file content stored as-is for processing
- User information linked for audit trail
- All data encrypted at rest and in transit

### Access Control
- Only authenticated users can upload
- Users can only view their own requests (unless admin/approver)
- Audit logs track all access and modifications

### Data Retention
- Raw file content retained for processing and audit
- User data retained per existing business rules
- Audit logs retained per compliance requirements

## Performance Considerations

### Storage
- Raw file content stored as TEXT (PostgreSQL)
- Large files (up to 100MB) handled efficiently
- Database connection pooling for concurrent uploads

### Querying
- Indexes on frequently queried fields
- Efficient joins between Request and User tables
- Pagination for large result sets

### Concurrency
- Single upload per user prevents conflicts
- Database transactions ensure data consistency
- Connection pooling handles concurrent users

## Migration Strategy

### No Schema Changes Required
- Existing Request model supports all requirements
- Existing User model supports authentication
- Existing AuditLog model supports activity tracking

### Data Migration
- No data migration required
- Existing data remains compatible
- New validation rules apply to new uploads only

### Backward Compatibility
- Existing API endpoints remain functional
- Existing data remains accessible
- New features are additive, not breaking

## Testing Strategy

### Unit Tests
- Request model validation
- User authentication checks
- File size and format validation
- Error message formatting

### Integration Tests
- End-to-end upload flow
- Database transaction handling
- Audit log creation
- Error handling scenarios

### Performance Tests
- Large file upload handling
- Concurrent user scenarios
- Database query performance
- Memory usage monitoring

## Conclusion

The existing data model already supports the package lock upload feature requirements. The enhancements focus on validation rules, error handling, and user experience rather than structural changes. This approach minimizes risk while delivering the required functionality.
