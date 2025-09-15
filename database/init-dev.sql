-- Development database initialization
-- Fresh start every time - no migrations needed

-- Include the base schema
\i init.sql

-- Insert development users
INSERT INTO users (username, email, full_name, role) VALUES
    ('admin', 'admin@company.com', 'System Administrator', 'admin'),
    ('approver', 'approver@company.com', 'Package Approver', 'approver'),
    ('developer', 'dev@company.com', 'Package Developer', 'user'),
    ('tester', 'tester@company.com', 'QA Tester', 'user')
ON CONFLICT (username) DO NOTHING;

-- Insert development applications
INSERT INTO applications (name, version, description, created_by) VALUES
    ('secure-package-manager-frontend', '0.0.0', 'Frontend application', 1),
    ('test-application', '1.0.0', 'Test application for development', 3),
    ('demo-app', '2.1.0', 'Demo application', 4)
ON CONFLICT (name, version) DO NOTHING;

-- Insert additional development licenses
INSERT INTO supported_licenses (name, identifier, status, created_by) VALUES
    ('GNU General Public License v3.0', 'GPL-3.0', 'avoid', 1),
    ('GNU Lesser General Public License v3.0', 'LGPL-3.0', 'avoid', 1),
    ('Creative Commons Zero v1.0 Universal', 'CC0-1.0', 'allowed', 1),
    ('Unlicense', 'Unlicense', 'allowed', 1)
ON CONFLICT (identifier) DO NOTHING;

-- Insert development repository config
INSERT INTO repository_config (config_key, config_value, description) VALUES
    ('npm_registry_url', 'https://registry.npmjs.org/', 'NPM registry URL for development'),
    ('trivy_timeout', '300', 'Trivy scan timeout in seconds'),
    ('max_package_size_mb', '50', 'Maximum package size in MB'),
    ('dev_mode', 'true', 'Development mode flag')
ON CONFLICT (config_key) DO NOTHING;