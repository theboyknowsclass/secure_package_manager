-- Migration to add allow/block list support to existing database
-- This adds the new columns to the existing supported_licenses table

-- Add the new columns
ALTER TABLE supported_licenses 
ADD COLUMN IF NOT EXISTS list_type VARCHAR(20) DEFAULT 'allow' CHECK (list_type IN ('allow', 'block'));

ALTER TABLE supported_licenses 
ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;

-- Rename the old column to maintain compatibility
ALTER TABLE supported_licenses 
RENAME COLUMN is_approved TO is_approved_old;

-- Add the new is_approved column that references is_active
ALTER TABLE supported_licenses 
ADD COLUMN is_approved BOOLEAN GENERATED ALWAYS AS (is_active) STORED;

-- Update existing licenses to have proper list_type values
-- Set permissive licenses to 'allow' and copyleft licenses to 'block'
UPDATE supported_licenses 
SET list_type = CASE 
    WHEN is_permissive = TRUE THEN 'allow'
    ELSE 'block'
END
WHERE list_type IS NULL;

-- Update the trigger for the new column
DROP TRIGGER IF EXISTS update_supported_licenses_updated_at ON supported_licenses;
CREATE TRIGGER update_supported_licenses_updated_at 
    BEFORE UPDATE ON supported_licenses 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
