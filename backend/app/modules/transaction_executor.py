"""
Transaction Executor for HideX.

The Transaction Executor is responsible for:
- Executing transaction plans (with explicit confirmation)
- Dry-run mode by default
- Gas/fee randomization
- Graceful error handling
- Logging all executed transactions

Design principles:
- SIMULATION ONLY by default
- Explicit user confirmation required
- All actions are logged
- Failures are handled gracefully
"""

import asyncio
import time
from datetime import datetime
from typing import Optional, Callable

from ..models.transaction import (
    TransactionPlan,
    TransactionStep,
    TransactionStatus,
    Transaction,
)
from ..models.wallet import Wallet
from ..utils.crypto import generate_id
from ..utils.random import SeededRandom
from ..config import get_settings


class ExecutionResult:
    """Result of a transaction execution."""
    
    def __init__(
        self,
        success: bool,
        tx_hash: Optional[str] = None,
        block_number: Optional[int] = None,
        gas_used: Optional[int] = None,
        error: Optional[str] = None
    ):
        self.success = success
        self.tx_hash = tx_hash
        self.block_number = block_number
        self.gas_used = gas_used
        self.error = error


class TransactionExecutor:
    """
    Transaction Executor.
    
    Executes transaction plans with:
    - Dry-run mode by default (simulation only)
    - Explicit user confirmation required
    - Gas randomization within safe bounds
    - Graceful error handling
    - Full logging of all operations
    
    IMPORTANT: Execution is ALWAYS opt-in.
    """
    
    # Gas randomization bounds (percent variation)
    GAS_LIMIT_VARIATION = 0.05  # 5% variation
    GAS_PRICE_VARIATION = 0.03  # 3% variation
    
    def __init__(
        self,
        web3_provider: Optional[str] = None,
        seed: Optional[int] = None,
        confirmation_callback: Optional[Callable[[str], bool]] = None
    ):
        """
        Initialize the Transaction Executor.
        
        Args:
            web3_provider: Web3 provider URL (for live execution)
            seed: Optional seed for deterministic gas randomization
            confirmation_callback: Function to call for user confirmation
        """
        settings = get_settings()
        self._seed = seed or settings.simulation_seed
        self._rng = SeededRandom(self._seed)
        self._web3_provider = web3_provider
        self._web3 = None
        
        # Confirmation callback (must return True to proceed)
        self._confirmation_callback = confirmation_callback
        
        # Execution log
        self._executed_transactions: list[Transaction] = []
    
    def _get_web3(self):
        """Get or create Web3 instance."""
        if self._web3 is None and self._web3_provider:
            from web3 import Web3
            self._web3 = Web3(Web3.HTTPProvider(self._web3_provider))
        return self._web3
    
    def simulate_plan(self, plan: TransactionPlan) -> TransactionPlan:
        """
        Simulate a transaction plan without execution.
        
        This is the default mode and should always be run first.
        
        Returns:
            Updated plan with simulation results
        """
        plan.status = TransactionStatus.SIMULATED
        plan.simulated_at = datetime.utcnow()
        
        # Simulate each step
        total_estimated_gas = 0
        for step in plan.steps:
            # Estimate gas (simplified - real implementation would query chain)
            estimated_gas = 21000  # Base ETH transfer
            if step.token_address:
                estimated_gas = 65000  # ERC20 transfer
            
            # Apply randomization for realistic simulation
            step.gas_limit = self._randomize_gas_limit(estimated_gas)
            total_estimated_gas += step.gas_limit
        
        plan.metadata["estimated_total_gas"] = total_estimated_gas
        plan.metadata["simulated"] = True
        
        return plan
    
    def request_confirmation(self, plan: TransactionPlan) -> bool:
        """
        Request explicit user confirmation before execution.
        
        REQUIRED before any live execution.
        
        Returns:
            True if user confirms, False otherwise
        """
        if self._confirmation_callback:
            # Build confirmation message
            message = self._build_confirmation_message(plan)
            return self._confirmation_callback(message)
        
        # No callback means no confirmation possible
        return False
    
    def _build_confirmation_message(self, plan: TransactionPlan) -> str:
        """Build a human-readable confirmation message."""
        lines = [
            "=" * 50,
            "TRANSACTION EXECUTION CONFIRMATION",
            "=" * 50,
            "",
            f"Plan: {plan.name or plan.id}",
            f"Total Amount: {plan.total_amount_formatted}",
            f"Steps: {len(plan.steps)}",
            "",
            "Steps to Execute:",
        ]
        
        for step in plan.steps:
            lines.append(
                f"  {step.order + 1}. {step.from_address[:10]}... -> "
                f"{step.to_address[:10]}... ({step.amount_formatted})"
            )
            if step.delay_seconds > 0:
                lines.append(f"     Delay: {step.delay_seconds}s")
        
        lines.extend([
            "",
            "Risk Assessment:",
            f"  Score: {plan.risk_score or 'Not assessed'}/100",
            f"  Band: {plan.risk_band or 'Not assessed'}",
        ])
        
        if plan.policy_violations:
            lines.append("")
            lines.append("⚠️ Policy Violations:")
            for v in plan.policy_violations:
                lines.append(f"  - {v}")
        
        lines.extend([
            "",
            "=" * 50,
            "Do you confirm execution? (This action cannot be undone)",
            "=" * 50,
        ])
        
        return "\n".join(lines)
    
    async def execute_plan(
        self,
        plan: TransactionPlan,
        signing_func: Callable[[str, dict], str],
        force_execution: bool = False
    ) -> TransactionPlan:
        """
        Execute a transaction plan.
        
        Args:
            plan: The plan to execute
            signing_func: Function to sign transactions (wallet_id, tx_dict) -> signed_tx
            force_execution: Override dry-run (requires explicit confirmation)
            
        Returns:
            Updated plan with execution results
            
        Raises:
            ValueError: If confirmation not obtained or plan is not ready
        """
        # Check dry-run mode
        if plan.is_dry_run and not force_execution:
            raise ValueError(
                "Plan is in dry-run mode. "
                "Set force_execution=True and obtain confirmation to execute."
            )
        
        # Verify simulation was run
        if plan.status == TransactionStatus.PLANNED:
            raise ValueError("Plan must be simulated before execution")
        
        # Request confirmation
        if not self.request_confirmation(plan):
            plan.status = TransactionStatus.CANCELLED
            return plan
        
        plan.status = TransactionStatus.CONFIRMED
        plan.confirmed_at = datetime.utcnow()
        
        # Execute steps in order
        plan.status = TransactionStatus.EXECUTING
        
        for step in plan.steps:
            try:
                # Wait for delay
                if step.delay_seconds > 0:
                    await asyncio.sleep(step.delay_seconds)
                
                # Execute step
                result = await self._execute_step(step, signing_func)
                
                if result.success:
                    step.status = TransactionStatus.EXECUTED
                    step.tx_hash = result.tx_hash
                    step.block_number = result.block_number
                    
                    # Log transaction
                    self._log_transaction(plan, step, result)
                else:
                    step.status = TransactionStatus.FAILED
                    step.error_message = result.error
                    
                    # Abort remaining steps on failure
                    plan.status = TransactionStatus.FAILED
                    break
                    
            except Exception as e:
                step.status = TransactionStatus.FAILED
                step.error_message = str(e)
                plan.status = TransactionStatus.FAILED
                break
        
        if plan.status != TransactionStatus.FAILED:
            plan.status = TransactionStatus.EXECUTED
            plan.executed_at = datetime.utcnow()
        
        return plan
    
    async def _execute_step(
        self,
        step: TransactionStep,
        signing_func: Callable[[str, dict], str]
    ) -> ExecutionResult:
        """
        Execute a single transaction step.
        
        This is where the actual blockchain interaction happens.
        """
        web3 = self._get_web3()
        
        if web3 is None:
            # Simulation mode - return mock success
            return ExecutionResult(
                success=True,
                tx_hash=f"0x{'0' * 64}",  # Mock hash
                block_number=0,
                gas_used=step.gas_limit or 21000,
            )
        
        try:
            # Build transaction
            tx = {
                'from': step.from_address,
                'to': step.to_address,
                'value': int(step.amount),
                'gas': step.gas_limit or 21000,
                'nonce': web3.eth.get_transaction_count(step.from_address),
            }
            
            # Get gas price with randomization
            gas_price = web3.eth.gas_price
            tx['gasPrice'] = self._randomize_gas_price(gas_price)
            
            # For ERC20 transfers
            if step.token_address:
                # Build ERC20 transfer data
                # This is simplified - real implementation would use contract ABI
                tx['to'] = step.token_address
                tx['value'] = 0
                # tx['data'] = encode transfer call
            
            # Sign transaction
            signed_tx = signing_func(step.from_address, tx)
            
            # Send transaction
            tx_hash = web3.eth.send_raw_transaction(signed_tx)
            
            # Wait for receipt
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
            
            return ExecutionResult(
                success=receipt['status'] == 1,
                tx_hash=tx_hash.hex(),
                block_number=receipt['blockNumber'],
                gas_used=receipt['gasUsed'],
                error="Transaction reverted" if receipt['status'] != 1 else None,
            )
            
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=str(e),
            )
    
    def _randomize_gas_limit(self, base_gas: int) -> int:
        """Add small random variation to gas limit."""
        variation = self._rng.uniform(
            1 - self.GAS_LIMIT_VARIATION,
            1 + self.GAS_LIMIT_VARIATION
        )
        return int(base_gas * variation)
    
    def _randomize_gas_price(self, base_price: int) -> int:
        """Add small random variation to gas price."""
        variation = self._rng.uniform(
            1 - self.GAS_PRICE_VARIATION,
            1 + self.GAS_PRICE_VARIATION
        )
        return int(base_price * variation)
    
    def _log_transaction(
        self,
        plan: TransactionPlan,
        step: TransactionStep,
        result: ExecutionResult
    ) -> None:
        """Log an executed transaction."""
        tx = Transaction(
            id=generate_id("tx"),
            plan_id=plan.id,
            step_id=step.id,
            tx_hash=result.tx_hash or "",
            from_address=step.from_address,
            to_address=step.to_address,
            amount=step.amount,
            chain=step.chain,
            block_number=result.block_number or 0,
            timestamp=datetime.utcnow(),
            gas_used=result.gas_used or 0,
            gas_price=step.gas_price or "0",
            status="success" if result.success else "failed",
            metadata={
                "step_order": step.order,
                "delay_seconds": step.delay_seconds,
            },
        )
        self._executed_transactions.append(tx)
    
    def get_execution_history(self) -> list[Transaction]:
        """Get all executed transactions."""
        return self._executed_transactions.copy()
    
    def get_plan_transactions(self, plan_id: str) -> list[Transaction]:
        """Get all transactions for a specific plan."""
        return [tx for tx in self._executed_transactions if tx.plan_id == plan_id]


def create_confirmation_prompt() -> Callable[[str], bool]:
    """
    Create a command-line confirmation prompt.
    
    For use in CLI applications.
    """
    def prompt(message: str) -> bool:
        print(message)
        response = input("\nType 'CONFIRM' to proceed: ")
        return response.strip().upper() == "CONFIRM"
    
    return prompt
