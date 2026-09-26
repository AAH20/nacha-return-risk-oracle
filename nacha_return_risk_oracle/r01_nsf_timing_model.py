"""
R01 (Insufficient Funds) Predictive Payday & Balance Timing Model.
Calculates NSF return probabilities prior to FedACH submission based on
payroll direct deposit cycle alignment and account liquidity buffers.
Zero external dependencies (pure Python standard library).
"""

from typing import List, Tuple

from .models import ACHEntry, RiskTier


class R01NSFTimingModel:
    """Predicts likelihood of NACHA Return Code R01 (Insufficient Funds)."""

    def evaluate_nsf_risk(self, entry: ACHEntry) -> Tuple[float, List[str], str]:
        """
        Computes R01 return probability [0.0 - 1.0].
        Returns:
            (probability, reasons, recommended_action)
        """
        reasons: List[str] = []
        score = 0.0

        # 1. Payday Cycle Alignment (Bi-weekly payroll decay curve)
        # Days 0-2 post-payday: Low NSF. Days 11-14 (tail end of paycheck): Severe NSF risk
        if entry.days_since_last_payday >= 11:
            score += 0.35
            reasons.append(f"Tail end of payroll cycle ({entry.days_since_last_payday} days since payday); median consumer balance depleted")
        elif entry.days_since_last_payday <= 2:
            score = max(0.0, score - 0.10)  # Post-payday liquidity peak

        # 2. Balance-to-Debit Ratio
        if entry.estimated_account_balance > 0:
            coverage_ratio = entry.amount / entry.estimated_account_balance
            if coverage_ratio >= 1.0:
                score += 0.50
                reasons.append(f"Debit amount (${entry.amount:,.2f}) exceeds estimated account balance (${entry.estimated_account_balance:,.2f})")
            elif coverage_ratio >= 0.75:
                score += 0.25
                reasons.append(f"High balance utilization ({coverage_ratio*100:.1f}% of estimated balance)")

        # 3. Recidivism History (Prior R01 returns)
        if entry.previous_r01_count >= 2:
            score += 0.30
            reasons.append(f"Chronic NSF debtor: {entry.previous_r01_count} prior R01 returns in last 90 days")
        elif entry.previous_r01_count == 1:
            score += 0.15
            reasons.append("1 prior R01 return on file")

        prob = min(1.0, max(0.0, round(score, 3)))

        action = "DISPATCH"
        if prob >= 0.65:
            action = "DELAY_FOR_PAYDAY"
        elif prob >= 0.40:
            action = "REVIEW_BALANCE"

        return prob, reasons, action
