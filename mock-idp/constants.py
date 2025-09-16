"""
Configuration constants for the Mock IDP service.
All hardcoded values should be defined here and imported where needed.

This module provides centralized configuration for the Mock IDP service,
following the same pattern as the main backend constants.
"""

import os

# =============================================================================
# CONFIGURATION FUNCTIONS
# =============================================================================

def get_required_env(key: str, description: str = None) -> str:
    """
    Get a required environment variable or raise an error.
    
    Args:
        key: Environment variable name
        description: Optional description for error message
        
    Returns:
        Environment variable value
        
    Raises:
        ValueError: If the environment variable is not set
    """
    value = os.getenv(key)
    if not value:
        desc = f" ({description})" if description else ""
        raise ValueError(f"Required environment variable {key}{desc} is not set")
    return value


def get_optional_env(key: str, default: str = None) -> str:
    """
    Get an optional environment variable with a default value.
    
    Args:
        key: Environment variable name
        default: Default value if not set
        
    Returns:
        Environment variable value or default
    """
    return os.getenv(key, default)


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
IDP_SECRET_KEY = get_required_env("IDP_SECRET_KEY", "Identity Provider secret key")

# OAuth & IDP Configuration
OAUTH_AUDIENCE = get_required_env("OAUTH_AUDIENCE", "OAuth audience")
OAUTH_ISSUER = get_required_env("OAUTH_ISSUER", "OAuth issuer URL")

# ADFS Configuration
ADFS_ENTITY_ID = get_optional_env("ADFS_ENTITY_ID", "http://localhost:3000")
ADFS_SSO_URL = get_optional_env("ADFS_SSO_URL", "http://localhost:8081/sso")
ADFS_CERT_PATH = get_optional_env("ADFS_CERT_PATH", "/app/certs/adfs.crt")

# =============================================================================
# FLASK CONFIGURATION
# =============================================================================

# Flask Ports & Network
IDP_PORT = int(get_required_env("IDP_PORT", "Identity Provider port"))
FRONTEND_PORT = int(get_required_env("FRONTEND_PORT", "Frontend port"))

# Hosts
LOCALHOST = get_required_env("LOCALHOST", "Localhost address") or "localhost"

# URLs (constructed from hosts and ports)
FRONTEND_URL = f"http://{LOCALHOST}:{FRONTEND_PORT}"
IDP_URL = f"http://{LOCALHOST}:{IDP_PORT}"

# Flask App Configuration
FLASK_ENV = get_optional_env("FLASK_ENV", "development")
FLASK_DEBUG = get_optional_env(
    "FLASK_DEBUG", "1" if FLASK_ENV == "development" else "0"
)