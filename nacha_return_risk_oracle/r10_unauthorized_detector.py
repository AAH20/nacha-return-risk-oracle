"""
R10 (Customer Advises Unauthorized) & R05 Debit Risk Detector.
Evaluates unauthorized return probabilities under NACHA's strict 0.50% threshold.
Flags unvalidated micro-entries, internet-initiated (WEB) first-time spikes, and fraud history.
Zero external dependencies (pure Python standard library).
"""

from typing import List, Tuple

from .models import ACHEntry, StandardEntryClass


class R10UnauthorizedDetector:
    """Predicts likelihood of NACHA Unauthorized Return Codes (R05, R07, R10, R29)."""

    def evaluate_unauthorized_risk(self, entry: ACHEntry) -> Tuple[float, List[str], str]:
        """
        Computes R10/R05 unauthorized return probability [0.0 - 1.0].
        Returns:
            (probability, reasons, recommended_action)
        """
        reasons: List[str] = []
        score = 0.0

        # 1. NACHA Micro-Entry Rule Compliance
        if not entry.micro_entry_validated and entry.is_first_time_pull:
            score += 0.55
            reasons.append("NACHA Micro-Entry Violation: First-time debit pull initiated without completed micro-deposit validation")

        # 2. High-Risk SEC Code (WEB vs PPD)
        if entry.sec_code == StandardEntryClass.WEB:
            score += 0.15
            if entry.amount >= 1500.0 and entry.is_first_time_pull:
                score += 0.30
                reasons.append(f"High-exposure WEB debit (${entry.amount:,.2f}) on unseasoned debtor account")

        # 3. Debtor Prior Unauthorized Dispute History
        if entry.previous_r10_count >= 1:
            score += 0.40
            reasons.append(f"Debtor has {entry.previous_r10_count} prior R10 unauthorized dispute(s) on file")

        prob = min(1.0, max(0.0, round(score, 3)))

        action = "DISPATCH"
        if prob >= 0.50:
            action = "QUARANTINE"
        elif prob >= 0.25:
            action = "REQUIRE_REAUTHENTICATION"

        return prob, reasons, action
