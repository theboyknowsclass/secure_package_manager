-- Migration to simplify repository configuration to only source and target URLs
-- Remove unnecessary configuration items

-- Delete unnecessary configuration entries
DELETE FROM repository_config WHERE config_key IN (
    'source_repository_type',
    'target_repository_type', 
    'validation_timeout',
    'max_package_size'
);

-- Update descriptions for remaining items
UPDATE repository_config 
SET description = 'Source repository URL for package validation'
WHERE config_key = 'source_repository_url';

UPDATE repository_config 
SET description = 'Target repository URL for approved packages'
WHERE config_key = 'target_repository_url';
