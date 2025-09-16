"""
Centralized configuration constants for the Secure Package Manager.
All hardcoded values should be defined here and imported where needed.

This module enforces that all configuration comes from environment variables
to prevent accidental use of development values in production.
"""

import os

# =============================================================================
# CONFIGURATION VALIDATION
# =============================================================================


def get_required_env(key: str, description: str | None = None) -> str:
    """
    Get a required environment variable or add to missing list.

    Args:
        key: Environment variable name
        description: Optional description for error message

    Returns:
        Environment variable value (guaranteed to be non-None)
    """
    value = os.getenv(key)
    if not value:
        desc = f" ({description})" if description else ""
        _missing_env_vars.append(f"  - {key}{desc}")
        return ""  # Return empty string as placeholder
    return value


def get_required_env_int(key: str, description: str | None = None) -> int:
    """
    Get a required environment variable as an integer or add to missing list.

    Args:
        key: Environment variable name
        description: Optional description for error message

    Returns:
        Environment variable value as integer (guaranteed to be valid)
    """
    value = os.getenv(key)
    if not value:
        desc = f" ({description})" if description else ""
        _missing_env_vars.append(f"  - {key}{desc}")
        return 0  # Return 0 as placeholder (will be caught by validation)
    
    try:
        return int(value)
    except ValueError:
        desc = f" ({description})" if description else ""
        _missing_env_vars.append(f"  - {key}{desc} (invalid integer value: '{value}')")
        return 0  # Return 0 as placeholder


def validate_all_required_env() -> None:
    """
    Validate that all required environment variables are set.
    Raises ValueError with all missing variables if any are missing.
    """
    if _missing_env_vars:
        error_msg = "Missing required environment variables:\n" + "\n".join(
            _missing_env_vars
        )
        error_msg += "\n\nPlease set these environment variables before starting the application."
        error_msg += "\nSee env.example for reference values."
        raise ValueError(error_msg)


# Global list to collect missing environment variables
_missing_env_vars: list[str] = []

# =============================================================================
# APPLICATION CONFIGURATION
# =============================================================================

# Application Name (used for both backend and frontend)
APP_NAME = get_required_env("APP_NAME", "Application name")
FRONTEND_APP_NAME = f"{APP_NAME}-frontend"

# =============================================================================
# SECURITY CONFIGURATION
# =============================================================================

# JWT & Flask Secrets
JWT_SECRET = get_required_env("JWT_SECRET", "JWT signing secret")
FLASK_SECRET_KEY = get_required_env("FLASK_SECRET_KEY", "Flask secret key")
IDP_SECRET_KEY = get_required_env("IDP_SECRET_KEY", "Identity Provider secret key")

# OAuth & IDP Configuration
OAUTH_AUDIENCE = get_required_env("OAUTH_AUDIENCE", "OAuth audience")
OAUTH_ISSUER = get_required_env("OAUTH_ISSUER", "OAuth issuer URL")
IDP_PORT = get_required_env_int("IDP_PORT", "Identity Provider port")

# ADFS Configuration
ADFS_ENTITY_ID = get_required_env("ADFS_ENTITY_ID", "ADFS entity ID")
ADFS_SSO_URL = get_required_env("ADFS_SSO_URL", "ADFS SSO URL")
ADFS_CERT_PATH = get_required_env("ADFS_CERT_PATH", "ADFS certificate path")

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

# Database Port & Connection
DATABASE_PORT = get_required_env_int("DATABASE_PORT", "PostgreSQL database port")
DATABASE_URL = get_required_env("DATABASE_URL", "Database connection URL")

# Database Credentials
POSTGRES_USER = get_required_env("POSTGRES_USER", "PostgreSQL username")
POSTGRES_PASSWORD = get_required_env("POSTGRES_PASSWORD", "PostgreSQL password")
POSTGRES_DB = get_required_env("POSTGRES_DB", "PostgreSQL database name")

# =============================================================================
# EXTERNAL SERVICES CONFIGURATION
# =============================================================================

# Trivy Service
TRIVY_PORT = get_required_env_int("TRIVY_PORT", "Trivy security scanner port")
TRIVY_URL = get_required_env("TRIVY_URL", "Trivy service URL")
TRIVY_TIMEOUT = get_required_env_int("TRIVY_TIMEOUT", "Trivy timeout in seconds")
TRIVY_MAX_RETRIES = get_required_env_int("TRIVY_MAX_RETRIES", "Trivy maximum retry attempts")

# Repository Configuration
SOURCE_REPOSITORY_URL = get_required_env("SOURCE_REPOSITORY_URL", "Source repository URL (e.g., https://registry.npmjs.org)")
TARGET_REPOSITORY_URL = get_required_env("TARGET_REPOSITORY_URL", "Target repository URL (e.g., http://localhost:8080)")

# =============================================================================
# FLASK CONFIGURATION
# =============================================================================

# Flask Ports & Network
API_PORT = get_required_env_int("API_PORT", "Backend API port")
FRONTEND_PORT = get_required_env_int("FRONTEND_PORT", "Frontend application port")

# Hosts
LOCALHOST = get_required_env("LOCALHOST", "Localhost hostname")
DOCKER_HOST = get_required_env("DOCKER_HOST", "Docker hostname")

# URLs (constructed from hosts and ports)
FRONTEND_URL = f"http://{LOCALHOST}:{FRONTEND_PORT}"
API_URL = f"http://{LOCALHOST}:{API_PORT}"
IDP_URL = f"http://{LOCALHOST}:{IDP_PORT}"

# Flask App Configuration
FLASK_ENV = get_required_env("FLASK_ENV", "Flask environment (development/production)")
FLASK_DEBUG = get_required_env("FLASK_DEBUG", "Flask debug mode (0/1)")
MAX_CONTENT_LENGTH = get_required_env_int("MAX_CONTENT_LENGTH", "Maximum content length in bytes")
SQLALCHEMY_TRACK_MODIFICATIONS = False  # Disable for performance


# Internal Docker URLs (for container-to-container communication)
INTERNAL_API_URL = f"http://api:{API_PORT}"
INTERNAL_IDP_URL = f"http://idp:{IDP_PORT}"
INTERNAL_TRIVY_URL = f"http://trivy:{TRIVY_PORT}"

# =============================================================================
# DEFAULT USERS (Development Only)
# =============================================================================

# Default admin credentials (should only be used in development)
DEFAULT_ADMIN_USERNAME = get_required_env(
    "DEFAULT_ADMIN_USERNAME", "Default admin username"
)
DEFAULT_ADMIN_PASSWORD = get_required_env(
    "DEFAULT_ADMIN_PASSWORD", "Default admin password"
)
DEFAULT_ADMIN_EMAIL = get_required_env("DEFAULT_ADMIN_EMAIL", "Default admin email")

# =============================================================================
# ENVIRONMENT DETECTION
# =============================================================================


def is_development() -> bool:
    """Check if running in development mode"""
    return os.getenv("FLASK_ENV", "development") == "development"


def is_production() -> bool:
    """Check if running in production mode"""
    return os.getenv("FLASK_ENV", "development") == "production"


# =============================================================================
# CONFIGURATION VALIDATION
# =============================================================================


# Validate all required environment variables at module load time
# Only validate if not running as a worker (workers may not need all variables)
import os
if not os.getenv('WORKER_TYPE'):
    validate_all_required_env()
