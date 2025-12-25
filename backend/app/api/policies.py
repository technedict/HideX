"""Policy management endpoints."""

from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
import json

from ..core.service import HideXService
from ..modules.policy_engine import create_default_policy
from .deps import get_service

router = APIRouter(prefix="/policies", tags=["policies"])


@router.get("")
async def list_policies(service: HideXService = Depends(get_service)):
    """List all loaded policies."""
    policies = service.list_policies()
    return {
        "policies": [
            {
                "id": p.id,
                "name": p.name,
                "version": p.version,
                "description": p.description,
                "rules_count": len(p.rules),
                "strict_mode": p.strict_mode,
            }
            for p in policies
        ],
        "total": len(policies),
    }


@router.get("/{policy_id}")
async def get_policy(
    policy_id: str,
    service: HideXService = Depends(get_service)
):
    """Get policy by ID with full details."""
    policy = service.get_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    return {
        "id": policy.id,
        "name": policy.name,
        "version": policy.version,
        "description": policy.description,
        "strict_mode": policy.strict_mode,
        "allow_override": policy.allow_override,
        "rules": [
            {
                "id": r.id,
                "type": r.type.value,
                "name": r.name,
                "description": r.description,
                "enabled": r.enabled,
                "severity": r.severity,
                "parameters": r.parameters,
                "rationale": r.rationale,
            }
            for r in policy.rules
        ],
    }


@router.post("/{policy_id}/activate")
async def activate_policy(
    policy_id: str,
    service: HideXService = Depends(get_service)
):
    """Set a policy as the active policy for validation."""
    try:
        service.set_active_policy(policy_id)
        return {"success": True, "message": f"Policy {policy_id} is now active"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/default/template")
async def get_default_policy_template():
    """
    Get the default policy template.
    
    Use this as a starting point for custom policies.
    """
    policy = create_default_policy()
    return {
        "id": policy.id,
        "name": policy.name,
        "version": policy.version,
        "description": policy.description,
        "strict_mode": policy.strict_mode,
        "allow_override": policy.allow_override,
        "rules": [
            {
                "id": r.id,
                "type": r.type.value,
                "name": r.name,
                "description": r.description,
                "enabled": r.enabled,
                "severity": r.severity,
                "parameters": r.parameters,
                "rationale": r.rationale,
            }
            for r in policy.rules
        ],
    }
