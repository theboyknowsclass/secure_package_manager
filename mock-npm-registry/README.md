# Mock Secure NPM Registry

This is a mock npm registry designed for testing the Secure Package Manager's publishing functionality. It implements the essential npm registry API endpoints to simulate a real npm registry.

## Features

- **Package Publishing**: Accepts npm publish commands
- **Package Installation**: Serves packages for npm install
- **Package Search**: Implements npm search functionality
- **Package Metadata**: Stores and serves package information
- **Tarball Storage**: Stores and serves package tarballs

## API Endpoints

### Registry Information
- `GET /` - Registry information
- `GET /health` - Health check

### Package Operations
- `GET /:package` - Get package information
- `GET /:package/:version` - Get specific package version
- `PUT /:package` - Publish package (with tarball upload)
- `GET /:package/-/:filename` - Download package tarball

### Search
- `GET /-/v1/search?text=query` - Search packages

### Debug
- `GET /-/all` - List all packages (for debugging)

## Usage

### Starting the Registry

The registry is automatically started with docker-compose:

```bash
docker-compose up mock-npm-registry
```

Or build and run manually:

```bash
cd mock-npm-registry
docker build -t mock-npm-registry .
docker run -p 8080:8080 mock-npm-registry
```

### Testing the Registry

1. **Health Check**:
   ```bash
   curl http://localhost:8080/health
   ```

2. **Registry Info**:
   ```bash
   curl http://localhost:8080/
   ```

3. **Publishing a Package**:
   ```bash
   # Set registry
   npm config set registry http://localhost:8080
   
   # Create a test package
   mkdir test-package
   cd test-package
   npm init -y
   
   # Publish
   npm publish
   ```

4. **Installing from Registry**:
   ```bash
   npm config set registry http://localhost:8080
   npm install your-package-name
   ```

5. **Search Packages**:
   ```bash
   curl "http://localhost:8080/-/v1/search?text=your-package"
   ```

### Integration with Secure Package Manager

The mock registry is configured to work with the Secure Package Manager:

1. **Environment Variable**: Set `SECURE_REPO_URL=http://mock-npm-registry:8080`
2. **Docker Network**: The registry runs on the `app-network` for internal communication
3. **Volume Storage**: Package tarballs are stored in the `npm_storage` volume

## Configuration

The registry can be configured using environment variables:

- `PORT`: Port to run on (default: 8080)

## Storage

- Package metadata is stored in memory (resets on restart)
- Package tarballs are stored in `/app/storage/packages/` (persistent via Docker volume)

## Limitations

This is a mock registry designed for testing and development:

- No authentication/authorization
- No package versioning constraints
- No package deletion
- No user management
- In-memory metadata storage (not persistent)

## Development

To modify the registry:

1. Edit `server.js` for API changes
2. Update `package.json` for dependencies
3. Rebuild the Docker image:
   ```bash
   docker-compose build mock-npm-registry
   docker-compose up mock-npm-registry
   ```
