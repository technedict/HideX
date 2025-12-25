"""API response schemas for HideX."""

from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field

from ..models.wallet import WalletRole, WalletState
from ..models.risk import RiskBand


class WalletResponse(BaseModel):
    """Wallet response."""
    id: str
    address: str
    role: WalletRole
    state: WalletState
    chain: str
    label: Optional[str]
    created_at: datetime
    transaction_count: int
    is_one_time: bool


class WalletListResponse(BaseModel):
    """List of wallets response."""
    wallets: list[WalletResponse]
    total: int


class StepResponse(BaseModel):
    """Transaction step response."""
    id: str
    order: int
    from_address: str
    to_address: str
    amount_formatted: str
    delay_seconds: int
    status: str
    tx_hash: Optional[str]
    description: Optional[str]


class PlanResponse(BaseModel):
    """Transaction plan response."""
    id: str
    name: Optional[str]
    description: Optional[str]
    source_address: str
    destination_address: str
    total_amount_formatted: str
    chain: str
    steps: list[StepResponse]
    status: str
    
    # Risk assessment
    risk_score: Optional[int]
    risk_band: Optional[str]
    risk_explanation: Optional[str]
    
    # Policy compliance
    is_policy_compliant: bool
    policy_violations: list[str]
    policy_warnings: list[str]
    
    # Timestamps
    created_at: datetime
    simulated_at: Optional[datetime]
    executed_at: Optional[datetime]
    
    # Mode
    is_dry_run: bool


class RiskFactorResponse(BaseModel):
    """Risk factor response."""
    name: str
    score: int
    explanation: str
    remediation: Optional[str]


class RiskScoreResponse(BaseModel):
    """Risk score response."""
    plan_id: str
    score: int
    band: str
    summary: str
    explanation: str
    factors: list[RiskFactorResponse]
    recommendations: list[str]
    warnings: list[str]
    blockers: list[str]


class PolicyViolationResponse(BaseModel):
    """Policy violation response."""
    rule_name: str
    severity: str
    message: str
    remediation: Optional[str]


class PolicyValidationResponse(BaseModel):
    """Policy validation response."""
    policy_id: str
    policy_name: str
    plan_id: str
    is_valid: bool
    is_compliant: bool
    violations: list[PolicyViolationResponse]
    warnings_count: int
    errors_count: int


class AuditEntryResponse(BaseModel):
    """Audit entry response."""
    id: str
    timestamp: datetime
    event_type: str
    summary: str
    plan_id: Optional[str]
    tx_hash: Optional[str]


class AuditLogResponse(BaseModel):
    """Audit log response."""
    id: str
    name: Optional[str]
    started_at: datetime
    ended_at: Optional[datetime]
    total_entries: int
    entries: list[AuditEntryResponse]


class ComplianceReportResponse(BaseModel):
    """Compliance report response."""
    plan_id: str
    session_id: str
    generated_at: str
    timeline: list[dict]
    policy_compliance: dict
    risk_assessment: dict
    transactions: list[dict]
    summary: dict


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
