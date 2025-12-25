"""
Audit logging models for HideX.

Audit logs are:
- Immutable (append-only)
- Designed for forensic review
- Compliant with transparency requirements
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field


class AuditEventType(str, Enum):
    """Types of auditable events."""
    # Wallet events
    WALLET_CREATED = "wallet_created"
    WALLET_USED = "wallet_used"
    WALLET_RETIRED = "wallet_retired"
    
    # Plan events
    PLAN_CREATED = "plan_created"
    PLAN_SIMULATED = "plan_simulated"
    PLAN_CONFIRMED = "plan_confirmed"
    PLAN_CANCELLED = "plan_cancelled"
    
    # Transaction events
    TX_EXECUTED = "tx_executed"
    TX_FAILED = "tx_failed"
    
    # Policy events
    POLICY_LOADED = "policy_loaded"
    POLICY_VALIDATED = "policy_validated"
    POLICY_VIOLATION = "policy_violation"
    
    # Risk events
    RISK_CALCULATED = "risk_calculated"
    RISK_OVERRIDE = "risk_override"
    
    # System events
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    CONFIG_CHANGED = "config_changed"


class AuditEntry(BaseModel):
    """
    Single audit log entry.
    
    Designed for immutability and forensic review.
    """
    id: str = Field(..., description="Unique entry identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: AuditEventType
    
    # Context
    session_id: Optional[str] = Field(default=None)
    plan_id: Optional[str] = Field(default=None)
    wallet_id: Optional[str] = Field(default=None)
    tx_hash: Optional[str] = Field(default=None)
    
    # Event data
    summary: str = Field(..., description="One-line summary")
    details: dict[str, Any] = Field(default_factory=dict)
    
    # Policy compliance
    policy_id: Optional[str] = Field(default=None)
    policy_compliant: Optional[bool] = Field(default=None)
    
    # Risk snapshot
    risk_score: Optional[int] = Field(default=None)
    risk_band: Optional[str] = Field(default=None)
    
    # State changes
    before_state: Optional[dict] = Field(default=None)
    after_state: Optional[dict] = Field(default=None)
    
    # Integrity
    previous_entry_hash: Optional[str] = Field(
        default=None,
        description="Hash of previous entry for chain integrity"
    )
    entry_hash: Optional[str] = Field(
        default=None,
        description="Hash of this entry"
    )


class AuditLog(BaseModel):
    """
    Collection of audit entries for a session or plan.
    """
    id: str = Field(..., description="Log identifier")
    name: Optional[str] = Field(default=None)
    
    # Entries
    entries: list[AuditEntry] = Field(default_factory=list)
    
    # Metadata
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = Field(default=None)
    
    # Summary
    total_entries: int = Field(default=0)
    plan_ids: list[str] = Field(default_factory=list)
    tx_hashes: list[str] = Field(default_factory=list)
    
    def add_entry(self, entry: AuditEntry) -> None:
        """Add an entry to the log."""
        self.entries.append(entry)
        self.total_entries = len(self.entries)
        if entry.plan_id and entry.plan_id not in self.plan_ids:
            self.plan_ids.append(entry.plan_id)
        if entry.tx_hash and entry.tx_hash not in self.tx_hashes:
            self.tx_hashes.append(entry.tx_hash)
