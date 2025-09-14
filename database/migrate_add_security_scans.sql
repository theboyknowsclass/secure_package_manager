-- Add security scan results table for Trivy integration

-- Create security_scans table
CREATE TABLE IF NOT EXISTS security_scans (
    id SERIAL PRIMARY KEY,
    package_id INTEGER REFERENCES packages(id) ON DELETE CASCADE,
    scan_type VARCHAR(50) NOT NULL DEFAULT 'trivy' CHECK (scan_type IN ('trivy', 'snyk', 'npm_audit')),
    status VARCHAR(50) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'skipped')),
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

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_security_scans_package_id ON security_scans(package_id);
CREATE INDEX IF NOT EXISTS idx_security_scans_status ON security_scans(status);
CREATE INDEX IF NOT EXISTS idx_security_scans_scan_type ON security_scans(scan_type);
CREATE INDEX IF NOT EXISTS idx_security_scans_created_at ON security_scans(created_at);

-- Create trigger for updated_at
CREATE TRIGGER update_security_scans_updated_at 
    BEFORE UPDATE ON security_scans 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add security scan status to packages table
ALTER TABLE packages ADD COLUMN IF NOT EXISTS security_scan_status VARCHAR(50) DEFAULT 'pending' 
    CHECK (security_scan_status IN ('pending', 'scanning', 'completed', 'failed', 'skipped'));

-- Add security scan summary fields to packages table
ALTER TABLE packages ADD COLUMN IF NOT EXISTS vulnerability_count INTEGER DEFAULT 0;
ALTER TABLE packages ADD COLUMN IF NOT EXISTS critical_vulnerabilities INTEGER DEFAULT 0;
ALTER TABLE packages ADD COLUMN IF NOT EXISTS high_vulnerabilities INTEGER DEFAULT 0;
ALTER TABLE packages ADD COLUMN IF NOT EXISTS medium_vulnerabilities INTEGER DEFAULT 0;
ALTER TABLE packages ADD COLUMN IF NOT EXISTS low_vulnerabilities INTEGER DEFAULT 0;

-- Create index for security scan status
CREATE INDEX IF NOT EXISTS idx_packages_security_scan_status ON packages(security_scan_status);
