"""
Routing Planner for HideX.

The Routing Planner is responsible for:
- Planning multi-hop transaction routes
- Amount splitting strategies
- Timing randomization
- Chain-aware logic
- Policy compliance

Design principles:
- MUST obey all policies
- MUST show full plan before execution
- MUST NOT auto-use mixers or privacy rails
- All plans are previewed and user-approved
"""

from datetime import datetime, timedelta
from typing import Optional
from decimal import Decimal

from ..models.transaction import TransactionPlan, TransactionStep, TransactionStatus
from ..models.wallet import Wallet, WalletRole
from ..models.policy import Policy
from ..utils.crypto import generate_id
from ..utils.random import SeededRandom
from ..config import get_settings


class RoutingPlanner:
    """
    Routing Planner.
    
    Creates transaction plans with:
    - Multi-hop routing through transit wallets
    - Amount splitting to reduce correlation
    - Timing randomization
    - Policy-compliant paths
    
    All plans must be explicitly approved before execution.
    """
    
    def __init__(self, seed: Optional[int] = None):
        """
        Initialize the Routing Planner.
        
        Args:
            seed: Optional seed for deterministic planning
        """
        settings = get_settings()
        self._seed = seed or settings.simulation_seed
        self._rng = SeededRandom(self._seed)
    
    def create_simple_plan(
        self,
        source_address: str,
        destination_address: str,
        amount_wei: str,
        chain: str = "ethereum",
        name: Optional[str] = None,
    ) -> TransactionPlan:
        """
        Create a simple single-hop transaction plan.
        
        This is the baseline - not recommended for privacy.
        """
        plan_id = generate_id("plan")
        step_id = generate_id("step")
        
        amount_formatted = self._format_amount(amount_wei, chain)
        
        step = TransactionStep(
            id=step_id,
            order=0,
            from_address=source_address,
            to_address=destination_address,
            chain=chain,
            amount=amount_wei,
            amount_formatted=amount_formatted,
            delay_seconds=0,
            description="Direct transfer",
        )
        
        return TransactionPlan(
            id=plan_id,
            name=name or "Simple Transfer",
            description="Direct single-hop transfer (not privacy-optimized)",
            source_address=source_address,
            destination_address=destination_address,
            total_amount=amount_wei,
            total_amount_formatted=amount_formatted,
            chain=chain,
            steps=[step],
            status=TransactionStatus.PLANNED,
            is_dry_run=True,
        )
    
    def create_multi_hop_plan(
        self,
        source_address: str,
        destination_address: str,
        amount_wei: str,
        transit_wallets: list[Wallet],
        chain: str = "ethereum",
        name: Optional[str] = None,
        min_delay_seconds: int = 300,
        max_delay_seconds: int = 3600,
    ) -> TransactionPlan:
        """
        Create a multi-hop transaction plan through transit wallets.
        
        Args:
            source_address: Source wallet address
            destination_address: Final destination address
            amount_wei: Total amount in wei
            transit_wallets: List of transit wallets to route through
            chain: Blockchain network
            name: Optional plan name
            min_delay_seconds: Minimum delay between hops
            max_delay_seconds: Maximum delay between hops
            
        Returns:
            TransactionPlan with multiple hops
        """
        plan_id = generate_id("plan")
        total_amount = int(amount_wei)
        amount_formatted = self._format_amount(amount_wei, chain)
        
        steps = []
        current_address = source_address
        
        # Create hop through each transit wallet
        for i, transit_wallet in enumerate(transit_wallets):
            step_id = generate_id("step")
            
            # Calculate delay (randomized)
            delay = self._rng.random_delay(min_delay_seconds, max_delay_seconds)
            
            step = TransactionStep(
                id=step_id,
                order=i,
                from_address=current_address,
                to_address=transit_wallet.address,
                chain=chain,
                amount=amount_wei,
                amount_formatted=amount_formatted,
                delay_seconds=delay,
                description=f"Hop {i + 1}: Transit through {transit_wallet.label or transit_wallet.address[:10]}...",
            )
            steps.append(step)
            current_address = transit_wallet.address
        
        # Final step to destination
        final_step = TransactionStep(
            id=generate_id("step"),
            order=len(transit_wallets),
            from_address=current_address,
            to_address=destination_address,
            chain=chain,
            amount=amount_wei,
            amount_formatted=amount_formatted,
            delay_seconds=self._rng.random_delay(min_delay_seconds, max_delay_seconds),
            description="Final hop to destination",
        )
        steps.append(final_step)
        
        return TransactionPlan(
            id=plan_id,
            name=name or f"Multi-hop ({len(steps)} hops)",
            description=f"Multi-hop transfer through {len(transit_wallets)} transit wallet(s)",
            source_address=source_address,
            destination_address=destination_address,
            total_amount=amount_wei,
            total_amount_formatted=amount_formatted,
            chain=chain,
            steps=steps,
            status=TransactionStatus.PLANNED,
            is_dry_run=True,
        )
    
    def create_split_plan(
        self,
        source_address: str,
        destination_address: str,
        amount_wei: str,
        transit_wallets: list[Wallet],
        num_splits: int = 3,
        chain: str = "ethereum",
        name: Optional[str] = None,
        min_delay_seconds: int = 300,
        max_delay_seconds: int = 3600,
    ) -> TransactionPlan:
        """
        Create a split-amount transaction plan.
        
        Splits the amount across multiple paths with varying amounts
        and timing to reduce correlation.
        
        Args:
            source_address: Source wallet address
            destination_address: Final destination address
            amount_wei: Total amount in wei
            transit_wallets: Transit wallets (need at least num_splits)
            num_splits: Number of paths to split across
            chain: Blockchain network
            name: Optional plan name
            min_delay_seconds: Minimum delay between hops
            max_delay_seconds: Maximum delay between hops
            
        Returns:
            TransactionPlan with split paths
        """
        if len(transit_wallets) < num_splits:
            raise ValueError(f"Need at least {num_splits} transit wallets for splitting")
        
        plan_id = generate_id("plan")
        total_amount = int(amount_wei)
        amount_formatted = self._format_amount(amount_wei, chain)
        
        # Split amounts with variation
        split_amounts = self._split_amount(total_amount, num_splits)
        
        steps = []
        order = 0
        
        # Phase 1: Source to transit wallets
        for i in range(num_splits):
            transit = transit_wallets[i]
            split_amount = split_amounts[i]
            delay = self._rng.random_delay(min_delay_seconds, max_delay_seconds)
            
            step = TransactionStep(
                id=generate_id("step"),
                order=order,
                from_address=source_address,
                to_address=transit.address,
                chain=chain,
                amount=str(split_amount),
                amount_formatted=self._format_amount(str(split_amount), chain),
                delay_seconds=delay if i > 0 else 0,  # First tx immediate
                description=f"Split {i + 1}/{num_splits}: Source to transit",
            )
            steps.append(step)
            order += 1
        
        # Phase 2: Transit wallets to destination
        for i in range(num_splits):
            transit = transit_wallets[i]
            split_amount = split_amounts[i]
            # Add significant delay for second phase
            delay = self._rng.random_delay(
                min_delay_seconds * 2,
                max_delay_seconds * 2
            )
            
            step = TransactionStep(
                id=generate_id("step"),
                order=order,
                from_address=transit.address,
                to_address=destination_address,
                chain=chain,
                amount=str(split_amount),
                amount_formatted=self._format_amount(str(split_amount), chain),
                delay_seconds=delay,
                description=f"Consolidate {i + 1}/{num_splits}: Transit to destination",
            )
            steps.append(step)
            order += 1
        
        return TransactionPlan(
            id=plan_id,
            name=name or f"Split ({num_splits} paths)",
            description=f"Split transfer across {num_splits} paths with varied amounts",
            source_address=source_address,
            destination_address=destination_address,
            total_amount=amount_wei,
            total_amount_formatted=amount_formatted,
            chain=chain,
            steps=steps,
            status=TransactionStatus.PLANNED,
            is_dry_run=True,
        )
    
    def _split_amount(self, total: int, num_splits: int) -> list[int]:
        """
        Split an amount into non-equal parts.
        
        Ensures variation to avoid easy correlation.
        """
        if num_splits <= 0:
            return []
        if num_splits == 1:
            return [total]
        
        # Generate random proportions
        proportions = [self._rng.uniform(0.5, 1.5) for _ in range(num_splits)]
        total_proportion = sum(proportions)
        
        # Allocate amounts based on proportions
        amounts = []
        remaining = total
        
        for i in range(num_splits - 1):
            proportion = proportions[i] / total_proportion
            amount = int(total * proportion)
            # Add small random variation
            amount = self._rng.random_amount_variation(amount, 0.03)
            amount = max(1, min(amount, remaining - (num_splits - i - 1)))
            amounts.append(amount)
            remaining -= amount
        
        # Last split gets remainder
        amounts.append(remaining)
        
        return amounts
    
    def _format_amount(self, amount_wei: str, chain: str) -> str:
        """Format amount for display."""
        try:
            wei = int(amount_wei)
            eth = wei / 10**18
            if chain in ["ethereum", "polygon", "arbitrum", "optimism"]:
                return f"{eth:.6f} ETH"
            else:
                return f"{eth:.6f}"
        except ValueError:
            return amount_wei
    
    def estimate_total_time(self, plan: TransactionPlan) -> timedelta:
        """Estimate total time to execute a plan."""
        total_seconds = sum(step.delay_seconds for step in plan.steps)
        return timedelta(seconds=total_seconds)
    
    def add_timing_randomization(
        self,
        plan: TransactionPlan,
        jitter_percent: float = 0.2
    ) -> TransactionPlan:
        """
        Add random jitter to all delays in a plan.
        
        This helps avoid timing correlation attacks.
        """
        for step in plan.steps:
            if step.delay_seconds > 0:
                jitter = int(step.delay_seconds * jitter_percent * 
                           (self._rng.random() - 0.5) * 2)
                step.delay_seconds = max(60, step.delay_seconds + jitter)
        
        return plan
    
    def validate_plan_feasibility(
        self,
        plan: TransactionPlan,
        wallet_balances: dict[str, int]
    ) -> tuple[bool, list[str]]:
        """
        Validate that a plan is feasible with given balances.
        
        Returns:
            (is_feasible, list of issues)
        """
        issues = []
        
        # Track balances through simulation
        simulated_balances = wallet_balances.copy()
        
        for step in plan.steps:
            from_addr = step.from_address.lower()
            amount = int(step.amount)
            
            # Check balance
            current = simulated_balances.get(from_addr, 0)
            if current < amount:
                issues.append(
                    f"Step {step.order}: Insufficient balance at {from_addr[:10]}... "
                    f"(need {amount}, have {current})"
                )
            else:
                # Update balances
                simulated_balances[from_addr] = current - amount
                to_addr = step.to_address.lower()
                simulated_balances[to_addr] = simulated_balances.get(to_addr, 0) + amount
        
        return len(issues) == 0, issues
