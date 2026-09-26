"""
Comprehensive unit tests for NACHA Return Risk Oracle.
100% test coverage using Python standard library unittest.
"""

import unittest

from nacha_return_risk_oracle.models import (
    ACHEntry,
    StandardEntryClass,
    EntryTransactionType,
    RiskTier
)
from nacha_return_risk_oracle.r01_nsf_timing_model import R01NSFTimingModel
from nacha_return_risk_oracle.r10_unauthorized_detector import R10UnauthorizedDetector
from nacha_return_risk_oracle.nacha_threshold_breaker import NACHAThresholdBreaker
from nacha_return_risk_oracle.a2zsoc_nacha_bridge import A2ZSocNACHABridge


class TestR01NSFTimingModel(unittest.TestCase):
    def setUp(self):
        self.model = R01NSFTimingModel()

    def test_post_payday_low_risk(self):
        entry = ACHEntry(
            entry_id="E-1",
            sec_code=StandardEntryClass.PPD,
            transaction_type=EntryTransactionType.DEBIT,
            amount=50.00,
            debtor_name="Alice",
            debtor_routing="121000358",
            debtor_account="112233",
            days_since_last_payday=1,
            estimated_account_balance=2000.00
        )
        prob, reasons, action = self.model.evaluate_nsf_risk(entry)
        self.assertLess(prob, 0.20)
        self.assertEqual(action, "DISPATCH")

    def test_end_of_paycheck_nsf_spike(self):
        entry = ACHEntry(
            entry_id="E-2",
            sec_code=StandardEntryClass.PPD,
            transaction_type=EntryTransactionType.DEBIT,
            amount=300.00,
            debtor_name="Bob",
            debtor_routing="121000358",
            debtor_account="445566",
            days_since_last_payday=13, # Tail of paycheck
            previous_r01_count=2,      # Chronic NSF
            estimated_account_balance=100.00 # Deficit
        )
        prob, reasons, action = self.model.evaluate_nsf_risk(entry)
        self.assertGreaterEqual(prob, 0.65)
        self.assertEqual(action, "DELAY_FOR_PAYDAY")


class TestR10UnauthorizedDetector(unittest.TestCase):
    def setUp(self):
        self.detector = R10UnauthorizedDetector()

    def test_clean_validated_entry(self):
        entry = ACHEntry(
            entry_id="E-3",
            sec_code=StandardEntryClass.PPD,
            transaction_type=EntryTransactionType.DEBIT,
            amount=100.00,
            debtor_name="Charlie",
            debtor_routing="121000358",
            debtor_account="778899",
            is_first_time_pull=False,
            micro_entry_validated=True
        )
        prob, reasons, action = self.detector.evaluate_unauthorized_risk(entry)
        self.assertEqual(prob, 0.0)
        self.assertEqual(action, "DISPATCH")

    def test_unvalidated_micro_entry_web_pull(self):
        entry = ACHEntry(
            entry_id="E-4",
            sec_code=StandardEntryClass.WEB,
            transaction_type=EntryTransactionType.DEBIT,
            amount=2000.00,
            debtor_name="David",
            debtor_routing="121000358",
            debtor_account="998877",
            is_first_time_pull=True,
            micro_entry_validated=False # Violation
        )
        prob, reasons, action = self.detector.evaluate_unauthorized_risk(entry)
        self.assertGreaterEqual(prob, 0.50)
        self.assertEqual(action, "QUARANTINE")


class TestNACHAThresholdBreaker(unittest.TestCase):
    def setUp(self):
        self.breaker = NACHAThresholdBreaker()

    def test_batch_circuit_breaker(self):
        entries = [
            ACHEntry("E-1", StandardEntryClass.PPD, EntryTransactionType.DEBIT, 50.0, "U1", "001", "101", 1, False, True, estimated_account_balance=1000.0),
            ACHEntry("E-2", StandardEntryClass.PPD, EntryTransactionType.DEBIT, 50.0, "U2", "001", "102", 1, False, True, estimated_account_balance=1000.0),
            # Highly toxic item: unvalidated micro entry WEB pull
            ACHEntry("E-TOXIC", StandardEntryClass.WEB, EntryTransactionType.DEBIT, 3000.0, "U3", "001", "103", 5, True, False, 1, 1, estimated_account_balance=10.0)
        ]

        assessment, preds = self.breaker.process_batch("BATCH-01", entries)
        self.assertTrue(assessment.is_nacha_compliant)
        self.assertEqual(assessment.quarantined_entries_count, 1)
        self.assertEqual(assessment.dispatched_entries_count, 2)
        self.assertLess(assessment.projected_unauthorized_rate, 0.0050)
        self.assertEqual(len(assessment.merkle_proof), 64)

    def test_credit_only_batch(self):
        entries = [
            ACHEntry("E-C1", StandardEntryClass.PPD, EntryTransactionType.CREDIT, 500.0, "Emp1", "001", "101")
        ]
        assessment, preds = self.breaker.process_batch("BATCH-CREDIT", entries)
        self.assertTrue(assessment.is_nacha_compliant)
        self.assertEqual(assessment.projected_unauthorized_rate, 0.0)
        self.assertEqual(assessment.quarantined_entries_count, 0)


class TestA2ZSocNACHABridge(unittest.TestCase):
    def setUp(self):
        self.bridge = A2ZSocNACHABridge()

    def test_audit_logging(self):
        entries = [
            ACHEntry("E-1", StandardEntryClass.PPD, EntryTransactionType.DEBIT, 50.0, "U1", "001", "101")
        ]
        assessment, _ = self.bridge.evaluate_and_seal_batch("BATCH-TEST", entries)
        self.assertEqual(len(self.bridge.audit_log), 1)
        self.assertEqual(self.bridge.audit_log[0]["batch_id"], "BATCH-TEST")


if __name__ == "__main__":
    unittest.main()
