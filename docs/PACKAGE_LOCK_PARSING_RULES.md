# Package-lock.json Parsing Rules

## Overview

This document defines the rules for parsing `package-lock.json` files to extract dependent packages for security scanning and license validation.

## Package-lock.json Structure

### Basic Structure
```json
{
  "name": "project-name",
  "version": "1.0.0",
  "lockfileVersion": 3,
  "requires": true,
  "packages": {
    "": { /* root package */ },
    "node_modules/package-name": { /* dependency */ },
    "node_modules/@scope/package-name": { /* scoped dependency */ }
  }
}
```

### Supported Versions
- **lockfileVersion 3+**: Only supported (npm 8+)
- **lockfileVersion 1-2**: Not supported (legacy format)

## Package Path Rules

### 1. Root Package
- **Path**: `""` (empty string)
- **Purpose**: Represents the main project
- **Action**: Skip during dependency extraction

### 2. Regular Packages
- **Path Format**: `node_modules/<package-name>`
- **Examples**:
  - `node_modules/lodash`
  - `node_modules/express`
  - `node_modules/react`
- **Extraction Rule**: Take the package name directly from the path

### 3. Scoped Packages
- **Path Format**: `node_modules/@<scope>/<package-name>`
- **Examples**:
  - `node_modules/@types/node`
  - `node_modules/@babel/core`
  - `node_modules/@mui/material`
- **Extraction Rule**: Combine scope and package name: `@<scope>/<package-name>`

### 4. Nested Dependencies
- **Path Format**: `node_modules/<parent>/node_modules/<child>`
- **Examples**:
  - `node_modules/express/node_modules/accepts`
  - `node_modules/@types/node/node_modules/@types/events`
- **Extraction Rule**: Extract the final package name from the path

## Package Information Extraction

### Required Fields
Each package entry must contain:
- **`version`**: Exact version installed
- **`resolved`**: URL from which package was fetched
- **`integrity`**: Hash for package verification

### Optional Fields
- **`name`**: Package name (may be missing in some entries)
- **`dependencies`**: Package's own dependencies
- **`license`**: License information
- **`dev`**: Whether it's a dev dependency

## Parsing Algorithm

### Step 1: Validate File
```python
def validate_package_lock(package_data):
    if "lockfileVersion" not in package_data:
        raise ValueError("Not a package-lock.json file")
    
    if package_data["lockfileVersion"] < 3:
        raise ValueError("Unsupported lockfile version")
```

### Step 2: Extract Packages
```python
def extract_packages(package_data):
    packages = package_data.get("packages", {})
    return {path: info for path, info in packages.items() if path != ""}
```

### Step 3: Parse Package Names
```python
def extract_package_name(package_path, package_info):
    # Try to get name from package info first
    package_name = package_info.get("name")
    if package_name:
        return package_name
    
    # Extract from path if name is missing
    if package_path.startswith("node_modules/"):
        path_parts = package_path.split("/")
        
        if len(path_parts) >= 2:
            if path_parts[1].startswith("@"):
                # Scoped package: @scope/package
                if len(path_parts) >= 3:
                    return f"{path_parts[1]}/{path_parts[2]}"
                else:
                    return path_parts[1]
            else:
                # Regular package
                return path_parts[1]
    
    return None
```

## Deduplication Rules

### Primary Key
- **Format**: `<package-name>@<version>`
- **Examples**:
  - `lodash@4.17.21`
  - `@types/node@18.15.0`

### Deduplication Strategy
1. **Within same lockfile**: Keep first occurrence
2. **Across different lockfiles**: Allow multiple versions
3. **Same name+version**: Treat as single package

## Error Handling

### Invalid Paths
- Skip packages with invalid paths
- Log warnings for malformed entries
- Continue processing other packages

### Missing Information
- Skip packages without version
- Use path-based name extraction when `name` field is missing
- Log warnings for incomplete entries

### Scoped Package Edge Cases
- Handle incomplete scoped paths (e.g., `node_modules/@types` without package name)
- Validate scope format (must start with `@`)
- Handle nested scoped packages correctly

## Examples

### Regular Package
```json
"node_modules/lodash": {
  "version": "4.17.21",
  "resolved": "https://registry.npmjs.org/lodash/-/lodash-4.17.21.tgz",
  "integrity": "sha512-..."
}
```
**Extracted**: `lodash@4.17.21`

### Scoped Package
```json
"node_modules/@types/node": {
  "version": "18.15.0",
  "resolved": "https://registry.npmjs.org/@types/node/-/node-18.15.0.tgz",
  "integrity": "sha512-..."
}
```
**Extracted**: `@types/node@18.15.0`

### Nested Dependency
```json
"node_modules/express/node_modules/accepts": {
  "version": "1.3.8",
  "resolved": "https://registry.npmjs.org/accepts/-/accepts-1.3.8.tgz",
  "integrity": "sha512-..."
}
```
**Extracted**: `accepts@1.3.8`

## Implementation Notes

### Performance Considerations
- Process packages in batches
- Use efficient data structures for deduplication
- Cache package metadata lookups

### Security Considerations
- Validate package names against npm naming conventions
- Sanitize package paths to prevent path traversal
- Verify package integrity hashes

### Logging
- Log package extraction statistics
- Warn about malformed entries
- Track processing time and performance metrics
