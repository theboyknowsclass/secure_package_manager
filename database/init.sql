-- Initialize the secure package manager database
-- Production schema - simplified and streamlined

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user' NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT users_role_check CHECK (role IN ('user', 'approver', 'admin'))
);

-- Create supported_licenses table
CREATE TABLE IF NOT EXISTS supported_licenses (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    identifier VARCHAR(100) UNIQUE NOT NULL, -- SPDX identifier (e.g., 'MIT', 'Apache-2.0')
    status VARCHAR(20) DEFAULT 'allowed' NOT NULL,
    created_by INTEGER REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT supported_licenses_status_check CHECK (status IN ('always_allowed', 'allowed', 'avoid', 'blocked'))
);

-- Create requests table (simplified from package_requests + applications)
CREATE TABLE IF NOT EXISTS requests (
    id SERIAL PRIMARY KEY,
    application_name VARCHAR(255) NOT NULL, -- from package-lock.json
    version VARCHAR(100) NOT NULL, -- from package-lock.json
    requestor_id INTEGER REFERENCES users(id) ON DELETE RESTRICT,
    package_lock_file TEXT, -- Store original package-lock.json content
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create packages table (distinct set of packages, unique on name+version)
CREATE TABLE IF NOT EXISTS packages (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    version VARCHAR(100) NOT NULL,
    npm_url VARCHAR(500),
    local_path VARCHAR(500),
    integrity VARCHAR(255), -- Package integrity hash from package-lock.json
    license_identifier VARCHAR(100), -- SPDX license identifier from package.json
    license_text TEXT, -- Full license text if available
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, version)
);

-- Create request_packages table (many-to-many linking table)
CREATE TABLE IF NOT EXISTS request_packages (
    request_id INTEGER REFERENCES requests(id) ON DELETE CASCADE,
    package_id INTEGER REFERENCES packages(id) ON DELETE CASCADE,
    package_type VARCHAR(20) NOT NULL DEFAULT 'new',
    PRIMARY KEY (request_id, package_id),
    CONSTRAINT request_packages_package_type_check CHECK (package_type IN ('new', 'existing'))
);

-- Create package_status table (replaces package_validations and status tracking)
CREATE TABLE IF NOT EXISTS package_status (
    id SERIAL PRIMARY KEY,
    package_id INTEGER REFERENCES packages(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL,
    file_size BIGINT,
    checksum VARCHAR(255),
    license_score INTEGER CHECK (license_score >= 0 AND license_score <= 100),
    security_score INTEGER CHECK (security_score >= 0 AND security_score <= 100),
    security_scan_status VARCHAR(50) DEFAULT 'pending',
    license_status VARCHAR(20), -- Primary license status calculated from supported_licenses table
    approver_id INTEGER REFERENCES users(id) ON DELETE SET NULL, -- User who approved the package
    rejector_id INTEGER REFERENCES users(id) ON DELETE SET NULL, -- User who rejected the package
    published_at TIMESTAMP, -- Timestamp when package was successfully published
    publish_status VARCHAR(20) DEFAULT 'pending', -- Publishing status: pending, publishing, published, failed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(package_id), -- Only one status record per package
    CONSTRAINT package_status_status_check CHECK (status IN (
        'Requested', 
        'Checking Licence',
        'Licence Checked', 
        'Downloading',
        'Downloaded', 
        'Security Scanning',
        'Security Scanned',
        'Pending Approval', 
        'Approved', 
        'Rejected'
    )),
    CONSTRAINT package_status_security_scan_status_check CHECK (security_scan_status IN ('pending', 'running', 'completed', 'failed', 'skipped')),
    CONSTRAINT package_status_license_status_check CHECK (license_status IN ('always_allowed', 'allowed', 'avoid', 'blocked')),
    CONSTRAINT package_status_publish_status_check CHECK (publish_status IN ('pending', 'publishing', 'published', 'failed'))
);

-- Create security_scans table (stores Trivy scan results)
CREATE TABLE IF NOT EXISTS security_scans (
    id SERIAL PRIMARY KEY,
    package_id INTEGER REFERENCES packages(id) ON DELETE CASCADE,
    scan_type VARCHAR(50) NOT NULL DEFAULT 'trivy',
    scan_result JSONB, -- Store the full Trivy scan result
    vulnerability_count INTEGER DEFAULT 0,
    critical_count INTEGER DEFAULT 0,
    high_count INTEGER DEFAULT 0,
    medium_count INTEGER DEFAULT 0,
    low_count INTEGER DEFAULT 0,
    info_count INTEGER DEFAULT 0,
    scan_duration_ms INTEGER, -- Scan duration in milliseconds
    trivy_version VARCHAR(50), -- Version of Trivy used for the scan
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Create audit_log table
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE RESTRICT,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id INTEGER,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance (minimal set)
-- Foreign key indexes for joins
CREATE INDEX IF NOT EXISTS idx_requests_requestor_id ON requests(requestor_id);
CREATE INDEX IF NOT EXISTS idx_request_packages_request_id ON request_packages(request_id);
CREATE INDEX IF NOT EXISTS idx_request_packages_package_id ON request_packages(package_id);
CREATE INDEX IF NOT EXISTS idx_package_status_package_id ON package_status(package_id);
CREATE INDEX IF NOT EXISTS idx_package_status_approver_id ON package_status(approver_id);
CREATE INDEX IF NOT EXISTS idx_package_status_rejector_id ON package_status(rejector_id);
CREATE INDEX IF NOT EXISTS idx_security_scans_package_id ON security_scans(package_id);

-- Common query patterns
CREATE INDEX IF NOT EXISTS idx_packages_name_version ON packages(name, version);
CREATE INDEX IF NOT EXISTS idx_package_status_status ON package_status(status);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_request_packages_package_type ON request_packages(package_type);


-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at (only if they don't exist)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_users_updated_at') THEN
        CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_supported_licenses_updated_at') THEN
        CREATE TRIGGER update_supported_licenses_updated_at BEFORE UPDATE ON supported_licenses FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_package_status_updated_at') THEN
        CREATE TRIGGER update_package_status_updated_at BEFORE UPDATE ON package_status FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_security_scans_updated_at') THEN
        CREATE TRIGGER update_security_scans_updated_at BEFORE UPDATE ON security_scans FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;
