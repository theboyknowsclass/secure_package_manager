-- Initialize the secure package manager database

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

-- Create applications table
CREATE TABLE IF NOT EXISTS applications (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    version VARCHAR(100) NOT NULL,
    description TEXT,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, version)
);

-- Create supported_licenses table
CREATE TABLE IF NOT EXISTS supported_licenses (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    identifier VARCHAR(100) UNIQUE NOT NULL, -- SPDX identifier (e.g., 'MIT', 'Apache-2.0')
    status VARCHAR(20) DEFAULT 'allowed' CHECK (status IN ('always_allowed', 'allowed', 'avoid', 'blocked')), -- license status
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create package_requests table
CREATE TABLE IF NOT EXISTS package_requests (
    id SERIAL PRIMARY KEY,
    application_id INTEGER REFERENCES applications(id),
    requestor_id INTEGER REFERENCES users(id),
    package_lock_file TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'requested',
    total_packages INTEGER DEFAULT 0,
    validated_packages INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create packages table
CREATE TABLE IF NOT EXISTS packages (
    id SERIAL PRIMARY KEY,
    package_request_id INTEGER REFERENCES package_requests(id),
    name VARCHAR(255) NOT NULL,
    version VARCHAR(100) NOT NULL,
    npm_url VARCHAR(500),
    local_path VARCHAR(500),
    file_size BIGINT,
    checksum VARCHAR(255),
    license_identifier VARCHAR(100), -- SPDX license identifier from package.json
    license_text TEXT, -- Full license text if available
    status VARCHAR(50) DEFAULT 'requested',
    validation_errors TEXT[],
    security_score INTEGER CHECK (security_score >= 0 AND security_score <= 100),
    license_score INTEGER CHECK (license_score >= 0 AND license_score <= 100), -- License compliance score
    security_scan_status VARCHAR(50) DEFAULT 'pending',
    vulnerability_count INTEGER DEFAULT 0,
    critical_vulnerabilities INTEGER DEFAULT 0,
    high_vulnerabilities INTEGER DEFAULT 0,
    medium_vulnerabilities INTEGER DEFAULT 0,
    low_vulnerabilities INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, version, package_request_id)
);

-- Create package_references table
CREATE TABLE IF NOT EXISTS package_references (
    id SERIAL PRIMARY KEY,
    package_request_id INTEGER REFERENCES package_requests(id),
    name VARCHAR(255) NOT NULL,
    version VARCHAR(100) NOT NULL,
    npm_url VARCHAR(500),
    integrity VARCHAR(255),
    status VARCHAR(50) DEFAULT 'referenced',
    existing_package_id INTEGER REFERENCES packages(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create package_validations table
CREATE TABLE IF NOT EXISTS package_validations (
    id SERIAL PRIMARY KEY,
    package_id INTEGER REFERENCES packages(id),
    validation_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create security_scans table
CREATE TABLE IF NOT EXISTS security_scans (
    id SERIAL PRIMARY KEY,
    package_id INTEGER REFERENCES packages(id) ON DELETE CASCADE,
    scan_type VARCHAR(50) NOT NULL DEFAULT 'trivy',
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
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
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id INTEGER,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create repository_config table
CREATE TABLE IF NOT EXISTS repository_config (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_packages_status ON packages(status);
CREATE INDEX IF NOT EXISTS idx_package_requests_status ON package_requests(status);
CREATE INDEX IF NOT EXISTS idx_packages_name_version ON packages(name, version);
CREATE INDEX IF NOT EXISTS idx_package_references_status ON package_references(status);
CREATE INDEX IF NOT EXISTS idx_package_references_name_version ON package_references(name, version);
CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_security_scans_package_id ON security_scans(package_id);
CREATE INDEX IF NOT EXISTS idx_security_scans_status ON security_scans(status);
CREATE INDEX IF NOT EXISTS idx_security_scans_scan_type ON security_scans(scan_type);
CREATE INDEX IF NOT EXISTS idx_security_scans_created_at ON security_scans(created_at);
CREATE INDEX IF NOT EXISTS idx_packages_security_scan_status ON packages(security_scan_status);


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
    
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_applications_updated_at') THEN
        CREATE TRIGGER update_applications_updated_at BEFORE UPDATE ON applications FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_supported_licenses_updated_at') THEN
        CREATE TRIGGER update_supported_licenses_updated_at BEFORE UPDATE ON supported_licenses FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_package_requests_updated_at') THEN
        CREATE TRIGGER update_package_requests_updated_at BEFORE UPDATE ON package_requests FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_packages_updated_at') THEN
        CREATE TRIGGER update_packages_updated_at BEFORE UPDATE ON packages FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_repository_config_updated_at') THEN
        CREATE TRIGGER update_repository_config_updated_at BEFORE UPDATE ON repository_config FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_security_scans_updated_at') THEN
        CREATE TRIGGER update_security_scans_updated_at BEFORE UPDATE ON security_scans FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;
