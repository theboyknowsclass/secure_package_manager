# Mock NPM Registry

A mock NPM registry server for development and testing of the Secure Package Manager.

## Overview

This mock NPM registry simulates the public NPM registry (registry.npmjs.org) to provide package metadata and tarball downloads during development. It allows the Secure Package Manager to test package downloading and validation without hitting the real NPM registry.

## Features

- **Package Metadata API**: Serves package.json metadata for packages
- **Tarball Downloads**: Provides downloadable package tarballs
- **Search API**: Basic package search functionality
- **CORS Support**: Configured for cross-origin requests
- **Real Package Data**: Uses actual NPM package data when available

## Configuration

The mock registry runs on port 8080 by default and requires no special configuration. It automatically proxies requests to the real NPM registry when packages aren't found locally.

## API Endpoints

### Package Information

- **Get Package**: `GET /{package_name}`
  - Returns package metadata (package.json)
  - Example: `GET /lodash` returns lodash package information

- **Get Specific Version**: `GET /{package_name}/{version}`
  - Returns specific version metadata
  - Example: `GET /lodash/4.17.21` returns lodash v4.17.21 info

### Package Downloads

- **Download Tarball**: `GET /{package_name}/-/{package_name}-{version}.tgz`
  - Downloads package tarball
  - Example: `GET /lodash/-/lodash-4.17.21.tgz`

### Search

- **Search Packages**: `GET /-/v1/search?text={query}`
  - Searches for packages by name
  - Example: `GET /-/v1/search?text=lodash`

### Health Check

- **Health Check**: `GET /-/ping`
  - Returns registry status

## Development Usage

### Starting the Service

The mock registry is automatically started with the development environment:

```bash
# Start all development services
./scripts/dev-start.sh

# Or start just the mock registry
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up mock-npm-registry
```

### Access Points

- **Registry URL**: http://localhost:8080
- **Health Check**: http://localhost:8080/-/ping
- **Package Example**: http://localhost:8080/lodash

### Testing Package Downloads

1. The Secure Package Manager is configured to use this mock registry
2. When processing package-lock.json files, packages are downloaded from this registry
3. The registry proxies to the real NPM registry for actual package data

## How It Works

1. **Request Interception**: Intercepts requests from the Secure Package Manager
2. **Real Data Proxy**: Forwards requests to the real NPM registry (registry.npmjs.org)
3. **Response Caching**: Caches responses for faster subsequent requests
4. **Tarball Handling**: Downloads and serves actual package tarballs

## Package Processing Flow

When the Secure Package Manager processes a package:

1. **Metadata Request**: Requests package metadata from mock registry
2. **Version Resolution**: Gets specific version information
3. **Tarball Download**: Downloads the actual package tarball
4. **Extraction**: Extracts tarball for Trivy security scanning
5. **Validation**: Validates package contents and security

## Security Considerations

- **Real Package Data**: Downloads actual packages from NPM
- **No Malicious Packages**: Only serves packages that exist in the real NPM registry
- **Network Isolation**: Runs in Docker container with controlled network access
- **Development Only**: Intended for development and testing only

## Troubleshooting

### Common Issues

1. **Package Not Found**: Check that the package exists in the real NPM registry
2. **Download Failures**: Verify network connectivity to registry.npmjs.org
3. **CORS Errors**: The service is configured for CORS, but check frontend configuration

### Logs

View mock registry logs:

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs mock-npm-registry
```

### Reset Service

Restart the mock registry service:

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart mock-npm-registry
```

### Test Registry

Test the registry manually:

```bash
# Test health check
curl http://localhost:8080/-/ping

# Test package metadata
curl http://localhost:8080/lodash

# Test specific version
curl http://localhost:8080/lodash/4.17.21
```

## Dependencies

- Express.js: Web server framework
- CORS: Cross-origin resource sharing
- Request: HTTP client for proxying to real NPM registry

See `package.json` for complete dependency list.

## Integration with Secure Package Manager

The mock registry is configured as the package source in the development environment:

- **Environment Variable**: `TARGET_REPOSITORY_URL=http://mock-npm-registry:8080`
- **Package Service**: Uses this URL for downloading packages
- **Trivy Integration**: Downloaded packages are scanned for vulnerabilities

This allows the entire package processing pipeline to work in a controlled development environment without external dependencies.
