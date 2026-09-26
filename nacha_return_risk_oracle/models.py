"""
Data models for NACHA Return Risk Oracle.
Covers ACH SEC codes, Pre-Origination Return (R01/R10) predictions,
and NACHA Risk Management Framework 0.5% circuit-breaker metrics.
"""

from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Dict, List, Optional


class StandardEntryClass(str, Enum):
    PPD = "PPD"  # Prearranged Payment and Deposit (Consumer Recurring)
    WEB = "WEB"  # Internet-Initiated Debit (Highest Risk)
    CCD = "CCD"  # Corporate Credit or Debit (B2B)
    TEL = "TEL"  # Telephone-Initiated


class EntryTransactionType(str, Enum):
    DEBIT = "DEBIT"    # Pulling funds from customer account (Subject to returns)
    CREDIT = "CREDIT"  # Pushing funds to customer account


class RiskTier(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL_QUARANTINE = "CRITICAL_QUARANTINE"


@dataclass
class ACHEntry:
    """Individual ACH debit or credit entry in a pending batch."""
    entry_id: str
    sec_code: StandardEntryClass
    transaction_type: EntryTransactionType
    amount: float
    debtor_name: str
    debtor_routing: str
    debtor_account: str
    days_since_last_payday: int = 1      # 0 = Payday today, 1-14 = post-payday
    is_first_time_pull: bool = False     # New debtor pull
    micro_entry_validated: bool = True   # NACHA Micro-Entry rule compliance
    previous_r01_count: int = 0          # Prior NSF returns on file
    previous_r10_count: int = 0          # Prior unauthorized complaints
    estimated_account_balance: float = 500.0


@dataclass
class ReturnPrediction:
    """Predictive evaluation of ACH return risk prior to transmission."""
    entry_id: str
    predicted_return_code: Optional[str]  # None, "R01", "R10", "R03"
    return_probability: float            # 0.0 to 1.0
    risk_tier: RiskTier
    reasons: List[str] = field(default_factory=list)
    action: str = "DISPATCH"             # DISPATCH, DELAY_FOR_PAYDAY, QUARANTINE


@dataclass
class BatchRiskAssessment:
    """Batch-level aggregate evaluation under NACHA Risk Management rules."""
    batch_id: str
    total_entries_count: int
    total_debit_volume: float
    projected_unauthorized_rate: float   # NACHA Cap: 0.50% (R05, R07, R10, R29)
    projected_overall_return_rate: float # NACHA Cap: 7.50%
    is_nacha_compliant: bool
    dispatched_entries_count: int
    quarantined_entries_count: int
    prevented_returns_estimate: int
    merkle_proof: str
    timestamp: float = field(default_factory=time.time)
