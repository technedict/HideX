"""
Risk scoring models for HideX.

All risk scores are:
- Deterministic (same inputs = same output)
- Explainable (no black-box ML)
- Transparent (all factors documented)
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class RiskBand(str, Enum):
    """Risk classification bands."""
    LOW = "LOW"  # 0-33
    MEDIUM = "MEDIUM"  # 34-66
    HIGH = "HIGH"  # 67-100


class RiskFactorType(str, Enum):
    """Types of risk factors considered."""
    SOURCE_CONTAMINATION = "source_contamination"
    TIMING_CORRELATION = "timing_correlation"
    AMOUNT_SIMILARITY = "amount_similarity"
    ADDRESS_REUSE = "address_reuse"
    CROSS_CHAIN_HEURISTIC = "cross_chain_heuristic"
    SAME_BLOCK_ACTIVITY = "same_block_activity"
    ROUND_AMOUNT = "round_amount"
    GAS_PATTERN = "gas_pattern"


class RiskFactor(BaseModel):
    """
    Individual risk factor with explanation.
    
    Every risk factor must be explainable to the user.
    """
    type: RiskFactorType
    name: str = Field(..., description="Human-readable factor name")
    score: int = Field(..., ge=0, le=100, description="Factor-specific score")
    weight: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Weight in overall calculation"
    )
    explanation: str = Field(..., description="Human-readable explanation")
    details: Optional[dict] = Field(
        default=None,
        description="Additional details for transparency"
    )
    remediation: Optional[str] = Field(
        default=None,
        description="Suggestion to reduce this risk"
    )


class RiskScore(BaseModel):
    """
    Complete risk assessment for a transaction plan.
    
    Design principle: Every score must be explainable.
    """
    plan_id: str
    
    # Overall score
    score: int = Field(..., ge=0, le=100)
    band: RiskBand
    
    # Individual factors
    factors: list[RiskFactor] = Field(default_factory=list)
    
    # Summary
    summary: str = Field(..., description="One-line summary of risk")
    explanation: str = Field(..., description="Detailed explanation")
    
    # Recommendations
    recommendations: list[str] = Field(default_factory=list)
    
    # Warnings and blockers
    warnings: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(
        default_factory=list,
        description="Issues that should block execution"
    )
    
    # Metadata
    calculated_at: datetime = Field(default_factory=datetime.utcnow)
    simulation_seed: Optional[int] = Field(
        default=None,
        description="Seed used for deterministic simulation"
    )
    
    def is_acceptable(self, max_score: int = 66) -> bool:
        """Check if risk is acceptable based on threshold."""
        return self.score <= max_score and len(self.blockers) == 0
