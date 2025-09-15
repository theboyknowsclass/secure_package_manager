-- Development database initialization
-- Fresh start every time - no migrations needed

-- Include the base schema
\i /docker-entrypoint-initdb.d/init.sql

-- Insert default admin user and development users
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

-- Insert default supported licenses with 4-tier status system (dev only)
INSERT INTO supported_licenses (name, identifier, status, created_by) VALUES
-- Always Acceptable (highest priority, no restrictions)
('MIT License', 'MIT', 'always_allowed', 1),
('BSD License', 'BSD', 'always_allowed', 1),
('Apache License 2.0', 'Apache-2.0', 'always_allowed', 1),

-- Acceptable (standard approval, may have minor restrictions)
('GNU Lesser General Public License', 'LGPL', 'allowed', 1),
('Mozilla Public License', 'MPL', 'allowed', 1),

-- Avoid (discouraged but not blocked, may have significant restrictions)
('Do What The F*ck You Want To Public License', 'WTFPL', 'avoid', 1),
('GNU General Public License v3.0', 'GPL-3.0', 'avoid', 1),
('GNU Lesser General Public License v3.0', 'LGPL-3.0', 'avoid', 1),

-- Blocked (explicitly prohibited)
('GNU General Public License', 'GPL', 'blocked', 1),
('GNU General Public License v2.0', 'GPL-2.0', 'blocked', 1),
('GNU Affero General Public License', 'AGPL', 'blocked', 1),

-- Additional development licenses
('Creative Commons Zero v1.0 Universal', 'CC0-1.0', 'allowed', 1),
('Unlicense', 'Unlicense', 'allowed', 1)
ON CONFLICT (identifier) DO NOTHING;

-- Insert default repository configuration and development config
INSERT INTO repository_config (config_key, config_value, description) VALUES
    ('source_repository_url', 'https://registry.npmjs.org/', 'Source repository URL for package downloads'),
    ('target_repository_url', 'http://localhost:8080/', 'Target repository URL for package publishing'),
    ('npm_registry_url', 'https://registry.npmjs.org/', 'NPM registry URL for development'),
    ('trivy_timeout', '300', 'Trivy scan timeout in seconds'),
    ('max_package_size_mb', '50', 'Maximum package size in MB'),
    ('dev_mode', 'true', 'Development mode flag')
ON CONFLICT (config_key) DO NOTHING;