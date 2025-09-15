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


def get_required_env(key: str, description: str = None) -> str:
    """
    Get a required environment variable or add to missing list.

    Args:
        key: Environment variable name
        description: Optional description for error message

    Returns:
        Environment variable value or None if missing
    """
    value = os.getenv(key)
    if not value:
        desc = f" ({description})" if description else ""
        _missing_env_vars.append(f"  - {key}{desc}")
        return None
    return value


def get_optional_env(key: str, default: str = None) -> str:
    """
    Get an optional environment variable with a default value.
    Only use this for truly optional configuration.

    Args:
        key: Environment variable name
        default: Default value if not set

    Returns:
        Environment variable value or default
    """
    return os.getenv(key, default)


def validate_all_required_env():
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
_missing_env_vars = []

# =============================================================================
# APPLICATION CONFIGURATION
# =============================================================================

# Application Names
APP_NAME = get_required_env("APP_NAME", "Application name")
FRONTEND_APP_NAME = get_required_env("FRONTEND_APP_NAME", "Frontend application name")

# =============================================================================
# NETWORK CONFIGURATION
# =============================================================================

# Ports
FRONTEND_PORT = int(get_required_env("FRONTEND_PORT", "Frontend port") or "3000")
API_PORT = int(get_required_env("API_PORT", "API port") or "5000")
DATABASE_PORT = int(get_required_env("DATABASE_PORT", "Database port") or "5432")
MOCK_IDP_PORT = int(get_required_env("MOCK_IDP_PORT", "Mock IDP port") or "8081")
MOCK_NPM_REGISTRY_PORT = int(
    get_required_env("MOCK_NPM_REGISTRY_PORT", "Mock NPM registry port") or "8080"
)
TRIVY_PORT = int(get_required_env("TRIVY_PORT", "Trivy port") or "4954")

# Hosts
LOCALHOST = get_required_env("LOCALHOST", "Localhost address") or "localhost"
DOCKER_HOST = get_required_env("DOCKER_HOST", "Docker host address") or "localhost"

# URLs (constructed from hosts and ports)
FRONTEND_URL = f"http://{LOCALHOST}:{FRONTEND_PORT}"
API_URL = f"http://{LOCALHOST}:{API_PORT}"
DATABASE_URL = get_required_env("DATABASE_URL", "Database connection URL")
MOCK_IDP_URL = f"http://{LOCALHOST}:{MOCK_IDP_PORT}"
MOCK_NPM_REGISTRY_URL = f"http://{LOCALHOST}:{MOCK_NPM_REGISTRY_PORT}"
TRIVY_URL = get_required_env("TRIVY_URL", "Trivy service URL")

# =============================================================================
# SECURITY CONFIGURATION
# =============================================================================

# JWT Configuration
JWT_SECRET = get_required_env("JWT_SECRET", "JWT signing secret")
FLASK_SECRET_KEY = get_required_env("FLASK_SECRET_KEY", "Flask secret key")
MOCK_IDP_SECRET_KEY = get_required_env("MOCK_IDP_SECRET_KEY", "Mock IDP secret key")

# OAuth Configuration
OAUTH_AUDIENCE = get_required_env("OAUTH_AUDIENCE", "OAuth audience")
OAUTH_ISSUER = get_required_env("OAUTH_ISSUER", "OAuth issuer URL")

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

# Database Credentials
POSTGRES_USER = get_required_env("POSTGRES_USER", "PostgreSQL username")
POSTGRES_PASSWORD = get_required_env("POSTGRES_PASSWORD", "PostgreSQL password")
POSTGRES_DB = get_required_env("POSTGRES_DB", "PostgreSQL database name")

# Internal Docker URLs (for container-to-container communication)
INTERNAL_API_URL = f"http://api:{API_PORT}"
INTERNAL_DATABASE_URL = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@db:{DATABASE_PORT}/{POSTGRES_DB}"
)
INTERNAL_MOCK_IDP_URL = f"http://mock-idp:{MOCK_IDP_PORT}"
INTERNAL_MOCK_NPM_REGISTRY_URL = f"http://mock-npm-registry:{MOCK_NPM_REGISTRY_PORT}"
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


def is_development():
    """Check if running in development mode"""
    return os.getenv("FLASK_ENV", "development") == "development"


def is_production():
    """Check if running in production mode"""
    return os.getenv("FLASK_ENV", "development") == "production"


# =============================================================================
# CONFIGURATION VALIDATION
# =============================================================================


def validate_config():
    """Validate that all required configuration is present"""
    required_vars = ["JWT_SECRET", "FLASK_SECRET_KEY", "POSTGRES_PASSWORD"]

    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )

    return True
