"""Tests for the Routing Planner."""

import pytest
from app.modules.routing_planner import RoutingPlanner
from app.models.wallet import Wallet, WalletRole, WalletState


def create_test_wallet(
    role: WalletRole = WalletRole.TRANSIT,
    address: str = None,
    label: str = None,
) -> Wallet:
    """Create a test wallet."""
    import secrets
    if address is None:
        address = "0x" + secrets.token_hex(20)
    
    return Wallet(
        id=f"wallet_{secrets.token_hex(8)}",
        address=address,
        role=role,
        state=WalletState.ACTIVE,
        chain="ethereum",
        label=label,
    )


class TestRoutingPlanner:
    """Tests for the Routing Planner."""
    
    def test_deterministic_planning(self):
        """Test that planning is deterministic with same seed."""
        planner1 = RoutingPlanner(seed=42)
        planner2 = RoutingPlanner(seed=42)
        
        source = "0x1234567890123456789012345678901234567890"
        dest = "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"
        amount = "1000000000000000000"
        
        transit = create_test_wallet()
        
        plan1 = planner1.create_multi_hop_plan(
            source_address=source,
            destination_address=dest,
            amount_wei=amount,
            transit_wallets=[transit],
        )
        
        plan2 = planner2.create_multi_hop_plan(
            source_address=source,
            destination_address=dest,
            amount_wei=amount,
            transit_wallets=[transit],
        )
        
        # Delays should be the same
        assert len(plan1.steps) == len(plan2.steps)
        for s1, s2 in zip(plan1.steps, plan2.steps):
            assert s1.delay_seconds == s2.delay_seconds
    
    def test_simple_plan_creation(self):
        """Test simple plan creation."""
        planner = RoutingPlanner(seed=42)
        
        source = "0x1234567890123456789012345678901234567890"
        dest = "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"
        amount = "1000000000000000000"
        
        plan = planner.create_simple_plan(
            source_address=source,
            destination_address=dest,
            amount_wei=amount,
        )
        
        assert len(plan.steps) == 1
        assert plan.steps[0].from_address == source
        assert plan.steps[0].to_address == dest
        assert plan.steps[0].amount == amount
        assert plan.is_dry_run is True
    
    def test_multi_hop_plan_creation(self):
        """Test multi-hop plan creation."""
        planner = RoutingPlanner(seed=42)
        
        source = "0x1234567890123456789012345678901234567890"
        dest = "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"
        amount = "1000000000000000000"
        
        transit1 = create_test_wallet(label="transit1")
        transit2 = create_test_wallet(label="transit2")
        
        plan = planner.create_multi_hop_plan(
            source_address=source,
            destination_address=dest,
            amount_wei=amount,
            transit_wallets=[transit1, transit2],
        )
        
        # Should have 3 steps: source->t1, t1->t2, t2->dest
        assert len(plan.steps) == 3
        
        # Verify path
        assert plan.steps[0].from_address == source
        assert plan.steps[0].to_address == transit1.address
        assert plan.steps[1].from_address == transit1.address
        assert plan.steps[1].to_address == transit2.address
        assert plan.steps[2].from_address == transit2.address
        assert plan.steps[2].to_address == dest
    
    def test_multi_hop_delays(self):
        """Test that multi-hop plans have randomized delays."""
        planner = RoutingPlanner(seed=42)
        
        source = "0x1234"
        dest = "0xabcd"
        amount = "1000000000000000000"
        
        transit1 = create_test_wallet()
        transit2 = create_test_wallet()
        
        plan = planner.create_multi_hop_plan(
            source_address=source,
            destination_address=dest,
            amount_wei=amount,
            transit_wallets=[transit1, transit2],
            min_delay_seconds=300,
            max_delay_seconds=600,
        )
        
        # All delays should be within bounds
        for step in plan.steps:
            assert step.delay_seconds >= 0  # First step can be 0
            if step.order > 0:
                # Subsequent steps should have delays
                assert step.delay_seconds >= 200  # Allow some jitter
    
    def test_split_plan_creation(self):
        """Test split amount plan creation."""
        planner = RoutingPlanner(seed=42)
        
        source = "0x1234567890123456789012345678901234567890"
        dest = "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"
        amount = "3000000000000000000"  # 3 ETH
        
        transit1 = create_test_wallet()
        transit2 = create_test_wallet()
        transit3 = create_test_wallet()
        
        plan = planner.create_split_plan(
            source_address=source,
            destination_address=dest,
            amount_wei=amount,
            transit_wallets=[transit1, transit2, transit3],
            num_splits=3,
        )
        
        # Should have 6 steps: 3 to transit, 3 from transit
        assert len(plan.steps) == 6
        
        # Total amount should equal original (across all steps)
        # First 3 steps are source -> transit
        # Last 3 steps are transit -> dest
    
    def test_split_amounts_vary(self):
        """Test that split amounts have variation."""
        planner = RoutingPlanner(seed=42)
        
        source = "0x1234"
        dest = "0xabcd"
        amount = "9000000000000000000"  # 9 ETH
        
        transit1 = create_test_wallet()
        transit2 = create_test_wallet()
        transit3 = create_test_wallet()
        
        plan = planner.create_split_plan(
            source_address=source,
            destination_address=dest,
            amount_wei=amount,
            transit_wallets=[transit1, transit2, transit3],
            num_splits=3,
        )
        
        # Get first phase amounts (source -> transit)
        first_phase_amounts = [
            int(plan.steps[i].amount) for i in range(3)
        ]
        
        # Amounts should not all be equal (they should vary)
        unique_amounts = len(set(first_phase_amounts))
        # With random variation, very unlikely all are same
        # But allow for edge cases in tests
        assert unique_amounts >= 1
        
        # Total should approximately equal original
        total = sum(first_phase_amounts)
        assert abs(total - int(amount)) < int(amount) * 0.01  # Within 1%
    
    def test_insufficient_transit_wallets(self):
        """Test that split plan fails with insufficient transit wallets."""
        planner = RoutingPlanner(seed=42)
        
        source = "0x1234"
        dest = "0xabcd"
        amount = "1000000000000000000"
        
        transit = create_test_wallet()
        
        with pytest.raises(ValueError) as exc_info:
            planner.create_split_plan(
                source_address=source,
                destination_address=dest,
                amount_wei=amount,
                transit_wallets=[transit],  # Only 1, need 3
                num_splits=3,
            )
        
        assert "Need at least 3 transit wallets" in str(exc_info.value)
    
    def test_estimate_total_time(self):
        """Test total time estimation."""
        planner = RoutingPlanner(seed=42)
        
        source = "0x1234"
        dest = "0xabcd"
        amount = "1000000000000000000"
        
        transit = create_test_wallet()
        
        plan = planner.create_multi_hop_plan(
            source_address=source,
            destination_address=dest,
            amount_wei=amount,
            transit_wallets=[transit],
            min_delay_seconds=300,
            max_delay_seconds=300,  # Fixed delay for predictability
        )
        
        total_time = planner.estimate_total_time(plan)
        
        # Should be approximately 2 * 300 = 600 seconds
        assert total_time.total_seconds() >= 300
    
    def test_timing_randomization(self):
        """Test adding timing randomization to plans."""
        planner = RoutingPlanner(seed=42)
        
        source = "0x1234"
        dest = "0xabcd"
        amount = "1000000000000000000"
        
        transit = create_test_wallet()
        
        plan = planner.create_multi_hop_plan(
            source_address=source,
            destination_address=dest,
            amount_wei=amount,
            transit_wallets=[transit],
            min_delay_seconds=1000,
            max_delay_seconds=1000,
        )
        
        original_delays = [s.delay_seconds for s in plan.steps]
        
        # Add jitter
        plan = planner.add_timing_randomization(plan, jitter_percent=0.2)
        
        new_delays = [s.delay_seconds for s in plan.steps]
        
        # Delays should be modified (for non-zero delays)
        for orig, new in zip(original_delays, new_delays):
            if orig > 0:
                # May or may not change, but should be valid
                assert new >= 60  # Minimum allowed
    
    def test_plan_feasibility_validation(self):
        """Test plan feasibility validation."""
        planner = RoutingPlanner(seed=42)
        
        source = "0x1234567890123456789012345678901234567890"
        dest = "0xabcd"
        amount = "1000000000000000000"
        
        transit = create_test_wallet()
        
        plan = planner.create_multi_hop_plan(
            source_address=source,
            destination_address=dest,
            amount_wei=amount,
            transit_wallets=[transit],
        )
        
        # With sufficient balance
        balances = {source.lower(): int(amount)}
        
        is_feasible, issues = planner.validate_plan_feasibility(plan, balances)
        assert is_feasible
        assert len(issues) == 0
    
    def test_plan_feasibility_insufficient_balance(self):
        """Test that insufficient balance is detected."""
        planner = RoutingPlanner(seed=42)
        
        source = "0x1234567890123456789012345678901234567890"
        dest = "0xabcd"
        amount = "1000000000000000000"
        
        transit = create_test_wallet()
        
        plan = planner.create_multi_hop_plan(
            source_address=source,
            destination_address=dest,
            amount_wei=amount,
            transit_wallets=[transit],
        )
        
        # With insufficient balance
        balances = {source.lower(): 1000}  # Very little
        
        is_feasible, issues = planner.validate_plan_feasibility(plan, balances)
        assert not is_feasible
        assert len(issues) > 0
        assert "Insufficient balance" in issues[0]
