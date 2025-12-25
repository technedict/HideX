"""
Wallet models for HideX.

Implements deterministic HD wallet generation with role-based separation.
Keys are stored locally only and never transmitted.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class WalletRole(str, Enum):
    """
    Wallet roles for operational separation.
    
    - FUNDING: Source wallets (may have CEX contamination)
    - TRANSIT: Intermediate wallets for breaking direct links
    - DESTINATION: Final destination wallets (clean addresses)
    """
    FUNDING = "funding"
    TRANSIT = "transit"
    DESTINATION = "destination"


class WalletState(str, Enum):
    """Wallet lifecycle state."""
    ACTIVE = "active"
    USED = "used"  # Address has been used, should not reuse
    RETIRED = "retired"  # Manually retired
    COMPROMISED = "compromised"  # Marked as compromised


class Wallet(BaseModel):
    """
    Wallet representation.
    
    Note: Private keys are NEVER included in this model.
    They are stored separately in encrypted keystores.
    """
    id: str = Field(..., description="Unique wallet identifier")
    address: str = Field(..., description="Blockchain address")
    role: WalletRole = Field(..., description="Wallet role")
    state: WalletState = Field(default=WalletState.ACTIVE)
    chain: str = Field(default="ethereum", description="Blockchain network")
    
    # HD wallet derivation info (for deterministic regeneration)
    derivation_path: Optional[str] = Field(
        default=None,
        description="HD derivation path (e.g., m/44'/60'/0'/0/0)"
    )
    derivation_index: Optional[int] = Field(
        default=None,
        description="Derivation index for this wallet"
    )
    
    # Metadata
    label: Optional[str] = Field(default=None, description="User-defined label")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    used_at: Optional[datetime] = Field(default=None)
    transaction_count: int = Field(default=0, ge=0)
    
    # Privacy hygiene
    is_one_time: bool = Field(
        default=True,
        description="If true, address should only be used once"
    )
    reuse_allowed: bool = Field(
        default=False,
        description="Explicit override to allow reuse"
    )

    class Config:
        use_enum_values = True


class WalletBalance(BaseModel):
    """Wallet balance information."""
    wallet_id: str
    address: str
    chain: str
    native_balance: str = Field(..., description="Native token balance (wei/satoshi)")
    native_balance_formatted: str = Field(..., description="Human-readable balance")
    token_balances: dict[str, str] = Field(
        default_factory=dict,
        description="Token address -> balance mapping"
    )
    last_updated: datetime = Field(default_factory=datetime.utcnow)
