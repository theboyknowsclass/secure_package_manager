# Flask Routes Structure

This document describes the new organized structure for Flask routes in the secure package manager backend.

## Structure

```
backend/
├── app.py                # Main Flask application (organized structure)
├── routes/               # Route blueprints
│   ├── __init__.py
│   ├── auth_routes.py    # Authentication routes (/api/auth/*)
│   ├── package_routes.py # Package management routes (/api/packages/*)
│   └── admin_routes.py   # Admin routes (/api/admin/*)
├── services/             # Business logic services
│   ├── auth_service.py   # Authentication service (with enhanced debugging)
│   ├── package_service.py
│   ├── validation_service.py
│   └── license_service.py
└── models.py             # Database models
```

## Route Organization

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

## Enhanced Debugging

The `auth_service.py` now includes comprehensive debugging:

- **Token extraction**: Logs Authorization header and extracted token
- **Token verification**: Detailed logging of JWT payload and user lookup
- **User creation**: Logs when new users are created from OAuth2 tokens
- **Request context**: Logs when user is added to request context
- **Endpoint execution**: Logs successful execution and errors

## Running the Application

Simply run the main Flask application:

```bash
python app.py
```

## Benefits of New Structure

1. **Better Organization**: Routes are grouped by functionality
2. **Easier Maintenance**: Each route file focuses on specific functionality
3. **Enhanced Debugging**: Comprehensive logging for authentication issues
4. **Scalability**: Easy to add new route groups
5. **Code Reusability**: Blueprints can be reused in different contexts

## Key Features

- **Organized Structure**: Routes grouped by functionality using Flask blueprints
- **Enhanced Debugging**: Comprehensive logging for authentication issues
- **New Endpoint**: `/api/auth/userinfo` for consistency with OAuth flow
- **Scalable**: Easy to add new route groups and features
