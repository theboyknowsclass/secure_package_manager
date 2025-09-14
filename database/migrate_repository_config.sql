-- Migration to add repository configuration
-- Add repository configuration table

CREATE TABLE IF NOT EXISTS repository_config (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default repository configurations
INSERT INTO repository_config (config_key, config_value, description) VALUES
('source_repository_url', 'https://pypi.org/simple/', 'Source repository URL for package validation'),
('target_repository_url', 'https://your-company-pypi.com/simple/', 'Target repository URL for approved packages'),
('source_repository_type', 'pypi', 'Type of source repository (pypi, npm, etc.)'),
('target_repository_type', 'pypi', 'Type of target repository (pypi, npm, etc.)'),
('validation_timeout', '300', 'Package validation timeout in seconds'),
('max_package_size', '100', 'Maximum package size in MB')
ON CONFLICT (config_key) DO NOTHING;

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_repository_config_key ON repository_config(config_key);
