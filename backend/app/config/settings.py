"""
Application settings and configuration.

All configuration is designed for local-first operation.
No cloud dependencies are required for the MVP.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with secure defaults."""

    # Application
    app_name: str = "HideX"
    app_version: str = "0.1.0"
    debug: bool = Field(default=False, description="Enable debug mode")

    # Database (local SQLite)
    database_url: str = Field(
        default="sqlite:///./hidex.db",
        description="SQLite database URL (local only)"
    )

    # Security
    secret_key: str = Field(
        default="CHANGE_ME_IN_PRODUCTION_USE_SECURE_RANDOM_KEY",
        description="Secret key for encryption (must be changed in production)"
    )
    encryption_algorithm: str = "Fernet"

    # Paths
    data_dir: Path = Field(
        default=Path("./data"),
        description="Directory for local data storage"
    )
    keystore_dir: Path = Field(
        default=Path("./data/keystores"),
        description="Directory for encrypted keystores"
    )
    logs_dir: Path = Field(
        default=Path("./data/logs"),
        description="Directory for audit logs"
    )
    policies_dir: Path = Field(
        default=Path("./policies"),
        description="Directory for policy JSON files"
    )

    # Transaction defaults
    default_dry_run: bool = Field(
        default=True,
        description="Default to dry-run mode (simulation only)"
    )
    require_explicit_confirmation: bool = Field(
        default=True,
        description="Require explicit user confirmation for execution"
    )

    # Simulation
    simulation_seed: Optional[int] = Field(
        default=None,
        description="Seed for deterministic simulations (None for random)"
    )

    # Risk scoring thresholds
    risk_low_threshold: int = Field(default=33, ge=0, le=100)
    risk_high_threshold: int = Field(default=66, ge=0, le=100)

    # API settings
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    class Config:
        env_prefix = "HIDEX_"
        env_file = ".env"
        env_file_encoding = "utf-8"

    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        for directory in [self.data_dir, self.keystore_dir, self.logs_dir, self.policies_dir]:
            directory.mkdir(parents=True, exist_ok=True)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    settings.ensure_directories()
    return settings
