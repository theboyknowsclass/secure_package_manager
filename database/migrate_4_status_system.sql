-- Migration to update license system to support 4 statuses
-- This updates the existing supported_licenses table

-- Add the new status column
ALTER TABLE supported_licenses 
ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'allowed' CHECK (status IN ('always_allowed', 'allowed', 'avoid', 'blocked'));

-- Migrate existing data from list_type to status
UPDATE supported_licenses 
SET status = CASE 
    WHEN list_type = 'allow' THEN 'allowed'
    WHEN list_type = 'block' THEN 'blocked'
    ELSE 'allowed'
END
WHERE status IS NULL;

-- Update specific licenses to better statuses based on their characteristics
UPDATE supported_licenses 
SET status = 'always_allowed'
WHERE identifier IN ('MIT', 'Apache-2.0', 'BSD-2-Clause', 'ISC', 'Unlicense', 'CC0-1.0');

UPDATE supported_licenses 
SET status = 'avoid'
WHERE identifier IN ('MPL-2.0', 'LGPL-3.0');

-- Drop the old list_type column
ALTER TABLE supported_licenses DROP COLUMN IF EXISTS list_type;

-- Update the trigger for the new column
DROP TRIGGER IF EXISTS update_supported_licenses_updated_at ON supported_licenses;
CREATE TRIGGER update_supported_licenses_updated_at 
    BEFORE UPDATE ON supported_licenses 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
