"""Shared dependencies for HideX API."""

from typing import Optional

from ..core.service import HideXService


# Shared service instance
_shared_service: Optional[HideXService] = None


def get_service() -> HideXService:
    """Get or create shared service instance."""
    global _shared_service
    if _shared_service is None:
        _shared_service = HideXService()
    return _shared_service


def reset_service() -> None:
    """Reset the shared service (for testing)."""
    global _shared_service
    _shared_service = None
