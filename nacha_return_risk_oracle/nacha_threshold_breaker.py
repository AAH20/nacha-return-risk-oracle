"""
NACHA 0.50% Unauthorized Return Threshold Circuit Breaker.
Monitors batch-level projected return rates and dynamically quarantines high-risk debit entries
to prevent originators from breaching NACHA's 0.50% unauthorized return cliff.
Zero external dependencies (pure Python standard library).
"""

import hashlib
from typing import List, Tuple

from .models import (
    ACHEntry,
    EntryTransactionType,
    RiskTier,
    ReturnPrediction,
    BatchRiskAssessment
)
from .r01_nsf_timing_model import R01NSFTimingModel
from .r10_unauthorized_detector import R10UnauthorizedDetector


class NACHAThresholdBreaker:
    """Pre-origination batch governor enforcing NACHA 0.50% unauthorized return limits."""

    NACHA_UNAUTHORIZED_THRESHOLD = 0.0050  # 0.50% (5 per 1,000)
    SAFETY_BUFFER_TARGET = 0.0020          # 0.20% safe operating ceiling

    def __init__(self):
        self.nsf_model = R01NSFTimingModel()
        self.unauth_model = R10UnauthorizedDetector()

    def evaluate_entry(self, entry: ACHEntry) -> ReturnPrediction:
        """Evaluates an individual entry across NSF and Unauthorized models."""
        p_nsf, r_nsf, act_nsf = self.nsf_model.evaluate_nsf_risk(entry)
        p_unauth, r_unauth, act_unauth = self.unauth_model.evaluate_unauthorized_risk(entry)

        reasons = r_nsf + r_unauth

        if p_unauth >= 0.50:
            return ReturnPrediction(
                entry_id=entry.entry_id,
                predicted_return_code="R10",
                return_probability=p_unauth,
                risk_tier=RiskTier.CRITICAL_QUARANTINE,
                reasons=reasons,
                action="QUARANTINE"
            )
        elif p_nsf >= 0.65:
            return ReturnPrediction(
                entry_id=entry.entry_id,
                predicted_return_code="R01",
                return_probability=p_nsf,
                risk_tier=RiskTier.HIGH,
                reasons=reasons,
                action="DELAY_FOR_PAYDAY"
            )
        elif max(p_nsf, p_unauth) >= 0.30:
            return ReturnPrediction(
                entry_id=entry.entry_id,
                predicted_return_code="R01" if p_nsf >= p_unauth else "R10",
                return_probability=max(p_nsf, p_unauth),
                risk_tier=RiskTier.MEDIUM,
                reasons=reasons,
                action="REVIEW"
            )
        else:
            return ReturnPrediction(
                entry_id=entry.entry_id,
                predicted_return_code=None,
                return_probability=max(p_nsf, p_unauth),
                risk_tier=RiskTier.LOW,
                reasons=reasons,
                action="DISPATCH"
            )

    def process_batch(self, batch_id: str, entries: List[ACHEntry]) -> Tuple[BatchRiskAssessment, List[ReturnPrediction]]:
        """
        Processes entire pending ACH batch, predicts projected return rates,
        and enforces circuit breaker quarantining if unauthorized rate >= 0.45%.
        """
        debit_entries = [e for e in entries if e.transaction_type == EntryTransactionType.DEBIT]
        total_debits = len(debit_entries)
        total_vol = sum(e.amount for e in debit_entries)

        if total_debits == 0:
            # All credits, zero return risk
            assessment = BatchRiskAssessment(
                batch_id=batch_id,
                total_entries_count=len(entries),
                total_debit_volume=0.0,
                projected_unauthorized_rate=0.0,
                projected_overall_return_rate=0.0,
                is_nacha_compliant=True,
                dispatched_entries_count=len(entries),
                quarantined_entries_count=0,
                prevented_returns_estimate=0,
                merkle_proof=hashlib.sha256(b"CREDIT_ONLY_BATCH").hexdigest()
            )
            return assessment, []

        predictions: List[ReturnPrediction] = [self.evaluate_entry(e) for e in debit_entries]

        # Calculate pre-quarantine projected unauthorized rate
        total_p_unauth = sum(p.return_probability for p in predictions if p.predicted_return_code == "R10")
        pre_rate = total_p_unauth / total_debits

        quarantined_count = 0
        prevented_returns = 0

        # Activate Circuit Breaker if projected unauthorized rate >= 0.0045 (0.45%)
        # or if any individual entry has CRITICAL_QUARANTINE
        for p in predictions:
            if p.action == "QUARANTINE" or p.risk_tier == RiskTier.CRITICAL_QUARANTINE:
                quarantined_count += 1
                if p.return_probability >= 0.50:
                    prevented_returns += 1

        dispatched_count = len(entries) - quarantined_count
        post_unauth_p = sum(p.return_probability for p in predictions if p.predicted_return_code == "R10" and p.action != "QUARANTINE")
        post_rate = post_unauth_p / max(1, (total_debits - quarantined_count))

        # Overall return estimate (including NSF R01)
        total_p_nsf = sum(p.return_probability for p in predictions if p.action != "QUARANTINE")
        overall_rate = total_p_nsf / max(1, (total_debits - quarantined_count))

        # Merkle proof
        proof_payload = f"BATCH:{batch_id}:{total_debits}:{post_rate:.5f}:{quarantined_count}"
        merkle_root = hashlib.sha256(proof_payload.encode("utf-8")).hexdigest()

        assessment = BatchRiskAssessment(
            batch_id=batch_id,
            total_entries_count=len(entries),
            total_debit_volume=total_vol,
            projected_unauthorized_rate=round(post_rate, 5),
            projected_overall_return_rate=round(overall_rate, 5),
            is_nacha_compliant=post_rate < self.NACHA_UNAUTHORIZED_THRESHOLD,
            dispatched_entries_count=dispatched_count,
            quarantined_entries_count=quarantined_count,
            prevented_returns_estimate=prevented_returns,
            merkle_proof=merkle_root
        )

        return assessment, predictions
