-- Migration to add role-based access control
-- Add role column to users table

-- Add role column
ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'user' NOT NULL;

-- Add check constraint for valid roles
ALTER TABLE users ADD CONSTRAINT users_role_check CHECK (role IN ('user', 'approver', 'admin'));

-- Update existing admin users to have admin role
UPDATE users SET role = 'admin' WHERE is_admin = TRUE;

-- Update existing non-admin users to have user role (if any exist)
UPDATE users SET role = 'user' WHERE is_admin = FALSE OR is_admin IS NULL;

-- Create index for role-based queries
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
