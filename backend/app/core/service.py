"""
HideX Core Service.

Central orchestration service that coordinates all modules.
Provides a unified interface for the API layer.
"""

from pathlib import Path
from typing import Optional
from datetime import datetime

from ..models.wallet import Wallet, WalletRole
from ..models.transaction import TransactionPlan, TransactionStatus
from ..models.policy import Policy, PolicyValidationResult
from ..models.risk import RiskScore

from ..modules.policy_engine import PolicyEngine, create_default_policy
from ..modules.wallet_manager import WalletManager
from ..modules.risk_engine import RiskEngine
from ..modules.routing_planner import RoutingPlanner
from ..modules.transaction_executor import TransactionExecutor
from ..modules.audit_logger import AuditLogger

from ..config import get_settings


class HideXService:
    """
    HideX Core Service.
    
    Orchestrates all modules and provides a unified interface:
    - Policy management
    - Wallet management
    - Route planning
    - Risk assessment
    - Transaction execution (with confirmation)
    - Audit logging
    
    All operations are designed to be:
    - Explainable
    - Auditable
    - User-approved
    """
    
    def __init__(
        self,
        keystore_password: Optional[str] = None,
        seed: Optional[int] = None,
        web3_provider: Optional[str] = None,
    ):
        """
        Initialize HideX Service.
        
        Args:
            keystore_password: Password for wallet encryption
            seed: Seed for deterministic operations
            web3_provider: Web3 provider URL for execution
        """
        self._settings = get_settings()
        
        # Initialize modules
        self._policy_engine = PolicyEngine()
        self._wallet_manager = WalletManager(password=keystore_password)
        self._risk_engine = RiskEngine(seed=seed)
        self._routing_planner = RoutingPlanner(seed=seed)
        self._transaction_executor = TransactionExecutor(
            web3_provider=web3_provider,
            seed=seed,
        )
        self._audit_logger = AuditLogger()
        
        # Log startup
        self._audit_logger.log_system_start()
        
        # Load default policy
        self._setup_default_policy()
    
    def _setup_default_policy(self) -> None:
        """Setup default policy if none exists."""
        default = create_default_policy()
        self._policy_engine._policies[default.id] = default
        self._policy_engine.set_active_policy(default.id)
        self._audit_logger.log_policy_loaded(default.id, default.name)
    
    # ============================================================
    # Wallet Management
    # ============================================================
    
    def initialize_wallet(self, mnemonic: Optional[str] = None) -> str:
        """
        Initialize wallet system with mnemonic.
        
        Args:
            mnemonic: Optional existing mnemonic (generates new if None)
            
        Returns:
            The mnemonic (STORE SECURELY!)
        """
        if mnemonic:
            self._wallet_manager.set_mnemonic(mnemonic)
            return mnemonic
        else:
            new_mnemonic = self._wallet_manager.generate_mnemonic()
            self._wallet_manager.set_mnemonic(new_mnemonic)
            return new_mnemonic
    
    def load_wallet(self) -> bool:
        """Load existing wallet from encrypted storage."""
        return self._wallet_manager.load_mnemonic()
    
    def create_wallet(
        self,
        role: WalletRole,
        label: Optional[str] = None,
        chain: str = "ethereum"
    ) -> Wallet:
        """Create a new wallet with specified role."""
        wallet = self._wallet_manager.create_wallet(role, label, chain)
        self._audit_logger.log_wallet_created(wallet)
        return wallet
    
    def list_wallets(
        self,
        role: Optional[WalletRole] = None
    ) -> list[Wallet]:
        """List all wallets, optionally filtered by role."""
        return self._wallet_manager.list_wallets(role=role)
    
    def get_wallet(self, wallet_id: str) -> Optional[Wallet]:
        """Get wallet by ID."""
        return self._wallet_manager.get_wallet(wallet_id)
    
    def retire_wallet(self, wallet_id: str) -> Wallet:
        """Retire a wallet from use."""
        wallet = self._wallet_manager.retire_wallet(wallet_id)
        self._audit_logger.log_wallet_retired(wallet)
        return wallet
    
    # ============================================================
    # Policy Management
    # ============================================================
    
    def load_policy(self, policy_path: Path) -> Policy:
        """Load a policy from JSON file."""
        policy = self._policy_engine.load_policy(policy_path)
        self._audit_logger.log_policy_loaded(policy.id, policy.name)
        return policy
    
    def set_active_policy(self, policy_id: str) -> None:
        """Set the active policy for validation."""
        self._policy_engine.set_active_policy(policy_id)
    
    def list_policies(self) -> list[Policy]:
        """List all loaded policies."""
        return self._policy_engine.list_policies()
    
    def get_policy(self, policy_id: str) -> Optional[Policy]:
        """Get a policy by ID."""
        return self._policy_engine.get_policy(policy_id)
    
    # ============================================================
    # Route Planning
    # ============================================================
    
    def create_simple_plan(
        self,
        source_address: str,
        destination_address: str,
        amount_wei: str,
        chain: str = "ethereum",
        name: Optional[str] = None,
    ) -> TransactionPlan:
        """Create a simple single-hop transfer plan."""
        plan = self._routing_planner.create_simple_plan(
            source_address=source_address,
            destination_address=destination_address,
            amount_wei=amount_wei,
            chain=chain,
            name=name,
        )
        self._audit_logger.log_plan_created(plan)
        return plan
    
    def create_multi_hop_plan(
        self,
        source_address: str,
        destination_address: str,
        amount_wei: str,
        num_hops: int = 2,
        chain: str = "ethereum",
        name: Optional[str] = None,
        min_delay_seconds: int = 300,
        max_delay_seconds: int = 3600,
    ) -> TransactionPlan:
        """
        Create a multi-hop transfer plan.
        
        Automatically creates transit wallets as needed.
        """
        # Create transit wallets
        transit_wallets = []
        for i in range(num_hops):
            wallet = self.create_wallet(
                role=WalletRole.TRANSIT,
                label=f"transit_{i}",
                chain=chain,
            )
            transit_wallets.append(wallet)
        
        plan = self._routing_planner.create_multi_hop_plan(
            source_address=source_address,
            destination_address=destination_address,
            amount_wei=amount_wei,
            transit_wallets=transit_wallets,
            chain=chain,
            name=name,
            min_delay_seconds=min_delay_seconds,
            max_delay_seconds=max_delay_seconds,
        )
        self._audit_logger.log_plan_created(plan)
        return plan
    
    def create_split_plan(
        self,
        source_address: str,
        destination_address: str,
        amount_wei: str,
        num_splits: int = 3,
        chain: str = "ethereum",
        name: Optional[str] = None,
    ) -> TransactionPlan:
        """
        Create a split-amount transfer plan.
        
        Splits amount across multiple paths.
        """
        # Create transit wallets for splitting
        transit_wallets = []
        for i in range(num_splits):
            wallet = self.create_wallet(
                role=WalletRole.TRANSIT,
                label=f"split_{i}",
                chain=chain,
            )
            transit_wallets.append(wallet)
        
        plan = self._routing_planner.create_split_plan(
            source_address=source_address,
            destination_address=destination_address,
            amount_wei=amount_wei,
            transit_wallets=transit_wallets,
            num_splits=num_splits,
            chain=chain,
            name=name,
        )
        self._audit_logger.log_plan_created(plan)
        return plan
    
    # ============================================================
    # Risk Assessment
    # ============================================================
    
    def assess_risk(
        self,
        plan: TransactionPlan,
        known_cex_addresses: Optional[set[str]] = None
    ) -> RiskScore:
        """
        Assess risk for a transaction plan.
        
        Returns detailed, explainable risk score.
        """
        source_wallet = self._wallet_manager.get_wallet_by_address(
            plan.source_address
        )
        
        risk_score = self._risk_engine.calculate_risk(
            plan=plan,
            source_wallet=source_wallet,
            known_cex_addresses=known_cex_addresses,
        )
        
        # Update plan with risk info
        plan.risk_score = risk_score.score
        plan.risk_band = risk_score.band.value
        plan.risk_factors = [f.name for f in risk_score.factors]
        plan.risk_explanation = risk_score.explanation
        
        self._audit_logger.log_risk_calculated(plan.id, risk_score)
        
        return risk_score
    
    # ============================================================
    # Policy Validation
    # ============================================================
    
    def validate_plan(
        self,
        plan: TransactionPlan,
        policy_id: Optional[str] = None
    ) -> PolicyValidationResult:
        """
        Validate a plan against policy.
        
        Returns detailed validation result with any violations.
        """
        policy = None
        if policy_id:
            policy = self._policy_engine.get_policy(policy_id)
        
        result = self._policy_engine.validate_plan(plan, policy)
        
        # Update plan with validation info
        plan.policy_violations = [v.message for v in result.violations if v.severity == "error"]
        plan.policy_warnings = [v.message for v in result.violations if v.severity == "warning"]
        plan.is_policy_compliant = result.is_compliant
        
        self._audit_logger.log_policy_validated(result)
        
        return result
    
    # ============================================================
    # Simulation
    # ============================================================
    
    def simulate_plan(self, plan: TransactionPlan) -> TransactionPlan:
        """
        Simulate a transaction plan.
        
        This runs the plan through:
        1. Risk assessment
        2. Policy validation
        3. Execution simulation
        
        Returns updated plan with all assessments.
        """
        # Assess risk
        self.assess_risk(plan)
        
        # Validate against policy
        self.validate_plan(plan)
        
        # Run execution simulation
        plan = self._transaction_executor.simulate_plan(plan)
        
        self._audit_logger.log_plan_simulated(
            plan,
            RiskScore(
                plan_id=plan.id,
                score=plan.risk_score or 0,
                band=plan.risk_band or "LOW",
                factors=[],
                summary="",
                explanation="",
            )
        )
        
        return plan
    
    # ============================================================
    # Execution
    # ============================================================
    
    async def execute_plan(
        self,
        plan: TransactionPlan,
        confirmation_override: bool = False
    ) -> TransactionPlan:
        """
        Execute a transaction plan.
        
        REQUIRES:
        1. Plan must be simulated first
        2. Explicit user confirmation
        
        Args:
            plan: The plan to execute
            confirmation_override: Set to True to confirm (use with caution)
            
        Returns:
            Updated plan with execution results
        """
        if plan.status != TransactionStatus.SIMULATED:
            raise ValueError("Plan must be simulated before execution")
        
        if plan.is_dry_run and not confirmation_override:
            raise ValueError(
                "Plan is in dry-run mode. "
                "Set is_dry_run=False and confirmation_override=True to execute."
            )
        
        # Set up confirmation callback
        if confirmation_override:
            self._transaction_executor._confirmation_callback = lambda _: True
        
        # Log confirmation
        self._audit_logger.log_plan_confirmed(plan)
        
        # Define signing function
        def sign_transaction(address: str, tx_dict: dict) -> str:
            wallet = self._wallet_manager.get_wallet_by_address(address)
            if not wallet:
                raise ValueError(f"Wallet not found for address: {address}")
            
            account = self._wallet_manager.get_signing_account(wallet.id)
            
            # Mark wallet as used
            self._wallet_manager.mark_wallet_used(wallet.id)
            
            # Sign and return
            signed = account.sign_transaction(tx_dict)
            return signed.rawTransaction
        
        # Execute
        plan = await self._transaction_executor.execute_plan(
            plan=plan,
            signing_func=sign_transaction,
            force_execution=confirmation_override,
        )
        
        # Log results
        for step in plan.steps:
            if step.tx_hash:
                self._audit_logger.log_transaction_executed(
                    plan=plan,
                    step=step,
                    tx_hash=step.tx_hash,
                    block_number=step.block_number or 0,
                    gas_used=step.gas_limit or 21000,
                )
            elif step.error_message:
                self._audit_logger.log_transaction_failed(
                    plan=plan,
                    step=step,
                    error=step.error_message,
                )
        
        return plan
    
    # ============================================================
    # Audit & Compliance
    # ============================================================
    
    def get_audit_log(self):
        """Get current session's audit log."""
        return self._audit_logger.get_current_log()
    
    def generate_compliance_report(self, plan_id: str) -> dict:
        """Generate compliance report for a plan."""
        return self._audit_logger.generate_compliance_report(plan_id)
    
    def list_audit_sessions(self) -> list[str]:
        """List all available audit sessions."""
        return self._audit_logger.list_sessions()
    
    def load_audit_session(self, session_id: str):
        """Load a previous audit session."""
        return self._audit_logger.load_session_log(session_id)
    
    # ============================================================
    # Cleanup
    # ============================================================
    
    def shutdown(self) -> None:
        """Graceful shutdown."""
        self._wallet_manager.save_state()
        self._audit_logger.log_system_stop()
