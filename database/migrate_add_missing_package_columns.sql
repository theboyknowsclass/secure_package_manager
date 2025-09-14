-- Migration to add missing columns to packages table
-- This migration adds the missing columns that are defined in the model but not in the database

-- Add missing columns to packages table
ALTER TABLE packages ADD COLUMN IF NOT EXISTS security_scan_status VARCHAR(50) DEFAULT 'pending' CHECK (security_scan_status IN ('pending', 'scanning', 'completed', 'failed', 'skipped'));
ALTER TABLE packages ADD COLUMN IF NOT EXISTS vulnerability_count INTEGER DEFAULT 0;
ALTER TABLE packages ADD COLUMN IF NOT EXISTS critical_vulnerabilities INTEGER DEFAULT 0;
ALTER TABLE packages ADD COLUMN IF NOT EXISTS high_vulnerabilities INTEGER DEFAULT 0;
ALTER TABLE packages ADD COLUMN IF NOT EXISTS medium_vulnerabilities INTEGER DEFAULT 0;
ALTER TABLE packages ADD COLUMN IF NOT EXISTS low_vulnerabilities INTEGER DEFAULT 0;

-- Create index for security_scan_status
CREATE INDEX IF NOT EXISTS idx_packages_security_scan_status ON packages(security_scan_status);
