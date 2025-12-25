"""
Risk Simulation & Scoring Engine for HideX.

The Risk Engine is responsible for:
- Simulating transaction paths before execution
- Producing explainable risk scores (0-100)
- Classifying risk into bands (LOW/MEDIUM/HIGH)
- Providing human-readable explanations

Design principles:
- Deterministic (same inputs = same output)
- Explainable (no black-box ML)
- Transparent (all factors documented)
- Seedable randomness for simulations
"""

from datetime import datetime
from typing import Optional
from decimal import Decimal

from ..models.risk import RiskScore, RiskBand, RiskFactor, RiskFactorType
from ..models.transaction import TransactionPlan, TransactionStep
from ..models.wallet import Wallet, WalletRole
from ..utils.random import SeededRandom
from ..config import get_settings


class RiskEngine:
    """
    Risk Simulation & Scoring Engine.
    
    Produces explainable risk scores based on:
    - Source contamination (CEX funding)
    - Timing correlation
    - Amount similarity
    - Address reuse
    - Cross-chain heuristics
    
    All scoring is deterministic and explainable.
    """
    
    # Risk factor weights (must sum to 1.0 for normalization)
    FACTOR_WEIGHTS = {
        RiskFactorType.SOURCE_CONTAMINATION: 0.25,
        RiskFactorType.TIMING_CORRELATION: 0.20,
        RiskFactorType.AMOUNT_SIMILARITY: 0.20,
        RiskFactorType.ADDRESS_REUSE: 0.15,
        RiskFactorType.CROSS_CHAIN_HEURISTIC: 0.10,
        RiskFactorType.SAME_BLOCK_ACTIVITY: 0.05,
        RiskFactorType.ROUND_AMOUNT: 0.03,
        RiskFactorType.GAS_PATTERN: 0.02,
    }
    
    def __init__(self, seed: Optional[int] = None):
        """
        Initialize the Risk Engine.
        
        Args:
            seed: Optional seed for deterministic simulations
        """
        settings = get_settings()
        self._seed = seed or settings.simulation_seed
        self._rng = SeededRandom(self._seed)
        
        # Risk thresholds
        self._low_threshold = settings.risk_low_threshold
        self._high_threshold = settings.risk_high_threshold
    
    def calculate_risk(
        self,
        plan: TransactionPlan,
        source_wallet: Optional[Wallet] = None,
        known_cex_addresses: Optional[set[str]] = None
    ) -> RiskScore:
        """
        Calculate risk score for a transaction plan.
        
        Args:
            plan: Transaction plan to assess
            source_wallet: Optional source wallet with metadata
            known_cex_addresses: Set of known CEX addresses
            
        Returns:
            Complete RiskScore with explanation
        """
        factors = []
        
        # Evaluate each risk factor
        factors.append(self._assess_source_contamination(
            plan, source_wallet, known_cex_addresses or set()
        ))
        factors.append(self._assess_timing_correlation(plan))
        factors.append(self._assess_amount_similarity(plan))
        factors.append(self._assess_address_reuse(plan))
        factors.append(self._assess_cross_chain(plan))
        factors.append(self._assess_same_block(plan))
        factors.append(self._assess_round_amounts(plan))
        factors.append(self._assess_gas_patterns(plan))
        
        # Calculate weighted score
        total_score = 0.0
        total_weight = 0.0
        
        for factor in factors:
            weight = self.FACTOR_WEIGHTS.get(factor.type, 0.1)
            factor.weight = weight
            total_score += factor.score * weight
            total_weight += weight
        
        # Normalize to 0-100
        final_score = int(total_score / total_weight) if total_weight > 0 else 0
        final_score = max(0, min(100, final_score))
        
        # Determine band
        if final_score <= self._low_threshold:
            band = RiskBand.LOW
        elif final_score <= self._high_threshold:
            band = RiskBand.MEDIUM
        else:
            band = RiskBand.HIGH
        
        # Generate summary and recommendations
        summary = self._generate_summary(final_score, band, factors)
        explanation = self._generate_explanation(factors)
        recommendations = self._generate_recommendations(factors)
        
        # Identify warnings and blockers
        warnings = []
        blockers = []
        
        for factor in factors:
            if factor.score >= 80:
                blockers.append(f"{factor.name}: {factor.explanation}")
            elif factor.score >= 50:
                warnings.append(f"{factor.name}: {factor.explanation}")
        
        return RiskScore(
            plan_id=plan.id,
            score=final_score,
            band=band,
            factors=factors,
            summary=summary,
            explanation=explanation,
            recommendations=recommendations,
            warnings=warnings,
            blockers=blockers,
            simulation_seed=self._seed,
        )
    
    def _assess_source_contamination(
        self,
        plan: TransactionPlan,
        source_wallet: Optional[Wallet],
        known_cex_addresses: set[str]
    ) -> RiskFactor:
        """
        Assess contamination from known sources (e.g., CEX).
        
        CEX-funded transactions are highly traceable.
        """
        score = 0
        explanation = "Source address analysis"
        details = {}
        
        source = plan.source_address.lower()
        
        # Check if source is a known CEX address
        if source in {addr.lower() for addr in known_cex_addresses}:
            score = 90
            explanation = "Source address is a known centralized exchange"
            details["cex_detected"] = True
        elif source_wallet and source_wallet.role == WalletRole.FUNDING:
            # Funding wallets may have CEX history
            score = 40
            explanation = "Source is a funding wallet (may have KYC history)"
            details["wallet_role"] = "funding"
        else:
            score = 10
            explanation = "Source address has no detected contamination"
        
        return RiskFactor(
            type=RiskFactorType.SOURCE_CONTAMINATION,
            name="Source Contamination",
            score=score,
            explanation=explanation,
            details=details,
            remediation="Use transit wallets to break direct links from CEX" if score > 30 else None,
        )
    
    def _assess_timing_correlation(self, plan: TransactionPlan) -> RiskFactor:
        """
        Assess timing correlation risk.
        
        Transactions close in time are easily linked.
        """
        if len(plan.steps) < 2:
            return RiskFactor(
                type=RiskFactorType.TIMING_CORRELATION,
                name="Timing Correlation",
                score=50,
                explanation="Single-step plan cannot be assessed for timing",
            )
        
        min_delay = float('inf')
        total_delay = 0
        
        for step in plan.steps:
            total_delay += step.delay_seconds
            if step.delay_seconds < min_delay:
                min_delay = step.delay_seconds
        
        avg_delay = total_delay / len(plan.steps)
        
        # Score based on minimum delay
        # <1 min: very high risk
        # 1-5 min: high risk
        # 5-30 min: medium risk
        # 30+ min: low risk
        if min_delay < 60:
            score = 85
            explanation = f"Minimum delay is only {min_delay}s - transactions easily correlated"
        elif min_delay < 300:
            score = 60
            explanation = f"Minimum delay is {min_delay}s - some timing correlation risk"
        elif min_delay < 1800:
            score = 30
            explanation = f"Minimum delay is {min_delay}s - moderate timing separation"
        else:
            score = 10
            explanation = f"Good timing separation with {min_delay}s minimum delay"
        
        return RiskFactor(
            type=RiskFactorType.TIMING_CORRELATION,
            name="Timing Correlation",
            score=score,
            explanation=explanation,
            details={"min_delay": min_delay, "avg_delay": avg_delay},
            remediation="Increase delays between steps" if score > 30 else None,
        )
    
    def _assess_amount_similarity(self, plan: TransactionPlan) -> RiskFactor:
        """
        Assess amount similarity risk.
        
        Similar amounts across steps are linkable.
        """
        if len(plan.steps) < 2:
            return RiskFactor(
                type=RiskFactorType.AMOUNT_SIMILARITY,
                name="Amount Similarity",
                score=30,
                explanation="Single-step plan has inherent amount linkage",
            )
        
        amounts = [int(step.amount) for step in plan.steps]
        total = int(plan.total_amount)
        
        # Check for exact splits or very similar amounts
        unique_amounts = len(set(amounts))
        if unique_amounts == 1:
            # All amounts are identical
            score = 80
            explanation = "All steps have identical amounts - trivially linkable"
        elif unique_amounts < len(amounts) * 0.5:
            score = 50
            explanation = "Multiple steps share the same amount"
        else:
            # Calculate variance
            avg = sum(amounts) / len(amounts)
            variance = sum((a - avg) ** 2 for a in amounts) / len(amounts)
            relative_variance = variance / (avg ** 2) if avg > 0 else 0
            
            if relative_variance < 0.01:
                score = 60
                explanation = "Amounts have low variance - may be linkable"
            elif relative_variance < 0.1:
                score = 30
                explanation = "Amounts have moderate variance"
            else:
                score = 10
                explanation = "Amounts have good variance"
        
        return RiskFactor(
            type=RiskFactorType.AMOUNT_SIMILARITY,
            name="Amount Similarity",
            score=score,
            explanation=explanation,
            details={"unique_amounts": unique_amounts, "step_count": len(amounts)},
            remediation="Vary amounts between steps" if score > 30 else None,
        )
    
    def _assess_address_reuse(self, plan: TransactionPlan) -> RiskFactor:
        """
        Assess address reuse risk.
        
        Reusing addresses creates permanent links.
        """
        addresses = []
        for step in plan.steps:
            addresses.append(step.from_address.lower())
            addresses.append(step.to_address.lower())
        
        unique = len(set(addresses))
        total = len(addresses)
        reuse_count = total - unique
        
        if reuse_count == 0:
            score = 0
            explanation = "No address reuse detected"
        elif reuse_count == 1:
            score = 40
            explanation = "One address is reused"
        elif reuse_count <= 3:
            score = 70
            explanation = f"{reuse_count} addresses are reused"
        else:
            score = 95
            explanation = f"Significant address reuse: {reuse_count} instances"
        
        return RiskFactor(
            type=RiskFactorType.ADDRESS_REUSE,
            name="Address Reuse",
            score=score,
            explanation=explanation,
            details={"reuse_count": reuse_count, "unique_addresses": unique},
            remediation="Use unique addresses for each step" if score > 0 else None,
        )
    
    def _assess_cross_chain(self, plan: TransactionPlan) -> RiskFactor:
        """
        Assess cross-chain correlation risk.
        
        Cross-chain transfers with matching amounts/timing are linkable.
        """
        chains = set()
        for step in plan.steps:
            chains.add(step.chain)
        
        if len(chains) <= 1:
            return RiskFactor(
                type=RiskFactorType.CROSS_CHAIN_HEURISTIC,
                name="Cross-Chain Heuristic",
                score=0,
                explanation="Single-chain plan - no cross-chain risks",
            )
        
        # Multi-chain increases complexity but also leaves more traces
        score = 30 + (len(chains) - 1) * 10
        score = min(score, 60)
        
        return RiskFactor(
            type=RiskFactorType.CROSS_CHAIN_HEURISTIC,
            name="Cross-Chain Heuristic",
            score=score,
            explanation=f"Plan spans {len(chains)} chains - cross-chain correlation possible",
            details={"chains": list(chains)},
            remediation="Consider chain-specific timing variation",
        )
    
    def _assess_same_block(self, plan: TransactionPlan) -> RiskFactor:
        """
        Assess same-block activity risk.
        
        Transactions in the same block are trivially linked.
        """
        blocks = {}
        for step in plan.steps:
            if step.block_number:
                if step.block_number in blocks:
                    blocks[step.block_number].append(step.id)
                else:
                    blocks[step.block_number] = [step.id]
        
        # Check for same-block transactions
        same_block_count = sum(1 for steps in blocks.values() if len(steps) > 1)
        
        if same_block_count > 0:
            score = 95
            explanation = f"{same_block_count} transactions share blocks"
        else:
            score = 0
            explanation = "No same-block activity detected"
        
        return RiskFactor(
            type=RiskFactorType.SAME_BLOCK_ACTIVITY,
            name="Same Block Activity",
            score=score,
            explanation=explanation,
            details={"same_block_count": same_block_count},
            remediation="Ensure transactions are in different blocks" if score > 0 else None,
        )
    
    def _assess_round_amounts(self, plan: TransactionPlan) -> RiskFactor:
        """
        Assess round amount risk.
        
        Round numbers (1 ETH, 0.5 ETH) are more memorable/linkable.
        """
        round_count = 0
        
        for step in plan.steps:
            try:
                amount = int(step.amount)
                # Check if amount is round (ends in many zeros)
                if amount > 0 and amount % (10 ** 15) == 0:  # 0.001 ETH granularity
                    round_count += 1
            except ValueError:
                pass
        
        if len(plan.steps) == 0:
            score = 0
        else:
            round_ratio = round_count / len(plan.steps)
            score = int(round_ratio * 50)
        
        if score > 30:
            explanation = f"{round_count} of {len(plan.steps)} steps use round amounts"
        else:
            explanation = "Amounts appear sufficiently non-round"
        
        return RiskFactor(
            type=RiskFactorType.ROUND_AMOUNT,
            name="Round Amount",
            score=score,
            explanation=explanation,
            details={"round_count": round_count},
            remediation="Add small random variations to amounts" if score > 30 else None,
        )
    
    def _assess_gas_patterns(self, plan: TransactionPlan) -> RiskFactor:
        """
        Assess gas pattern risk.
        
        Consistent gas patterns can be used for fingerprinting.
        """
        gas_limits = []
        for step in plan.steps:
            if step.gas_limit:
                gas_limits.append(step.gas_limit)
        
        if len(gas_limits) < 2:
            return RiskFactor(
                type=RiskFactorType.GAS_PATTERN,
                name="Gas Pattern",
                score=0,
                explanation="Insufficient data for gas pattern analysis",
            )
        
        # Check for identical gas limits
        unique_limits = len(set(gas_limits))
        if unique_limits == 1:
            score = 40
            explanation = "All transactions use identical gas limits"
        else:
            score = 10
            explanation = "Gas limits vary between transactions"
        
        return RiskFactor(
            type=RiskFactorType.GAS_PATTERN,
            name="Gas Pattern",
            score=score,
            explanation=explanation,
            details={"unique_gas_limits": unique_limits},
            remediation="Randomize gas limits within safe bounds" if score > 20 else None,
        )
    
    def _generate_summary(
        self,
        score: int,
        band: RiskBand,
        factors: list[RiskFactor]
    ) -> str:
        """Generate one-line summary."""
        high_risk_factors = [f for f in factors if f.score >= 60]
        
        if band == RiskBand.LOW:
            return f"Low risk ({score}/100) - Transaction plan appears well-structured"
        elif band == RiskBand.MEDIUM:
            top_issues = ", ".join(f.name for f in high_risk_factors[:2])
            return f"Medium risk ({score}/100) - Review recommended: {top_issues}"
        else:
            top_issues = ", ".join(f.name for f in high_risk_factors[:3])
            return f"High risk ({score}/100) - Significant issues: {top_issues}"
    
    def _generate_explanation(self, factors: list[RiskFactor]) -> str:
        """Generate detailed explanation."""
        lines = ["Risk Assessment Breakdown:", ""]
        
        for factor in sorted(factors, key=lambda f: f.score, reverse=True):
            status = "⚠️" if factor.score >= 50 else "✓"
            lines.append(f"{status} {factor.name} ({factor.score}/100): {factor.explanation}")
        
        return "\n".join(lines)
    
    def _generate_recommendations(self, factors: list[RiskFactor]) -> list[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        for factor in sorted(factors, key=lambda f: f.score, reverse=True):
            if factor.remediation and factor.score >= 30:
                recommendations.append(factor.remediation)
        
        return recommendations[:5]  # Top 5 recommendations
