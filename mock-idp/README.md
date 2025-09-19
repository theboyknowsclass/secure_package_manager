# Mock Identity Provider (IDP)

A mock OAuth 2.0 / OpenID Connect identity provider for development and testing of the Secure Package Manager.

## Overview

This mock IDP simulates an enterprise identity provider (like ADFS or Azure AD) to provide authentication services for the Secure Package Manager during development. It implements a simplified OAuth 2.0 authorization code flow with JWT token generation.

## Features

- **OAuth 2.0 Authorization Code Flow**: Implements the standard OAuth 2.0 flow
- **JWT Token Generation**: Creates signed JWT tokens with user claims
- **Mock User Database**: Pre-configured test users with different roles
- **Role-based Access Control**: Maps AD groups to application roles
- **Session Management**: Handles user sessions and OAuth state
- **CORS Support**: Configured for cross-origin requests

## Configuration

The mock IDP uses environment variables for configuration. See `../env.development.example` for all available options.

### Required Environment Variables

- `JWT_SECRET`: Secret key for signing JWT tokens
- `IDP_SECRET_KEY`: Flask session secret key
- `OAUTH_AUDIENCE`: OAuth audience identifier
- `OAUTH_ISSUER`: OAuth issuer URL
- `FRONTEND_URL`: Frontend application URL
- `IDP_ENTITY_ID`: IDP entity identifier
- `IDP_SSO_URL`: IDP SSO endpoint URL

## Default Test Users

The mock IDP includes several pre-configured test users:

| Username | Password | Role | AD Groups |
|----------|----------|------|-----------|
| admin | admin | admin | PackageManager-Admins |
| approver | approver | approver | PackageManager-Approvers |
| developer | developer | user | PackageManager-Users |
| tester | tester | user | PackageManager-Users |

## API Endpoints

### Authentication Flow

1. **Authorization Request**: `GET /sso`
   - Initiates OAuth flow
   - Redirects to login page

2. **Login Page**: `GET /login`
   - Displays user login form
   - Accepts username/password

3. **Login Submission**: `POST /login`
   - Validates credentials
   - Redirects to authorization callback

4. **Authorization Callback**: `GET /callback`
   - Generates authorization code
   - Redirects back to client

5. **Token Exchange**: `POST /token`
   - Exchanges authorization code for JWT token
   - Returns access token

6. **Token Validation**: `POST /validate`
   - Validates JWT tokens
   - Returns user information

### Health Check

- **Health Check**: `GET /health`
  - Returns service status

## JWT Token Structure

The mock IDP generates JWT tokens with the following claims:

```json
{
  "sub": "user_id",
  "username": "username",
  "email": "user@company.com",
  "roles": ["role1", "role2"],
  "ad_groups": ["group1", "group2"],
  "aud": "oauth_audience",
  "iss": "oauth_issuer",
  "exp": 1234567890,
  "iat": 1234567890
}
```

## Development Usage

### Starting the Service

The mock IDP is automatically started with the development environment:

```bash
# Start all development services
./scripts/dev-start.sh

# Or start just the mock IDP
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up mock-idp
```

### Access Points

- **Service URL**: http://localhost:8081
- **Health Check**: http://localhost:8081/health
- **SSO Endpoint**: http://localhost:8081/sso

### Testing Authentication

1. Navigate to the frontend application
2. Click "Login" to initiate OAuth flow
3. Use any of the test user credentials
4. You'll be redirected back to the frontend with a valid JWT token

## Security Notes

⚠️ **This is a development-only service!**

- Uses weak default passwords
- No real security validation
- JWT secrets are predictable
- **Never use in production**

## Troubleshooting

### Common Issues

1. **401 Unauthorized**: Check that JWT_SECRET matches between mock-idp and backend
2. **CORS Errors**: Verify FRONTEND_URL is correctly configured
3. **Token Validation Fails**: Ensure OAUTH_AUDIENCE and OAUTH_ISSUER match backend expectations

### Logs

View mock IDP logs:

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs mock-idp
```

### Reset Service

Restart the mock IDP service:

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart mock-idp
```

## Dependencies

- Flask: Web framework
- PyJWT: JWT token handling
- Flask-CORS: Cross-origin resource sharing

See `requirements.txt` for complete dependency list.
