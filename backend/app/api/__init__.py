"""API routes for HideX."""

from .wallets import router as wallets_router
from .plans import router as plans_router
from .policies import router as policies_router
from .audit import router as audit_router
from .health import router as health_router

__all__ = [
    "wallets_router",
    "plans_router",
    "policies_router",
    "audit_router",
    "health_router",
]
