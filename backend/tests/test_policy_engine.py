"""Tests for the Policy Engine."""

import pytest
from app.modules.policy_engine import PolicyEngine, create_default_policy
from app.models.policy import Policy, PolicyRule, PolicyRuleType
from app.models.transaction import TransactionPlan, TransactionStep, TransactionStatus
from app.utils.crypto import generate_id


def create_test_plan(
    steps: list[dict] = None,
    source: str = "0x1234567890123456789012345678901234567890",
    destination: str = "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd",
) -> TransactionPlan:
    """Create a test transaction plan."""
    plan_id = generate_id("plan")
    
    if steps is None:
        steps = [
            {
                "from_address": source,
                "to_address": destination,
                "amount": "1000000000000000000",
                "delay_seconds": 600,
            }
        ]
    
    plan_steps = []
    for i, step_data in enumerate(steps):
        step = TransactionStep(
            id=generate_id("step"),
            order=i,
            from_address=step_data.get("from_address", source),
            to_address=step_data.get("to_address", destination),
            chain="ethereum",
            amount=step_data.get("amount", "1000000000000000000"),
            amount_formatted="1.0 ETH",
            delay_seconds=step_data.get("delay_seconds", 600),
            block_number=step_data.get("block_number"),
        )
        plan_steps.append(step)
    
    return TransactionPlan(
        id=plan_id,
        source_address=source,
        destination_address=destination,
        total_amount="1000000000000000000",
        total_amount_formatted="1.0 ETH",
        chain="ethereum",
        steps=plan_steps,
        status=TransactionStatus.PLANNED,
    )


class TestPolicyEngine:
    """Tests for the Policy Engine."""
    
    def test_create_default_policy(self):
        """Test default policy creation."""
        policy = create_default_policy()
        
        assert policy.id == "default"
        assert policy.name == "Default Privacy Policy"
        assert len(policy.rules) > 0
    
    def test_load_and_set_policy(self):
        """Test loading and setting active policy."""
        engine = PolicyEngine()
        policy = create_default_policy()
        
        engine._policies[policy.id] = policy
        engine.set_active_policy(policy.id)
        
        assert engine._active_policy == policy
    
    def test_validate_plan_no_reuse_pass(self):
        """Test that plans without address reuse pass."""
        engine = PolicyEngine()
        policy = create_default_policy()
        engine._policies[policy.id] = policy
        engine.set_active_policy(policy.id)
        
        # Create plan with unique addresses
        steps = [
            {"from_address": "0x1111", "to_address": "0x2222", "delay_seconds": 600},
            {"from_address": "0x2222", "to_address": "0x3333", "delay_seconds": 600},
        ]
        plan = create_test_plan(steps=steps)
        
        result = engine.validate_plan(plan)
        
        # Should not have address reuse violation
        reuse_violations = [
            v for v in result.violations
            if "reuse" in v.rule_name.lower()
        ]
        assert len(reuse_violations) == 0
    
    def test_validate_plan_no_reuse_fail(self):
        """Test that plans with address reuse fail."""
        engine = PolicyEngine()
        policy = create_default_policy()
        engine._policies[policy.id] = policy
        engine.set_active_policy(policy.id)
        
        # Create plan with address reuse
        reused = "0x1111111111111111111111111111111111111111"
        steps = [
            {"from_address": reused, "to_address": "0x2222", "delay_seconds": 600},
            {"from_address": "0x2222", "to_address": reused, "delay_seconds": 600},
        ]
        plan = create_test_plan(steps=steps)
        
        result = engine.validate_plan(plan)
        
        # Should have address reuse violation
        reuse_violations = [
            v for v in result.violations
            if "reuse" in v.rule_name.lower()
        ]
        assert len(reuse_violations) > 0
    
    def test_validate_min_delay_pass(self):
        """Test that plans with sufficient delay pass."""
        engine = PolicyEngine()
        policy = create_default_policy()
        engine._policies[policy.id] = policy
        engine.set_active_policy(policy.id)
        
        # Create plan with good delays
        steps = [
            {"from_address": "0x1111", "to_address": "0x2222", "delay_seconds": 600},
            {"from_address": "0x2222", "to_address": "0x3333", "delay_seconds": 600},
        ]
        plan = create_test_plan(steps=steps)
        
        result = engine.validate_plan(plan)
        
        # Should not have delay violation
        delay_violations = [
            v for v in result.violations
            if "delay" in v.rule_name.lower() and "minimum" in v.rule_name.lower()
        ]
        assert len(delay_violations) == 0
    
    def test_validate_min_delay_fail(self):
        """Test that plans with insufficient delay fail."""
        engine = PolicyEngine()
        policy = create_default_policy()
        engine._policies[policy.id] = policy
        engine.set_active_policy(policy.id)
        
        # Create plan with short delays
        steps = [
            {"from_address": "0x1111", "to_address": "0x2222", "delay_seconds": 60},
            {"from_address": "0x2222", "to_address": "0x3333", "delay_seconds": 60},
        ]
        plan = create_test_plan(steps=steps)
        
        result = engine.validate_plan(plan)
        
        # Should have minimum delay violation (warning)
        delay_violations = [
            v for v in result.violations
            if "minimum" in v.rule_name.lower()
        ]
        assert len(delay_violations) > 0
    
    def test_validate_min_hops_fail(self):
        """Test that plans with insufficient hops get flagged."""
        engine = PolicyEngine()
        policy = create_default_policy()
        engine._policies[policy.id] = policy
        engine.set_active_policy(policy.id)
        
        # Create single-hop plan
        plan = create_test_plan()  # Default is 1 step
        
        result = engine.validate_plan(plan)
        
        # Should have min hops warning
        hop_violations = [
            v for v in result.violations
            if "hop" in v.rule_name.lower()
        ]
        assert len(hop_violations) > 0
    
    def test_strict_mode(self):
        """Test that strict mode converts warnings to errors."""
        engine = PolicyEngine()
        
        # Create strict policy
        policy = Policy(
            id="strict",
            name="Strict Policy",
            rules=[
                PolicyRule(
                    id="min_delay",
                    type=PolicyRuleType.MIN_DELAY,
                    name="Minimum Delay",
                    description="Min delay rule",
                    severity="warning",
                    parameters={"min_seconds": 300},
                )
            ],
            strict_mode=True,  # Enable strict mode
        )
        engine._policies[policy.id] = policy
        
        # Create plan with short delay
        steps = [
            {"from_address": "0x1111", "to_address": "0x2222", "delay_seconds": 60},
        ]
        plan = create_test_plan(steps=steps)
        
        result = engine.validate_plan(plan, policy)
        
        # In strict mode, all violations become errors
        assert result.errors_count > 0
        assert not result.is_valid
    
    def test_validation_result_counts(self):
        """Test that validation result correctly counts violations."""
        engine = PolicyEngine()
        policy = create_default_policy()
        engine._policies[policy.id] = policy
        engine.set_active_policy(policy.id)
        
        # Create problematic plan
        reused = "0x1111111111111111111111111111111111111111"
        steps = [
            {"from_address": reused, "to_address": "0x2222", "delay_seconds": 10},
            {"from_address": "0x2222", "to_address": reused, "delay_seconds": 10},
        ]
        plan = create_test_plan(steps=steps)
        
        result = engine.validate_plan(plan)
        
        assert result.warnings_count + result.errors_count == len(result.violations)
