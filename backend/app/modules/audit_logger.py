"""
Post-Transaction Audit Logger for HideX.

The Audit Logger is responsible for:
- Maintaining immutable local logs
- Storing timestamps, tx hashes, and compliance reports
- Recording wallet state changes
- Supporting forensic review and learning

Design principles:
- Append-only (immutable)
- Designed for forensic review
- Chain integrity verification
- Local storage only
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Any

from ..models.audit import AuditLog, AuditEntry, AuditEventType
from ..models.transaction import TransactionPlan, TransactionStep
from ..models.wallet import Wallet, WalletState
from ..models.policy import PolicyValidationResult
from ..models.risk import RiskScore
from ..utils.crypto import generate_id, hash_data
from ..config import get_settings


class AuditLogger:
    """
    Post-Transaction Audit Logger.
    
    Maintains immutable, append-only audit logs for:
    - Transaction planning and execution
    - Policy compliance
    - Risk assessments
    - Wallet state changes
    
    Logs are designed for forensic review and learning.
    """
    
    def __init__(self, logs_dir: Optional[Path] = None):
        """
        Initialize the Audit Logger.
        
        Args:
            logs_dir: Directory for storing audit logs
        """
        settings = get_settings()
        self._logs_dir = logs_dir or settings.logs_dir
        self._logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Current session log
        self._session_id = generate_id("session")
        self._current_log = AuditLog(
            id=self._session_id,
            name=f"Session {self._session_id[:8]}",
        )
        
        # Last entry hash for chain integrity
        self._last_hash: Optional[str] = None
    
    @property
    def session_id(self) -> str:
        """Get current session ID."""
        return self._session_id
    
    def log_event(
        self,
        event_type: AuditEventType,
        summary: str,
        details: Optional[dict] = None,
        plan_id: Optional[str] = None,
        wallet_id: Optional[str] = None,
        tx_hash: Optional[str] = None,
        policy_id: Optional[str] = None,
        policy_compliant: Optional[bool] = None,
        risk_score: Optional[int] = None,
        risk_band: Optional[str] = None,
        before_state: Optional[dict] = None,
        after_state: Optional[dict] = None,
    ) -> AuditEntry:
        """
        Log an audit event.
        
        All events are added to the append-only log with
        chain integrity verification.
        """
        entry_id = generate_id("audit")
        
        entry = AuditEntry(
            id=entry_id,
            timestamp=datetime.utcnow(),
            event_type=event_type,
            session_id=self._session_id,
            plan_id=plan_id,
            wallet_id=wallet_id,
            tx_hash=tx_hash,
            summary=summary,
            details=details or {},
            policy_id=policy_id,
            policy_compliant=policy_compliant,
            risk_score=risk_score,
            risk_band=risk_band,
            before_state=before_state,
            after_state=after_state,
            previous_entry_hash=self._last_hash,
        )
        
        # Calculate entry hash for chain integrity
        entry.entry_hash = self._calculate_entry_hash(entry)
        self._last_hash = entry.entry_hash
        
        # Add to current log
        self._current_log.add_entry(entry)
        
        # Persist immediately for durability
        self._persist_entry(entry)
        
        return entry
    
    def _calculate_entry_hash(self, entry: AuditEntry) -> str:
        """Calculate hash of an entry for integrity verification."""
        # Serialize key fields for hashing
        hash_input = json.dumps({
            "id": entry.id,
            "timestamp": entry.timestamp.isoformat(),
            "event_type": entry.event_type.value,
            "summary": entry.summary,
            "previous_hash": entry.previous_entry_hash,
        }, sort_keys=True)
        
        return hash_data(hash_input)
    
    def _persist_entry(self, entry: AuditEntry) -> None:
        """Persist an entry to disk immediately."""
        log_file = self._logs_dir / f"session_{self._session_id}.jsonl"
        
        # Append as JSON line
        with open(log_file, 'a') as f:
            f.write(entry.model_dump_json() + "\n")
    
    def log_system_start(self) -> AuditEntry:
        """Log system startup."""
        return self.log_event(
            event_type=AuditEventType.SYSTEM_START,
            summary=f"HideX session started: {self._session_id}",
            details={"session_id": self._session_id},
        )
    
    def log_system_stop(self) -> AuditEntry:
        """Log system shutdown."""
        self._current_log.ended_at = datetime.utcnow()
        return self.log_event(
            event_type=AuditEventType.SYSTEM_STOP,
            summary=f"HideX session ended: {self._session_id}",
            details={
                "session_id": self._session_id,
                "total_entries": self._current_log.total_entries,
            },
        )
    
    def log_wallet_created(self, wallet: Wallet) -> AuditEntry:
        """Log wallet creation."""
        return self.log_event(
            event_type=AuditEventType.WALLET_CREATED,
            summary=f"Wallet created: {wallet.address[:10]}... ({wallet.role.value})",
            wallet_id=wallet.id,
            details={
                "address": wallet.address,
                "role": wallet.role.value,
                "chain": wallet.chain,
                "is_one_time": wallet.is_one_time,
            },
            after_state={"state": wallet.state.value},
        )
    
    def log_wallet_used(
        self,
        wallet: Wallet,
        tx_hash: str,
        plan_id: Optional[str] = None
    ) -> AuditEntry:
        """Log wallet usage."""
        return self.log_event(
            event_type=AuditEventType.WALLET_USED,
            summary=f"Wallet used: {wallet.address[:10]}...",
            wallet_id=wallet.id,
            tx_hash=tx_hash,
            plan_id=plan_id,
            details={
                "address": wallet.address,
                "transaction_count": wallet.transaction_count,
            },
            before_state={"state": WalletState.ACTIVE.value},
            after_state={"state": wallet.state.value},
        )
    
    def log_wallet_retired(self, wallet: Wallet) -> AuditEntry:
        """Log wallet retirement."""
        return self.log_event(
            event_type=AuditEventType.WALLET_RETIRED,
            summary=f"Wallet retired: {wallet.address[:10]}...",
            wallet_id=wallet.id,
            details={"address": wallet.address},
            after_state={"state": WalletState.RETIRED.value},
        )
    
    def log_plan_created(self, plan: TransactionPlan) -> AuditEntry:
        """Log plan creation."""
        return self.log_event(
            event_type=AuditEventType.PLAN_CREATED,
            summary=f"Plan created: {plan.name or plan.id}",
            plan_id=plan.id,
            details={
                "source": plan.source_address,
                "destination": plan.destination_address,
                "amount": plan.total_amount_formatted,
                "steps": len(plan.steps),
            },
        )
    
    def log_plan_simulated(
        self,
        plan: TransactionPlan,
        risk_score: RiskScore
    ) -> AuditEntry:
        """Log plan simulation."""
        return self.log_event(
            event_type=AuditEventType.PLAN_SIMULATED,
            summary=f"Plan simulated: {plan.name or plan.id} (Risk: {risk_score.score}/100)",
            plan_id=plan.id,
            risk_score=risk_score.score,
            risk_band=risk_score.band.value,
            details={
                "risk_factors": [f.name for f in risk_score.factors],
                "warnings": risk_score.warnings,
                "blockers": risk_score.blockers,
            },
        )
    
    def log_plan_confirmed(self, plan: TransactionPlan) -> AuditEntry:
        """Log plan confirmation by user."""
        return self.log_event(
            event_type=AuditEventType.PLAN_CONFIRMED,
            summary=f"Plan confirmed for execution: {plan.name or plan.id}",
            plan_id=plan.id,
            details={"confirmed_at": datetime.utcnow().isoformat()},
        )
    
    def log_plan_cancelled(self, plan: TransactionPlan, reason: str) -> AuditEntry:
        """Log plan cancellation."""
        return self.log_event(
            event_type=AuditEventType.PLAN_CANCELLED,
            summary=f"Plan cancelled: {plan.name or plan.id}",
            plan_id=plan.id,
            details={"reason": reason},
        )
    
    def log_transaction_executed(
        self,
        plan: TransactionPlan,
        step: TransactionStep,
        tx_hash: str,
        block_number: int,
        gas_used: int,
    ) -> AuditEntry:
        """Log transaction execution."""
        return self.log_event(
            event_type=AuditEventType.TX_EXECUTED,
            summary=f"Transaction executed: {tx_hash[:10]}...",
            plan_id=plan.id,
            tx_hash=tx_hash,
            details={
                "step_order": step.order,
                "from": step.from_address,
                "to": step.to_address,
                "amount": step.amount_formatted,
                "block_number": block_number,
                "gas_used": gas_used,
            },
        )
    
    def log_transaction_failed(
        self,
        plan: TransactionPlan,
        step: TransactionStep,
        error: str,
    ) -> AuditEntry:
        """Log transaction failure."""
        return self.log_event(
            event_type=AuditEventType.TX_FAILED,
            summary=f"Transaction failed at step {step.order}",
            plan_id=plan.id,
            details={
                "step_order": step.order,
                "from": step.from_address,
                "to": step.to_address,
                "error": error,
            },
        )
    
    def log_policy_loaded(self, policy_id: str, policy_name: str) -> AuditEntry:
        """Log policy loading."""
        return self.log_event(
            event_type=AuditEventType.POLICY_LOADED,
            summary=f"Policy loaded: {policy_name}",
            policy_id=policy_id,
            details={"policy_name": policy_name},
        )
    
    def log_policy_validated(
        self,
        result: PolicyValidationResult
    ) -> AuditEntry:
        """Log policy validation result."""
        return self.log_event(
            event_type=AuditEventType.POLICY_VALIDATED,
            summary=f"Policy validation: {'PASSED' if result.is_valid else 'FAILED'}",
            policy_id=result.policy_id,
            plan_id=result.plan_id,
            policy_compliant=result.is_compliant,
            details={
                "is_valid": result.is_valid,
                "is_compliant": result.is_compliant,
                "warnings_count": result.warnings_count,
                "errors_count": result.errors_count,
                "violations": [v.message for v in result.violations],
            },
        )
    
    def log_policy_violation(
        self,
        plan_id: str,
        policy_id: str,
        rule_name: str,
        message: str,
        severity: str,
    ) -> AuditEntry:
        """Log individual policy violation."""
        return self.log_event(
            event_type=AuditEventType.POLICY_VIOLATION,
            summary=f"Policy violation ({severity}): {rule_name}",
            policy_id=policy_id,
            plan_id=plan_id,
            policy_compliant=False,
            details={
                "rule_name": rule_name,
                "message": message,
                "severity": severity,
            },
        )
    
    def log_risk_calculated(
        self,
        plan_id: str,
        risk_score: RiskScore
    ) -> AuditEntry:
        """Log risk calculation."""
        return self.log_event(
            event_type=AuditEventType.RISK_CALCULATED,
            summary=f"Risk calculated: {risk_score.score}/100 ({risk_score.band.value})",
            plan_id=plan_id,
            risk_score=risk_score.score,
            risk_band=risk_score.band.value,
            details={
                "factors": {f.name: f.score for f in risk_score.factors},
                "recommendations": risk_score.recommendations,
            },
        )
    
    def log_risk_override(
        self,
        plan_id: str,
        original_score: int,
        reason: str,
    ) -> AuditEntry:
        """Log user override of risk warning."""
        return self.log_event(
            event_type=AuditEventType.RISK_OVERRIDE,
            summary=f"Risk override: User accepted score {original_score}/100",
            plan_id=plan_id,
            risk_score=original_score,
            details={"reason": reason},
        )
    
    def get_current_log(self) -> AuditLog:
        """Get the current session's audit log."""
        return self._current_log
    
    def load_session_log(self, session_id: str) -> Optional[AuditLog]:
        """Load a previous session's audit log."""
        log_file = self._logs_dir / f"session_{session_id}.jsonl"
        
        if not log_file.exists():
            return None
        
        entries = []
        with open(log_file, 'r') as f:
            for line in f:
                if line.strip():
                    entry_data = json.loads(line)
                    entries.append(AuditEntry(**entry_data))
        
        log = AuditLog(
            id=session_id,
            name=f"Session {session_id[:8]}",
            entries=entries,
            total_entries=len(entries),
        )
        
        if entries:
            log.started_at = entries[0].timestamp
            log.ended_at = entries[-1].timestamp
        
        return log
    
    def list_sessions(self) -> list[str]:
        """List all available session IDs."""
        sessions = []
        for log_file in self._logs_dir.glob("session_*.jsonl"):
            session_id = log_file.stem.replace("session_", "")
            sessions.append(session_id)
        return sorted(sessions, reverse=True)
    
    def verify_log_integrity(self, log: AuditLog) -> tuple[bool, list[str]]:
        """
        Verify the integrity of an audit log.
        
        Checks that the hash chain is unbroken.
        
        Returns:
            (is_valid, list of issues)
        """
        issues = []
        
        for i, entry in enumerate(log.entries):
            # Verify hash chain
            if i == 0:
                if entry.previous_entry_hash is not None:
                    issues.append(f"Entry {i}: First entry has previous hash")
            else:
                expected_prev = log.entries[i - 1].entry_hash
                if entry.previous_entry_hash != expected_prev:
                    issues.append(
                        f"Entry {i}: Previous hash mismatch "
                        f"(expected {expected_prev[:10]}..., got {entry.previous_entry_hash[:10] if entry.previous_entry_hash else 'None'}...)"
                    )
            
            # Verify entry hash
            calculated = self._calculate_entry_hash(entry)
            if entry.entry_hash != calculated:
                issues.append(
                    f"Entry {i}: Entry hash mismatch "
                    f"(expected {calculated[:10]}..., got {entry.entry_hash[:10] if entry.entry_hash else 'None'}...)"
                )
        
        return len(issues) == 0, issues
    
    def generate_compliance_report(
        self,
        plan_id: str,
        session_id: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Generate a compliance report for a transaction plan.
        
        Designed for forensic review and regulatory compliance.
        """
        if session_id:
            log = self.load_session_log(session_id)
        else:
            log = self._current_log
        
        if not log:
            return {"error": "Log not found"}
        
        # Filter entries for this plan
        plan_entries = [e for e in log.entries if e.plan_id == plan_id]
        
        if not plan_entries:
            return {"error": f"No entries found for plan {plan_id}"}
        
        # Build report
        report = {
            "plan_id": plan_id,
            "session_id": log.id,
            "generated_at": datetime.utcnow().isoformat(),
            "timeline": [],
            "policy_compliance": {
                "validated": False,
                "violations": [],
            },
            "risk_assessment": {
                "score": None,
                "band": None,
            },
            "transactions": [],
            "summary": {},
        }
        
        for entry in plan_entries:
            timeline_entry = {
                "timestamp": entry.timestamp.isoformat(),
                "event": entry.event_type.value,
                "summary": entry.summary,
            }
            report["timeline"].append(timeline_entry)
            
            if entry.event_type == AuditEventType.POLICY_VALIDATED:
                report["policy_compliance"]["validated"] = True
                report["policy_compliance"]["is_compliant"] = entry.policy_compliant
                if entry.details.get("violations"):
                    report["policy_compliance"]["violations"] = entry.details["violations"]
            
            if entry.event_type == AuditEventType.RISK_CALCULATED:
                report["risk_assessment"]["score"] = entry.risk_score
                report["risk_assessment"]["band"] = entry.risk_band
            
            if entry.event_type == AuditEventType.TX_EXECUTED:
                report["transactions"].append({
                    "tx_hash": entry.tx_hash,
                    "timestamp": entry.timestamp.isoformat(),
                    "details": entry.details,
                })
        
        # Summary
        report["summary"] = {
            "total_events": len(plan_entries),
            "transactions_executed": len(report["transactions"]),
            "policy_validated": report["policy_compliance"]["validated"],
            "risk_score": report["risk_assessment"]["score"],
        }
        
        return report
