-- Clean up all package-related data for fresh testing
-- This will clear all tables and reset their auto-increment sequences

-- Clear package validations first (due to foreign key constraints)
DELETE FROM package_validations;

-- Clear package references
DELETE FROM package_references;

-- Clear packages
DELETE FROM packages;

-- Clear package requests
DELETE FROM package_requests;

-- Clear applications (if you want to start completely fresh)
DELETE FROM applications;

-- Reset auto-increment sequences
ALTER SEQUENCE package_validations_id_seq RESTART WITH 1;
ALTER SEQUENCE package_references_id_seq RESTART WITH 1;
ALTER SEQUENCE packages_id_seq RESTART WITH 1;
ALTER SEQUENCE package_requests_id_seq RESTART WITH 1;
ALTER SEQUENCE applications_id_seq RESTART WITH 1;

-- Verify tables are empty
SELECT 'package_validations' as table_name, COUNT(*) as count FROM package_validations
UNION ALL
SELECT 'package_references', COUNT(*) FROM package_references
UNION ALL
SELECT 'packages', COUNT(*) FROM packages
UNION ALL
SELECT 'package_requests', COUNT(*) FROM package_requests
UNION ALL
SELECT 'applications', COUNT(*) FROM applications; 