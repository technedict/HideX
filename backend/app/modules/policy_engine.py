"""
Privacy Policy Engine for HideX.

The Policy Engine is responsible for:
- Loading policies from human-readable JSON files
- Validating policies against schema
- Evaluating transaction plans against policies
- Providing clear violation messages

Design principles:
- Rule-based and deterministic
- No hard-coded logic
- All rules must be explainable
"""

import json
from pathlib import Path
from typing import Optional
from datetime import datetime

from pydantic import ValidationError

from ..models.policy import (
    Policy,
    PolicyRule,
    PolicyRuleType,
    PolicyValidationResult,
    PolicyViolation,
)
from ..models.transaction import TransactionPlan, TransactionStep
from ..models.wallet import WalletRole
from ..config import get_settings


class PolicyEngine:
    """
    Privacy Policy Engine.
    
    Loads and evaluates policies for transaction plans.
    All rules are loaded from JSON files, not hard-coded.
    """
    
    def __init__(self, policies_dir: Optional[Path] = None):
        """
        Initialize the Policy Engine.
        
        Args:
            policies_dir: Directory containing policy JSON files
        """
        settings = get_settings()
        self._policies_dir = policies_dir or settings.policies_dir
        self._policies: dict[str, Policy] = {}
        self._active_policy: Optional[Policy] = None
    
    def load_policy(self, policy_path: Path) -> Policy:
        """
        Load a policy from a JSON file.
        
        Args:
            policy_path: Path to the policy JSON file
            
        Returns:
            Loaded and validated Policy object
            
        Raises:
            FileNotFoundError: If policy file doesn't exist
            ValidationError: If policy is invalid
        """
        if not policy_path.exists():
            raise FileNotFoundError(f"Policy file not found: {policy_path}")
        
        with open(policy_path, 'r') as f:
            data = json.load(f)
        
        policy = Policy(**data)
        self._policies[policy.id] = policy
        return policy
    
    def load_policies_from_directory(self) -> list[Policy]:
        """
        Load all policies from the policies directory.
        
        Returns:
            List of loaded policies
        """
        policies = []
        if self._policies_dir.exists():
            for policy_file in self._policies_dir.glob("*.json"):
                try:
                    policy = self.load_policy(policy_file)
                    policies.append(policy)
                except (ValidationError, json.JSONDecodeError) as e:
                    # Log error but continue loading other policies
                    print(f"Warning: Failed to load policy {policy_file}: {e}")
        return policies
    
    def set_active_policy(self, policy_id: str) -> None:
        """Set the active policy for validation."""
        if policy_id not in self._policies:
            raise ValueError(f"Policy not found: {policy_id}")
        self._active_policy = self._policies[policy_id]
    
    def get_policy(self, policy_id: str) -> Optional[Policy]:
        """Get a policy by ID."""
        return self._policies.get(policy_id)
    
    def list_policies(self) -> list[Policy]:
        """List all loaded policies."""
        return list(self._policies.values())
    
    def validate_plan(
        self,
        plan: TransactionPlan,
        policy: Optional[Policy] = None
    ) -> PolicyValidationResult:
        """
        Validate a transaction plan against a policy.
        
        Args:
            plan: The transaction plan to validate
            policy: Policy to use (or active policy if None)
            
        Returns:
            PolicyValidationResult with violations and warnings
        """
        policy = policy or self._active_policy
        if not policy:
            raise ValueError("No policy specified and no active policy set")
        
        violations = []
        
        for rule in policy.rules:
            if not rule.enabled:
                continue
            
            violation = self._evaluate_rule(rule, plan)
            if violation:
                violations.append(violation)
        
        # Count by severity
        warnings_count = sum(1 for v in violations if v.severity == "warning")
        errors_count = sum(1 for v in violations if v.severity == "error")
        
        # In strict mode, warnings become errors
        if policy.strict_mode:
            errors_count += warnings_count
            for v in violations:
                v.severity = "error"
        
        return PolicyValidationResult(
            policy_id=policy.id,
            policy_name=policy.name,
            plan_id=plan.id,
            is_valid=errors_count == 0,
            is_compliant=len(violations) == 0,
            violations=violations,
            warnings_count=warnings_count,
            errors_count=errors_count,
        )
    
    def _evaluate_rule(
        self,
        rule: PolicyRule,
        plan: TransactionPlan
    ) -> Optional[PolicyViolation]:
        """
        Evaluate a single rule against a plan.
        
        Returns PolicyViolation if rule is violated, None otherwise.
        """
        # Dispatch to rule-specific handler
        handlers = {
            PolicyRuleType.NO_ADDRESS_REUSE: self._check_no_address_reuse,
            PolicyRuleType.MIN_DELAY: self._check_min_delay,
            PolicyRuleType.MAX_DELAY: self._check_max_delay,
            PolicyRuleType.NO_SAME_BLOCK: self._check_no_same_block,
            PolicyRuleType.ROLE_SEPARATION: self._check_role_separation,
            PolicyRuleType.MAX_AMOUNT_SIMILARITY: self._check_max_amount_similarity,
            PolicyRuleType.MIN_HOPS: self._check_min_hops,
            PolicyRuleType.MAX_HOPS: self._check_max_hops,
        }
        
        handler = handlers.get(rule.type)
        if handler:
            return handler(rule, plan)
        
        return None
    
    def _check_no_address_reuse(
        self,
        rule: PolicyRule,
        plan: TransactionPlan
    ) -> Optional[PolicyViolation]:
        """Check that no address is reused in the plan."""
        addresses = []
        for step in plan.steps:
            addresses.append(step.from_address)
            addresses.append(step.to_address)
        
        seen = set()
        duplicates = set()
        for addr in addresses:
            if addr in seen:
                duplicates.add(addr)
            seen.add(addr)
        
        if duplicates:
            return PolicyViolation(
                rule_id=rule.id,
                rule_name=rule.name,
                severity=rule.severity,
                message=f"Address reuse detected: {len(duplicates)} addresses used multiple times",
                details={"duplicate_addresses": list(duplicates)},
                remediation="Use unique addresses for each step in the transaction plan",
            )
        return None
    
    def _check_min_delay(
        self,
        rule: PolicyRule,
        plan: TransactionPlan
    ) -> Optional[PolicyViolation]:
        """Check minimum delay between steps."""
        min_delay = rule.parameters.get("min_seconds", 0)
        
        for i, step in enumerate(plan.steps):
            if step.delay_seconds < min_delay:
                return PolicyViolation(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    severity=rule.severity,
                    message=f"Step {i} delay ({step.delay_seconds}s) is below minimum ({min_delay}s)",
                    details={"step_id": step.id, "actual": step.delay_seconds, "minimum": min_delay},
                    remediation=f"Increase delay to at least {min_delay} seconds",
                )
        return None
    
    def _check_max_delay(
        self,
        rule: PolicyRule,
        plan: TransactionPlan
    ) -> Optional[PolicyViolation]:
        """Check maximum delay between steps."""
        max_delay = rule.parameters.get("max_seconds", float('inf'))
        
        for i, step in enumerate(plan.steps):
            if step.delay_seconds > max_delay:
                return PolicyViolation(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    severity=rule.severity,
                    message=f"Step {i} delay ({step.delay_seconds}s) exceeds maximum ({max_delay}s)",
                    details={"step_id": step.id, "actual": step.delay_seconds, "maximum": max_delay},
                    remediation=f"Reduce delay to at most {max_delay} seconds",
                )
        return None
    
    def _check_no_same_block(
        self,
        rule: PolicyRule,
        plan: TransactionPlan
    ) -> Optional[PolicyViolation]:
        """Check that no two steps are in the same block (for executed plans)."""
        blocks = {}
        for step in plan.steps:
            if step.block_number:
                if step.block_number in blocks:
                    return PolicyViolation(
                        rule_id=rule.id,
                        rule_name=rule.name,
                        severity=rule.severity,
                        message=f"Multiple transactions in same block {step.block_number}",
                        details={"block_number": step.block_number},
                        remediation="Ensure transactions are spread across different blocks",
                    )
                blocks[step.block_number] = step.id
        return None
    
    def _check_role_separation(
        self,
        rule: PolicyRule,
        plan: TransactionPlan
    ) -> Optional[PolicyViolation]:
        """
        Check that wallet roles are properly separated.
        
        This is a simplified check - full implementation would need
        access to wallet metadata.
        """
        # This rule requires additional context about wallet roles
        # For MVP, we just verify the plan has multiple hops
        if len(plan.steps) < 2:
            return PolicyViolation(
                rule_id=rule.id,
                rule_name=rule.name,
                severity=rule.severity,
                message="Plan has insufficient hops for role separation",
                details={"step_count": len(plan.steps)},
                remediation="Use at least 2 hops with different wallet roles",
            )
        return None
    
    def _check_max_amount_similarity(
        self,
        rule: PolicyRule,
        plan: TransactionPlan
    ) -> Optional[PolicyViolation]:
        """Check that amounts are sufficiently varied."""
        max_similarity = rule.parameters.get("max_percent", 0.99)
        
        amounts = [int(step.amount) for step in plan.steps]
        total = int(plan.total_amount)
        
        # Check if any single step is too close to the total
        for i, amount in enumerate(amounts):
            if total > 0:
                similarity = amount / total
                if similarity > max_similarity:
                    return PolicyViolation(
                        rule_id=rule.id,
                        rule_name=rule.name,
                        severity=rule.severity,
                        message=f"Step {i} amount is {similarity*100:.1f}% of total (max {max_similarity*100}%)",
                        details={"step_id": plan.steps[i].id, "similarity": similarity},
                        remediation="Split amounts more evenly across steps",
                    )
        return None
    
    def _check_min_hops(
        self,
        rule: PolicyRule,
        plan: TransactionPlan
    ) -> Optional[PolicyViolation]:
        """Check minimum number of hops."""
        min_hops = rule.parameters.get("min_hops", 1)
        
        if len(plan.steps) < min_hops:
            return PolicyViolation(
                rule_id=rule.id,
                rule_name=rule.name,
                severity=rule.severity,
                message=f"Plan has {len(plan.steps)} hops, minimum is {min_hops}",
                details={"actual": len(plan.steps), "minimum": min_hops},
                remediation=f"Add more intermediate steps to reach at least {min_hops} hops",
            )
        return None
    
    def _check_max_hops(
        self,
        rule: PolicyRule,
        plan: TransactionPlan
    ) -> Optional[PolicyViolation]:
        """Check maximum number of hops."""
        max_hops = rule.parameters.get("max_hops", 10)
        
        if len(plan.steps) > max_hops:
            return PolicyViolation(
                rule_id=rule.id,
                rule_name=rule.name,
                severity=rule.severity,
                message=f"Plan has {len(plan.steps)} hops, maximum is {max_hops}",
                details={"actual": len(plan.steps), "maximum": max_hops},
                remediation=f"Reduce intermediate steps to at most {max_hops} hops",
            )
        return None


def create_default_policy() -> Policy:
    """
    Create a default privacy policy.
    
    This provides sensible defaults for common use cases.
    Users should customize for their specific needs.
    """
    return Policy(
        id="default",
        name="Default Privacy Policy",
        version="1.0.0",
        description="Standard privacy hygiene policy for transaction planning",
        rules=[
            PolicyRule(
                id="no_reuse",
                type=PolicyRuleType.NO_ADDRESS_REUSE,
                name="No Address Reuse",
                description="Prevent reusing addresses within a transaction plan",
                severity="error",
                rationale="Address reuse creates clear links between transactions",
            ),
            PolicyRule(
                id="min_delay",
                type=PolicyRuleType.MIN_DELAY,
                name="Minimum Delay",
                description="Ensure minimum time between transaction steps",
                severity="warning",
                parameters={"min_seconds": 300},  # 5 minutes
                rationale="Timing correlation can link related transactions",
            ),
            PolicyRule(
                id="max_delay",
                type=PolicyRuleType.MAX_DELAY,
                name="Maximum Delay",
                description="Limit maximum delay to reasonable bounds",
                severity="warning",
                parameters={"max_seconds": 86400},  # 24 hours
                rationale="Very long delays may be impractical",
            ),
            PolicyRule(
                id="no_same_block",
                type=PolicyRuleType.NO_SAME_BLOCK,
                name="No Same Block",
                description="Prevent multiple transactions in the same block",
                severity="error",
                rationale="Same-block transactions are trivially linkable",
            ),
            PolicyRule(
                id="min_hops",
                type=PolicyRuleType.MIN_HOPS,
                name="Minimum Hops",
                description="Require minimum number of intermediate steps",
                severity="warning",
                parameters={"min_hops": 2},
                rationale="Multiple hops provide better separation",
            ),
        ],
        strict_mode=False,
        allow_override=True,
    )
