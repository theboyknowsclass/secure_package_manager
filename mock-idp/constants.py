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
# SECURITY CONFIGURATION
# =============================================================================

# JWT Configuration
JWT_SECRET = get_required_env("JWT_SECRET", "JWT signing secret")
IDP_SECRET_KEY = get_required_env("IDP_SECRET_KEY", "Identity Provider secret key")

# OAuth Configuration
OAUTH_AUDIENCE = get_required_env("OAUTH_AUDIENCE", "OAuth audience")
OAUTH_ISSUER = get_required_env("OAUTH_ISSUER", "OAuth issuer URL")

# =============================================================================
# NETWORK CONFIGURATION
# =============================================================================

# Frontend URL
FRONTEND_URL = get_required_env("FRONTEND_URL", "Frontend URL")

# IDP Configuration
IDP_ENTITY_ID = get_required_env("IDP_ENTITY_ID", "IDP entity ID")
IDP_SSO_URL = get_required_env("IDP_SSO_URL", "IDP SSO URL")