-- Initialize the secure package manager database

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

-- Create package_requests table
CREATE TABLE IF NOT EXISTS package_requests (
    id SERIAL PRIMARY KEY,
    application_id INTEGER REFERENCES applications(id),
    requestor_id INTEGER REFERENCES users(id),
    package_lock_file TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'requested' CHECK (status IN ('requested', 'validating', 'validated', 'approved', 'published', 'rejected')),
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
    status VARCHAR(50) DEFAULT 'requested' CHECK (status IN ('requested', 'downloading', 'downloaded', 'validating', 'validated', 'approved', 'published', 'rejected')),
    validation_errors TEXT[],
    security_score INTEGER CHECK (security_score >= 0 AND security_score <= 100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, version, package_request_id)
);

-- Create package_validations table
CREATE TABLE IF NOT EXISTS package_validations (
    id SERIAL PRIMARY KEY,
    package_id INTEGER REFERENCES packages(id),
    validation_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL CHECK (status IN ('pending', 'passed', 'failed')),
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_packages_status ON packages(status);
CREATE INDEX IF NOT EXISTS idx_package_requests_status ON package_requests(status);
CREATE INDEX IF NOT EXISTS idx_packages_name_version ON packages(name, version);
CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at);

-- Insert default admin user
INSERT INTO users (username, email, full_name, is_admin) 
VALUES ('admin', 'admin@example.com', 'System Administrator', TRUE)
ON CONFLICT (username) DO NOTHING;

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_applications_updated_at BEFORE UPDATE ON applications FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_package_requests_updated_at BEFORE UPDATE ON package_requests FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_packages_updated_at BEFORE UPDATE ON packages FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
