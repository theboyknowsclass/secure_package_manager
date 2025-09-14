-- Migration to add repository configuration table and default values

-- Create repository_config table if it doesn't exist
CREATE TABLE IF NOT EXISTS repository_config (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add trigger for updated_at
CREATE TRIGGER update_repository_config_updated_at 
    BEFORE UPDATE ON repository_config 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default repository configuration values
INSERT INTO repository_config (config_key, config_value, description) VALUES
('source_repository_url', 'https://registry.npmjs.org/', 'Source repository URL for package downloads'),
('target_repository_url', 'http://localhost:8080/', 'Target repository URL for package publishing')
ON CONFLICT (config_key) DO NOTHING;
