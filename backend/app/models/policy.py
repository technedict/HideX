"""
Policy models for HideX.

Policies are:
- Rule-based and deterministic
- Loaded from human-readable JSON files
- Validated against a schema
- Never hard-coded
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field


class PolicyRuleType(str, Enum):
    """Types of policy rules."""
    NO_ADDRESS_REUSE = "no_address_reuse"
    MIN_DELAY = "min_delay"
    MAX_DELAY = "max_delay"
    NO_SAME_BLOCK = "no_same_block"
    ROLE_SEPARATION = "role_separation"
    MAX_AMOUNT_SIMILARITY = "max_amount_similarity"
    MIN_HOPS = "min_hops"
    MAX_HOPS = "max_hops"
    CHAIN_RESTRICTION = "chain_restriction"
    TIME_WINDOW_RESTRICTION = "time_window_restriction"


class PolicyRule(BaseModel):
    """
    Individual policy rule.
    
    Rules are evaluated against transaction plans to determine compliance.
    """
    id: str = Field(..., description="Unique rule identifier")
    type: PolicyRuleType
    name: str = Field(..., description="Human-readable rule name")
    description: str = Field(..., description="What this rule enforces")
    
    # Rule configuration
    enabled: bool = Field(default=True)
    severity: str = Field(
        default="warning",
        description="'warning' or 'error' (blocks execution)"
    )
    
    # Rule parameters (type-specific)
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Rule-specific parameters"
    )
    
    # Metadata
    rationale: Optional[str] = Field(
        default=None,
        description="Why this rule exists"
    )


class Policy(BaseModel):
    """
    Complete policy configuration.
    
    Policies define the hygiene rules that transaction plans must follow.
    """
    id: str = Field(..., description="Unique policy identifier")
    name: str = Field(..., description="Policy name")
    version: str = Field(default="1.0.0")
    description: Optional[str] = Field(default=None)
    
    # Rules
    rules: list[PolicyRule] = Field(default_factory=list)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)
    author: Optional[str] = Field(default=None)
    
    # Settings
    strict_mode: bool = Field(
        default=False,
        description="If true, all warnings become errors"
    )
    allow_override: bool = Field(
        default=True,
        description="If true, user can override warnings"
    )


class PolicyViolation(BaseModel):
    """Record of a policy rule violation."""
    rule_id: str
    rule_name: str
    severity: str  # "warning" or "error"
    message: str
    details: Optional[dict] = Field(default=None)
    remediation: Optional[str] = Field(default=None)


class PolicyValidationResult(BaseModel):
    """Result of validating a transaction plan against a policy."""
    policy_id: str
    policy_name: str
    plan_id: str
    
    is_valid: bool = Field(..., description="True if no errors")
    is_compliant: bool = Field(..., description="True if no errors or warnings")
    
    violations: list[PolicyViolation] = Field(default_factory=list)
    warnings_count: int = Field(default=0)
    errors_count: int = Field(default=0)
    
    validated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def has_errors(self) -> bool:
        """Check if there are blocking errors."""
        return self.errors_count > 0
    
    def has_warnings(self) -> bool:
        """Check if there are warnings."""
        return self.warnings_count > 0
