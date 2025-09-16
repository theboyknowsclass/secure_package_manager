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


def get_optional_env(key: str, default: str | None = None) -> str | None:
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


def get_optional_env_int(key: str, default: str) -> int:
    """
    Get an optional environment variable as an integer with a default value.

    Args:
        key: Environment variable name
        default: Default value if not set

    Returns:
        Environment variable value as integer or default
    """
    value = os.getenv(key, default)
    return int(value)


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

# Application Names
APP_NAME = get_required_env("APP_NAME", "Application name")
FRONTEND_APP_NAME = get_required_env("FRONTEND_APP_NAME", "Frontend application name")

# =============================================================================
# NETWORK CONFIGURATION
# =============================================================================

# Ports
FRONTEND_PORT = int(get_required_env("FRONTEND_PORT", "Frontend port"))
API_PORT = int(get_required_env("API_PORT", "API port"))
DATABASE_PORT = int(get_required_env("DATABASE_PORT", "Database port"))
IDP_PORT = int(get_required_env("IDP_PORT", "Identity Provider port"))
NPM_REGISTRY_PORT = int(get_required_env("NPM_REGISTRY_PORT", "NPM registry port"))
TRIVY_PORT = int(get_required_env("TRIVY_PORT", "Trivy port"))

# Hosts
LOCALHOST = get_required_env("LOCALHOST", "Localhost address") or "localhost"
DOCKER_HOST = get_required_env("DOCKER_HOST", "Docker host address") or "localhost"

# URLs (constructed from hosts and ports)
FRONTEND_URL = f"http://{LOCALHOST}:{FRONTEND_PORT}"
API_URL = f"http://{LOCALHOST}:{API_PORT}"
DATABASE_URL = get_required_env("DATABASE_URL", "Database connection URL")
IDP_URL = f"http://{LOCALHOST}:{IDP_PORT}"
NPM_REGISTRY_URL = f"http://{LOCALHOST}:{NPM_REGISTRY_PORT}"
TRIVY_URL = get_required_env("TRIVY_URL", "Trivy service URL")
SECURE_REPO_URL = get_required_env("SECURE_REPO_URL", "Secure repository URL")
NPM_PROXY_URL = get_optional_env("NPM_PROXY_URL", "https://registry.npmjs.org")

# =============================================================================
# SECURITY CONFIGURATION
# =============================================================================

# JWT Configuration
JWT_SECRET = get_required_env("JWT_SECRET", "JWT signing secret")
FLASK_SECRET_KEY = get_required_env("FLASK_SECRET_KEY", "Flask secret key")
IDP_SECRET_KEY = get_required_env("IDP_SECRET_KEY", "Identity Provider secret key")

# OAuth Configuration
OAUTH_AUDIENCE = get_required_env("OAUTH_AUDIENCE", "OAuth audience")
OAUTH_ISSUER = get_required_env("OAUTH_ISSUER", "OAuth issuer URL")

# =============================================================================
# FLASK CONFIGURATION
# =============================================================================

# Flask App Configuration
FLASK_ENV = get_optional_env("FLASK_ENV", "development")
FLASK_DEBUG = get_optional_env(
    "FLASK_DEBUG", "1" if FLASK_ENV == "development" else "0"
)
MAX_CONTENT_LENGTH = get_optional_env_int(
    "MAX_CONTENT_LENGTH", "16777216"
)  # 16MB default
SQLALCHEMY_TRACK_MODIFICATIONS = False  # Disable for performance

# =============================================================================
# TRIVY CONFIGURATION
# =============================================================================

# Trivy Service Configuration
TRIVY_TIMEOUT = get_optional_env_int("TRIVY_TIMEOUT", "300")  # 5 minutes default
TRIVY_MAX_RETRIES = get_optional_env_int("TRIVY_MAX_RETRIES", "3")

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
INTERNAL_IDP_URL = f"http://idp:{IDP_PORT}"
INTERNAL_NPM_REGISTRY_URL = f"http://npm-registry:{NPM_REGISTRY_PORT}"
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


def validate_config() -> None:
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
