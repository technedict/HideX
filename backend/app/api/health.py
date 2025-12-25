"""Health check endpoints."""

from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "HideX",
        "version": "0.1.0",
    }


@router.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    return {
        "status": "ready",
        "components": {
            "policy_engine": "ready",
            "wallet_manager": "ready",
            "risk_engine": "ready",
            "routing_planner": "ready",
            "audit_logger": "ready",
        },
    }
