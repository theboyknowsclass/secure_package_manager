-- Migration to remove redundant is_admin column
-- This migration removes the is_admin column since we now use role-based access control

-- Drop the is_admin column from users table
ALTER TABLE users DROP COLUMN IF EXISTS is_admin;
