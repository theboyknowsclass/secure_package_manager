# Quickstart: Package Lock Upload

**Feature**: Package Lock Upload  
**Date**: 2024-12-19  
**Branch**: 001-package-lock-upload

## Overview

This quickstart guide demonstrates how to use the package lock upload feature. Users can securely upload package-lock.json files through a web interface with ADFS authentication, file validation, and progress tracking.

## Prerequisites

- Valid ADFS account with access to the Secure Package Manager
- package-lock.json file (lockfileVersion 3+)
- Modern web browser with JavaScript enabled
- Node.js 20.x LTS for development
- Docker and Docker Compose for local development

## Step-by-Step Guide

### 1. Access the Application

1. Navigate to the Secure Package Manager web interface
2. You will be redirected to the login page if not authenticated
3. Click "Sign In with Enterprise ID" to authenticate via ADFS
4. Complete the ADFS authentication flow
5. You will be redirected back to the application dashboard

### 2. Navigate to Upload Page

1. From the main dashboard, click on "Upload Package" or navigate to the upload page
2. You should see the package upload interface with drag-and-drop functionality

### 3. Upload Package-Lock.json File

1. **Drag and Drop Method**:
   - Drag your package-lock.json file onto the upload area
   - The file will be automatically selected for upload

2. **Click to Browse Method**:
   - Click on the upload area to open the file browser
   - Navigate to and select your package-lock.json file
   - Click "Open" to select the file

3. **Upload Process**:
   - The system will validate the file size (must be ≤ 100MB)
   - The system will validate the file format (must be valid JSON)
   - The system will validate the content (must be package-lock.json with lockfileVersion ≥ 3)
   - Upload progress will be displayed in real-time

### 4. Handle Upload Results

#### Successful Upload
- You will see a success message with:
  - Request ID for tracking
  - Application name and version extracted from the file
  - Number of packages processed
  - Timestamp of upload
- You will be automatically redirected to the status page after 2 seconds

#### Upload Errors
- **File Too Large**: "File size exceeds 100MB limit"
- **Invalid Format**: "Invalid JSON file"
- **Invalid Content**: "Invalid lockfileVersion: expected 3+, got {actual}"
- **Authentication Expired**: "Authentication required - please log in again"
- **Upload in Progress**: "You already have an upload in progress. Please wait for it to complete."

### 5. Track Upload Status

1. Navigate to the status page to view your upload progress
2. You can see:
   - Current status (uploading, processing, completed, failed, queued)
   - Progress percentage
   - Status messages
   - Request details

## User Scenarios

### Scenario 1: Successful Upload
**Given**: User is authenticated and has a valid package-lock.json file  
**When**: User uploads the file  
**Then**: 
- File is validated successfully
- Request is created with user information
- Raw file content is stored
- Success message is displayed
- User is redirected to status page

### Scenario 2: File Too Large
**Given**: User has a package-lock.json file larger than 100MB  
**When**: User attempts to upload the file  
**Then**: 
- File size validation fails
- Error message "File size exceeds 100MB limit" is displayed
- Upload is rejected
- User can try with a smaller file

### Scenario 3: Invalid File Format
**Given**: User has a file that is not valid JSON  
**When**: User attempts to upload the file  
**Then**: 
- JSON validation fails
- Error message "Invalid JSON file" is displayed
- Upload is rejected
- User can try with a valid JSON file

### Scenario 4: Invalid Package-Lock Content
**Given**: User has a JSON file that is not a valid package-lock.json  
**When**: User attempts to upload the file  
**Then**: 
- Content validation fails
- Specific error message is displayed (e.g., "Invalid lockfileVersion: expected 3+, got 2")
- Upload is rejected
- User can try with a valid package-lock.json file

### Scenario 5: Authentication Expired
**Given**: User's authentication token expires during upload  
**When**: Upload is in progress  
**Then**: 
- Current upload completes successfully
- User is required to re-authenticate for next upload
- Clear message about authentication requirement is displayed

### Scenario 6: Concurrent Upload Attempt
**Given**: User already has an upload in progress  
**When**: User attempts to start another upload  
**Then**: 
- Concurrency control prevents the new upload
- Message "You already have an upload in progress. Please wait for it to complete." is displayed
- New upload is queued or rejected

## Error Handling

### Common Error Messages

| Error Type | Message | Resolution |
|------------|---------|------------|
| File Too Large | "File size exceeds 100MB limit" | Use a smaller file or split the package-lock.json |
| Invalid JSON | "Invalid JSON file" | Ensure the file is valid JSON format |
| Invalid Lockfile Version | "Invalid lockfileVersion: expected 3+, got {actual}" | Use a package-lock.json from npm 8+ |
| Missing Required Fields | "Missing required field: {field}" | Ensure the file contains all required package-lock.json fields |
| Authentication Required | "Authentication required" | Log in via ADFS |
| Upload in Progress | "You already have an upload in progress" | Wait for current upload to complete |
| Database Unavailable | "Database temporarily unavailable" | Try again later |

### Troubleshooting

1. **Upload Stuck**: Refresh the page and try again
2. **Authentication Issues**: Clear browser cache and cookies, then log in again
3. **File Validation Errors**: Check that your file is a valid package-lock.json from npm 8+
4. **Network Issues**: Check your internet connection and try again

## Security Considerations

- All uploads require ADFS authentication
- Files are validated for size, format, and content
- Raw file content is stored securely
- All upload activities are logged for audit purposes
- User information is associated with each upload request

## Performance Notes

- Maximum file size: 100MB
- Upload progress is tracked in real-time
- Large files may take several minutes to upload
- Only one upload per user at a time
- Additional uploads are queued

## Support

If you encounter issues not covered in this guide:

1. Check the error message for specific guidance
2. Verify your file meets the requirements
3. Ensure you have a stable internet connection
4. Contact your system administrator for authentication issues
5. Check the application logs for technical details

## Next Steps

After successful upload:

1. Monitor the processing status on the status page
2. Review the extracted package information
3. Wait for background processing to complete
4. Access the processed results when available

The uploaded package-lock.json will be processed by the background workers for security scanning, license validation, and package approval workflows.

## Development and Testing

### Component Development with Storybook

1. **Start Storybook**:
   ```bash
   npm run storybook
   ```

2. **View Components**:
   - Navigate to `http://localhost:6006`
   - Browse component stories (co-located with components)
   - Test different states and interactions

3. **Component Organization**:
   ```
   src/components/FileUpload/
   ├── FileUpload.tsx           # Main component
   ├── FileUpload.test.tsx      # Unit tests
   └── FileUpload.stories.tsx   # Storybook stories
   ```

4. **Component Stories Available**:
   - Default upload state
   - Upload in progress with progress bar
   - Error states with specific error messages
   - Success state with confirmation
   - Queued state for concurrent uploads
   - Accessibility test scenarios

### API Development with MSW

1. **Mock API Responses**:
   - MSW handlers are co-located with services
   - Realistic API responses without backend dependency
   - Test error scenarios and edge cases

2. **Service Organization**:
   ```
   src/services/
   ├── packageService.ts      # Main service
   ├── packageService.mock.ts # MSW handlers for package service
   ├── authService.ts         # Auth service
   └── authService.mock.ts    # MSW handlers for auth service
   ```

3. **Available Mock Scenarios**:
   - Successful upload responses
   - Validation error responses
   - Authentication error responses
   - File too large errors
   - Concurrency conflict errors
   - Network error scenarios

### Automated Testing

1. **Run All Tests**:
   ```bash
   # Backend tests (co-located with source files)
   npm run python:all
   
   # Frontend tests (co-located with components)
   npm run test
   
   # Accessibility tests
   npm run test:a11y
   
   # Storybook tests
   npm run test:storybook
   ```

2. **Test Coverage**:
   - **Backend**: Unit tests mirror source structure under `tests/` folder (Python convention)
   - **Frontend**: Unit tests co-located with components (React convention)
   - **Component tests**: Storybook stories co-located with components
   - **Integration tests**: End-to-end flow testing
   - **Accessibility tests**: Automated WCAG AA compliance
   - **API contract tests**: OpenAPI specification validation

3. **Backend Test Organization** (Python Convention):
   ```
   backend/
   ├── routes/
   │   └── package_routes.py
   ├── services/
   │   └── auth_service.py
   ├── database/models/
   │   └── request.py
   └── tests/
       ├── routes/
       │   └── test_package_routes.py
       ├── services/
       │   └── test_auth_service.py
       └── database/models/
           └── test_request.py
   ```

4. **Frontend Test Organization** (React Convention):
   ```
   src/components/FileUpload/
   ├── FileUpload.tsx
   ├── FileUpload.test.tsx
   └── FileUpload.stories.tsx
   ```

### State Management

1. **Upload State (Zustand)**:
   - Global upload state management
   - Progress tracking
   - Error handling
   - Concurrency control

2. **State Actions**:
   - `startUpload()`: Initialize upload
   - `updateProgress(progress)`: Update progress
   - `setError(error)`: Handle errors
   - `setSuccess(requestId)`: Mark success
   - `resetState()`: Reset state

### Performance Optimization

1. **Vite Build System**:
   - Fast development server
   - Optimized production builds
   - Hot module replacement
   - Tree shaking for smaller bundles

2. **React 19.1.1 Features**:
   - Latest concurrent rendering improvements
   - Enhanced automatic batching
   - Improved Suspense and error boundaries
   - Better performance optimizations
   - Actions API and new hooks (useActionState, useFormStatus, useOptimistic)
   - Server Components and Server Actions support

### Accessibility Compliance

1. **Automated Testing**:
   - axe-core integration
   - WCAG AA compliance checks
   - Component-level accessibility testing
   - Storybook accessibility addon

2. **Manual Testing**:
   - Keyboard navigation
   - Screen reader compatibility
   - Color contrast validation
   - Focus management
