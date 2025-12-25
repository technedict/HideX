"""API request schemas for HideX."""

from typing import Optional
from pydantic import BaseModel, Field

from ..models.wallet import WalletRole


class InitializeWalletRequest(BaseModel):
    """Request to initialize wallet system."""
    mnemonic: Optional[str] = Field(
        default=None,
        description="Existing mnemonic phrase (generates new if not provided)"
    )


class CreateWalletRequest(BaseModel):
    """Request to create a new wallet."""
    role: WalletRole = Field(..., description="Wallet role")
    label: Optional[str] = Field(default=None, description="Optional label")
    chain: str = Field(default="ethereum", description="Blockchain network")


class CreatePlanRequest(BaseModel):
    """Request to create a transaction plan."""
    source_address: str = Field(..., description="Source wallet address")
    destination_address: str = Field(..., description="Destination address")
    amount_wei: str = Field(..., description="Amount in wei")
    chain: str = Field(default="ethereum", description="Blockchain network")
    name: Optional[str] = Field(default=None, description="Plan name")
    
    # Plan type
    plan_type: str = Field(
        default="simple",
        description="Plan type: 'simple', 'multi_hop', or 'split'"
    )
    
    # Multi-hop options
    num_hops: int = Field(default=2, ge=1, le=10, description="Number of hops")
    
    # Split options
    num_splits: int = Field(default=3, ge=2, le=10, description="Number of splits")
    
    # Timing options
    min_delay_seconds: int = Field(
        default=300,
        ge=0,
        description="Minimum delay between steps"
    )
    max_delay_seconds: int = Field(
        default=3600,
        ge=0,
        description="Maximum delay between steps"
    )


class SimulatePlanRequest(BaseModel):
    """Request to simulate a plan."""
    plan_id: str = Field(..., description="Plan ID to simulate")
    known_cex_addresses: list[str] = Field(
        default_factory=list,
        description="Known CEX addresses for contamination detection"
    )


class ExecutePlanRequest(BaseModel):
    """Request to execute a plan."""
    plan_id: str = Field(..., description="Plan ID to execute")
    confirmation: bool = Field(
        default=False,
        description="Explicit confirmation to execute"
    )
    
    # Risk override
    accept_high_risk: bool = Field(
        default=False,
        description="Accept execution despite high risk score"
    )
    risk_override_reason: Optional[str] = Field(
        default=None,
        description="Reason for accepting high risk"
    )
