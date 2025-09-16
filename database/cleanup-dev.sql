-- Development cleanup script
-- This removes all data but preserves the schema and dev users

-- Clear package-related data (in correct order due to foreign key constraints)
DELETE FROM security_scans;
DELETE FROM package_status;
DELETE FROM request_packages;
DELETE FROM packages;
DELETE FROM requests;

-- Clear audit log (optional - keep for debugging)
-- DELETE FROM audit_log;

-- Reset auto-increment sequences
ALTER SEQUENCE security_scans_id_seq RESTART WITH 1;
ALTER SEQUENCE package_status_id_seq RESTART WITH 1;
ALTER SEQUENCE packages_id_seq RESTART WITH 1;
ALTER SEQUENCE requests_id_seq RESTART WITH 1;

-- Keep development users and licenses intact
-- Keep supported_licenses intact

-- Verify cleanup
SELECT 
    'security_scans' as table_name, COUNT(*) as count FROM security_scans
UNION ALL
SELECT 'package_status', COUNT(*) FROM package_status
UNION ALL
SELECT 'request_packages', COUNT(*) FROM request_packages
UNION ALL
SELECT 'packages', COUNT(*) FROM packages
UNION ALL
SELECT 'requests', COUNT(*) FROM requests
UNION ALL
SELECT 'users', COUNT(*) FROM users
UNION ALL
SELECT 'supported_licenses', COUNT(*) FROM supported_licenses;