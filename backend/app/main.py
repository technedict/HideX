"""
HideX FastAPI Application
=========================

Privacy-hygiene and transaction-risk management tool for blockchain users.

⚠️ IMPORTANT DISCLAIMERS:
- This tool is NOT a mixer, tumbler, or obfuscation service
- This tool does NOT provide "untraceable" or "anonymous" transfers
- This tool does NOT include sanction bypass, KYC evasion, or illegal routing
- All behavior is explainable, auditable, and user-approved
- Default mode is SIMULATION ONLY. Execution is always opt-in.

The goal is to REDUCE TRANSACTION LINKABILITY THROUGH DISCIPLINE, NOT SECRECY.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import (
    health_router,
    wallets_router,
    plans_router,
    policies_router,
    audit_router,
)
from .config import get_settings

# Get settings
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="HideX API",
    description="""
    ## Privacy-Hygiene and Transaction-Risk Management Tool
    
    HideX helps blockchain users maintain transaction hygiene through:
    
    - **Risk Assessment**: Score transaction paths before execution
    - **Policy Enforcement**: Rule-based validation of transaction plans
    - **Wallet Management**: Role-based wallet separation and one-time addresses
    - **Route Planning**: Multi-hop and split-amount transaction strategies
    - **Audit Logging**: Immutable logs for compliance and learning
    
    ### ⚠️ Important Disclaimers
    
    - This is NOT a mixer, tumbler, or obfuscation service
    - This does NOT provide "untraceable" or "anonymous" transfers
    - All behavior is explainable, auditable, and user-approved
    - Default mode is SIMULATION ONLY
    - Execution requires explicit user confirmation
    
    ### Design Philosophy
    
    **REDUCE TRANSACTION LINKABILITY THROUGH DISCIPLINE, NOT SECRECY**
    """,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware (local development only)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(wallets_router)
app.include_router(plans_router)
app.include_router(policies_router)
app.include_router(audit_router)


@app.on_event("startup")
async def startup_event():
    """Application startup."""
    settings.ensure_directories()
    print(f"HideX API starting on {settings.api_host}:{settings.api_port}")
    print("⚠️  SIMULATION MODE ENABLED BY DEFAULT")
    print("⚠️  All execution requires explicit confirmation")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown."""
    print("HideX API shutting down")


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "HideX",
        "version": settings.app_version,
        "description": "Privacy-hygiene and transaction-risk management tool",
        "status": "running",
        "mode": "simulation" if settings.default_dry_run else "execution",
        "disclaimers": [
            "This is NOT a mixer, tumbler, or obfuscation service",
            "All behavior is explainable, auditable, and user-approved",
            "Execution requires explicit confirmation",
        ],
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "wallets": "/wallets",
            "plans": "/plans",
            "policies": "/policies",
            "audit": "/audit",
        },
    }
