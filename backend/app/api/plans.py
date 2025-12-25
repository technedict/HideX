"""Transaction plan endpoints."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends

from ..core.service import HideXService
from ..schemas.requests import CreatePlanRequest, SimulatePlanRequest, ExecutePlanRequest
from ..schemas.responses import (
    PlanResponse,
    StepResponse,
    RiskScoreResponse,
    RiskFactorResponse,
    PolicyValidationResponse,
    PolicyViolationResponse,
)
from .deps import get_service

router = APIRouter(prefix="/plans", tags=["plans"])

# In-memory plan storage (would use database in production)
_plans: dict = {}


def _plan_to_response(plan) -> PlanResponse:
    """Convert plan to response model."""
    return PlanResponse(
        id=plan.id,
        name=plan.name,
        description=plan.description,
        source_address=plan.source_address,
        destination_address=plan.destination_address,
        total_amount_formatted=plan.total_amount_formatted,
        chain=plan.chain,
        steps=[
            StepResponse(
                id=s.id,
                order=s.order,
                from_address=s.from_address,
                to_address=s.to_address,
                amount_formatted=s.amount_formatted,
                delay_seconds=s.delay_seconds,
                status=s.status.value if hasattr(s.status, 'value') else str(s.status),
                tx_hash=s.tx_hash,
                description=s.description,
            )
            for s in plan.steps
        ],
        status=plan.status.value if hasattr(plan.status, 'value') else str(plan.status),
        risk_score=plan.risk_score,
        risk_band=plan.risk_band,
        risk_explanation=plan.risk_explanation,
        is_policy_compliant=plan.is_policy_compliant,
        policy_violations=plan.policy_violations,
        policy_warnings=plan.policy_warnings,
        created_at=plan.created_at,
        simulated_at=plan.simulated_at,
        executed_at=plan.executed_at,
        is_dry_run=plan.is_dry_run,
    )


@router.post("", response_model=PlanResponse)
async def create_plan(
    request: CreatePlanRequest,
    service: HideXService = Depends(get_service)
):
    """
    Create a transaction plan.
    
    Plan types:
    - simple: Direct single-hop transfer (not privacy-optimized)
    - multi_hop: Route through transit wallets
    - split: Split amount across multiple paths
    
    All plans are created in dry-run mode by default.
    """
    try:
        if request.plan_type == "simple":
            plan = service.create_simple_plan(
                source_address=request.source_address,
                destination_address=request.destination_address,
                amount_wei=request.amount_wei,
                chain=request.chain,
                name=request.name,
            )
        elif request.plan_type == "multi_hop":
            plan = service.create_multi_hop_plan(
                source_address=request.source_address,
                destination_address=request.destination_address,
                amount_wei=request.amount_wei,
                num_hops=request.num_hops,
                chain=request.chain,
                name=request.name,
                min_delay_seconds=request.min_delay_seconds,
                max_delay_seconds=request.max_delay_seconds,
            )
        elif request.plan_type == "split":
            plan = service.create_split_plan(
                source_address=request.source_address,
                destination_address=request.destination_address,
                amount_wei=request.amount_wei,
                num_splits=request.num_splits,
                chain=request.chain,
                name=request.name,
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown plan type: {request.plan_type}"
            )
        
        # Store plan
        _plans[plan.id] = plan
        
        return _plan_to_response(plan)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{plan_id}", response_model=PlanResponse)
async def get_plan(plan_id: str):
    """Get plan by ID."""
    plan = _plans.get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return _plan_to_response(plan)


@router.post("/{plan_id}/simulate", response_model=PlanResponse)
async def simulate_plan(
    plan_id: str,
    request: SimulatePlanRequest = None,
    service: HideXService = Depends(get_service)
):
    """
    Simulate a transaction plan.
    
    This runs the plan through:
    1. Risk assessment
    2. Policy validation
    3. Execution simulation
    
    No actual transactions are executed.
    """
    plan = _plans.get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    try:
        # Run simulation
        plan = service.simulate_plan(plan)
        _plans[plan_id] = plan
        
        return _plan_to_response(plan)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{plan_id}/risk", response_model=RiskScoreResponse)
async def get_plan_risk(
    plan_id: str,
    service: HideXService = Depends(get_service)
):
    """Get detailed risk assessment for a plan."""
    plan = _plans.get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    risk_score = service.assess_risk(plan)
    _plans[plan_id] = plan
    
    return RiskScoreResponse(
        plan_id=plan_id,
        score=risk_score.score,
        band=risk_score.band.value,
        summary=risk_score.summary,
        explanation=risk_score.explanation,
        factors=[
            RiskFactorResponse(
                name=f.name,
                score=f.score,
                explanation=f.explanation,
                remediation=f.remediation,
            )
            for f in risk_score.factors
        ],
        recommendations=risk_score.recommendations,
        warnings=risk_score.warnings,
        blockers=risk_score.blockers,
    )


@router.get("/{plan_id}/validate", response_model=PolicyValidationResponse)
async def validate_plan(
    plan_id: str,
    policy_id: Optional[str] = None,
    service: HideXService = Depends(get_service)
):
    """Validate a plan against policy."""
    plan = _plans.get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    result = service.validate_plan(plan, policy_id)
    _plans[plan_id] = plan
    
    return PolicyValidationResponse(
        policy_id=result.policy_id,
        policy_name=result.policy_name,
        plan_id=result.plan_id,
        is_valid=result.is_valid,
        is_compliant=result.is_compliant,
        violations=[
            PolicyViolationResponse(
                rule_name=v.rule_name,
                severity=v.severity,
                message=v.message,
                remediation=v.remediation,
            )
            for v in result.violations
        ],
        warnings_count=result.warnings_count,
        errors_count=result.errors_count,
    )


@router.post("/{plan_id}/execute", response_model=PlanResponse)
async def execute_plan(
    plan_id: str,
    request: ExecutePlanRequest,
    service: HideXService = Depends(get_service)
):
    """
    Execute a transaction plan.
    
    ⚠️ REQUIRES:
    1. Plan must be simulated first
    2. Explicit confirmation=True in request
    
    This will execute real blockchain transactions!
    """
    plan = _plans.get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    if not request.confirmation:
        raise HTTPException(
            status_code=400,
            detail="Execution requires explicit confirmation=True"
        )
    
    # Check risk level
    if plan.risk_score and plan.risk_score >= 67:
        if not request.accept_high_risk:
            raise HTTPException(
                status_code=400,
                detail="Plan has HIGH risk. Set accept_high_risk=True to proceed."
            )
        if not request.risk_override_reason:
            raise HTTPException(
                status_code=400,
                detail="High risk override requires a reason"
            )
    
    try:
        # Disable dry-run mode
        plan.is_dry_run = False
        
        # Execute
        plan = await service.execute_plan(plan, confirmation_override=True)
        _plans[plan_id] = plan
        
        return _plan_to_response(plan)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
