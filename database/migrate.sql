-- Migration script to add package_references table
-- Run this if the table doesn't exist

-- Create package_references table if it doesn't exist
CREATE TABLE IF NOT EXISTS package_references (
    id SERIAL PRIMARY KEY,
    package_request_id INTEGER REFERENCES package_requests(id),
    name VARCHAR(255) NOT NULL,
    version VARCHAR(100) NOT NULL,
    npm_url VARCHAR(500),
    integrity VARCHAR(255),
    status VARCHAR(50) DEFAULT 'referenced' CHECK (status IN ('referenced', 'already_validated', 'needs_validation')),
    existing_package_id INTEGER REFERENCES packages(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for package_references if they don't exist
CREATE INDEX IF NOT EXISTS idx_package_references_status ON package_references(status);
CREATE INDEX IF NOT EXISTS idx_package_references_name_version ON package_references(name, version);

-- Update the status check constraint for packages to include new statuses
ALTER TABLE packages DROP CONSTRAINT IF EXISTS packages_status_check;
ALTER TABLE packages ADD CONSTRAINT packages_status_check 
    CHECK (status IN ('requested', 'downloading', 'downloaded', 'validating', 'validated', 'approved', 'published', 'rejected', 'already_validated'));
