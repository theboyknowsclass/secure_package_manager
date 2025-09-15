-- Development cleanup script
-- This removes all data but preserves the schema and dev users

-- Clear package-related data
DELETE FROM security_scans;
DELETE FROM package_validations;
DELETE FROM package_references;
DELETE FROM packages;
DELETE FROM package_requests;
DELETE FROM applications WHERE name NOT IN ('secure-package-manager-frontend');

-- Clear audit log (optional - keep for debugging)
-- DELETE FROM audit_log;

-- Reset auto-increment sequences
ALTER SEQUENCE security_scans_id_seq RESTART WITH 1;
ALTER SEQUENCE package_validations_id_seq RESTART WITH 1;
ALTER SEQUENCE package_references_id_seq RESTART WITH 1;
ALTER SEQUENCE packages_id_seq RESTART WITH 1;
ALTER SEQUENCE package_requests_id_seq RESTART WITH 1;
ALTER SEQUENCE applications_id_seq RESTART WITH 1;

-- Keep development users and licenses intact
-- Keep repository config intact

-- Verify cleanup
SELECT 
    'security_scans' as table_name, COUNT(*) as count FROM security_scans
UNION ALL
SELECT 'package_validations', COUNT(*) FROM package_validations
UNION ALL
SELECT 'package_references', COUNT(*) FROM package_references
UNION ALL
SELECT 'packages', COUNT(*) FROM packages
UNION ALL
SELECT 'package_requests', COUNT(*) FROM package_requests
UNION ALL
SELECT 'applications', COUNT(*) FROM applications
UNION ALL
SELECT 'users', COUNT(*) FROM users
UNION ALL
SELECT 'supported_licenses', COUNT(*) FROM supported_licenses;
