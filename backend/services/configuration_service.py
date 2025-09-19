"""Configuration Service.

Handles application configuration and environment variable management.
"""

import logging
import os
from typing import List

logger = logging.getLogger(__name__)


class ConfigurationService:
    """Service for managing application configuration."""

    def is_configuration_complete(self) -> bool:
        """Check if repository configuration is complete."""
        source_repo_url = os.getenv("SOURCE_REPOSITORY_URL")
        target_repo_url = os.getenv("TARGET_REPOSITORY_URL")
        return bool(source_repo_url and target_repo_url)

    def get_missing_config_keys(self) -> List[str]:
        """Get list of missing configuration keys."""
        missing = []
        if not os.getenv("SOURCE_REPOSITORY_URL"):
            missing.append("SOURCE_REPOSITORY_URL")
        if not os.getenv("TARGET_REPOSITORY_URL"):
            missing.append("TARGET_REPOSITORY_URL")
        return missing

    @property
    def source_repo_url(self) -> str:
        """Get source repository URL."""
        return os.getenv("SOURCE_REPOSITORY_URL", "")

    @property
    def target_repo_url(self) -> str:
        """Get target repository URL."""
        return os.getenv("TARGET_REPOSITORY_URL", "")
