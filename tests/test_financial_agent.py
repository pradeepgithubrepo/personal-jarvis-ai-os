"""
tests/test_financial_agent.py

Unit tests for Financial Agent V1 pure functions and stage logic.
No Supabase connection required — all I/O is mocked.
"""
import hashlib
import unittest
from unittest.mock import MagicMock, patch, call

from src.agents.financial.financial_agent import (
    FinancialAgent,
    _canonicalize,
    _build_canonical_hash,
    _score_confidence,
    _infer_source,
    _infer_account,
    _infer_direction,
    _normalize_direction,
    _classify_transaction_type,
    _parse_date,
)


# ─────────────────────────────────────────────────────────────────────────────
# Pure function tests
# ─────────────────────────────────────────────────────────────────────────────

class TestCanonicalize(unittest.TestCase):

    def test_strips_city_name(self):
        self.assertEqual(_canonicalize("SWIGGY BANGALORE"), "SWIGGY")

    def test_strips_ltd(self):
        self.assertEqual(_canonicalize("SWIGGY LTD"), "SWIGGY")

    def test_strips_instamart(self):
        self.assertEqual(_canonicalize("SWIGGY INSTAMART"), "SWIGGY")

    def test_strips_asterisk_variant(self):
        self.assertEqual(_canonicalize("SWIGGY*ONLINE"), "SWIGGY")

    def test_amazon_variants(self):
        self.assertEqual(_canonicalize("AMAZON PAY INDIA"), "AMAZON")

    def test_preserves_core_name(self):
        self.assertEqual(_canonicalize("ZOMATO"), "ZOMATO")

    def test_multi_strip(self):
        self.assertEqual(_canonicalize("NETFLIX INDIA TECH SERVICES"), "NETFLIX")


class TestBuildCanonicalHash(unittest.TestCase):

    def test_tier1_uses_reference_number(self):
        ref = "UPI123456789"
        expected = hashlib.sha256(ref.encode("utf-8")).hexdigest()
        result = _build_canonical_hash(1000.00, "2025-01-15", "DEBIT", "HDFC", ref)
        self.assertEqual(result, expected)

    def test_tier2_fallback_deterministic(self):
        h1 = _build_canonical_hash(1500.00, "2025-03-20", "DEBIT", "SBI", None)
        h2 = _build_canonical_hash(1500.00, "2025-03-20", "DEBIT", "SBI", None)
        self.assertEqual(h1, h2)

    def test_tier2_different_amounts_differ(self):
        h1 = _build_canonical_hash(1000.00, "2025-03-20", "DEBIT", "HDFC", None)
        h2 = _build_canonical_hash(2000.00, "2025-03-20", "DEBIT", "HDFC", None)
        self.assertNotEqual(h1, h2)

    def test_tier2_date_truncated_to_day(self):
        # Same day, different time → same hash (SMS vs EOD statement)
        h1 = _build_canonical_hash(500.00, "2025-06-01", "DEBIT", "HDFC", None)
        h2 = _build_canonical_hash(500.00, "2025-06-01T23:59:00", "DEBIT", "HDFC", None)
        self.assertEqual(h1, h2)

    def test_tier1_empty_ref_falls_to_tier2(self):
        h = _build_canonical_hash(100.00, "2025-01-01", "CREDIT", "HDFC", "  ")
        self.assertIsInstance(h, str)
        self.assertEqual(len(h), 64)


class TestScoreConfidence(unittest.TestCase):

    def test_bank_statement_always_100(self):
        self.assertEqual(_score_confidence("BANK_STATEMENT_PDF", None), 100)
        self.assertEqual(_score_confidence("BANK_STATEMENT_PDF", "REF123"), 100)

    def test_gpay_always_90(self):
        self.assertEqual(_score_confidence("GPAY_PDF", None), 90)

    def test_sms_with_ref_is_75(self):
        self.assertEqual(_score_confidence("SMS", "UPI123456"), 75)

    def test_sms_without_ref_is_60(self):
        self.assertEqual(_score_confidence("SMS", None), 60)
        self.assertEqual(_score_confidence("SMS", ""), 60)


class TestInferSource(unittest.TestCase):

    def test_gpay_in_raw_message(self):
        self.assertEqual(_infer_source({}, "google pay payment Rs.500"), "GPAY_PDF")

    def test_bank_statement_from_contract(self):
        self.assertEqual(_infer_source({"source": "BANK_STATEMENT"}, ""), "BANK_STATEMENT_PDF")

    def test_default_is_sms(self):
        self.assertEqual(_infer_source({}, "A/c XX1234 debited Rs.100"), "SMS")


class TestInferAccount(unittest.TestCase):

    def test_hdfc(self):
        self.assertEqual(_infer_account("HDFC Bank A/c debited Rs.500"), "HDFC")

    def test_sbi(self):
        self.assertEqual(_infer_account("Your SBI account credited Rs.1000"), "SBI")

    def test_state_bank(self):
        self.assertEqual(_infer_account("STATE BANK OF INDIA alert"), "SBI")

    def test_unknown_returns_none(self):
        self.assertIsNone(_infer_account("random message"))


class TestNormalizeDirection(unittest.TestCase):

    def test_debit_string(self):
        self.assertEqual(_normalize_direction("DEBIT", ""), "DEBIT")

    def test_dr_abbreviation(self):
        self.assertEqual(_normalize_direction("DR", ""), "DEBIT")

    def test_credit_string(self):
        self.assertEqual(_normalize_direction("CREDIT", ""), "CREDIT")

    def test_cr_abbreviation(self):
        self.assertEqual(_normalize_direction("CR", ""), "CREDIT")

    def test_fallback_to_infer(self):
        self.assertEqual(_normalize_direction("", "PAYMENT"), "DEBIT")
        self.assertEqual(_normalize_direction("", "RECEIVED"), "CREDIT")


class TestClassifyTransactionType(unittest.TestCase):

    def test_self_transfer_always_transfer(self):
        result = _classify_transaction_type("DEBIT", True, "transfer to SBI", None, "DEBIT")
        self.assertEqual(result, "TRANSFER")

    def test_refund_detected(self):
        result = _classify_transaction_type("CREDIT", False, "Amazon refund processed Rs.500", None, "CREDIT")
        self.assertEqual(result, "REFUND")

    def test_reversal_detected(self):
        result = _classify_transaction_type("CREDIT", False, "UPI reversal credited", None, "CREDIT")
        self.assertEqual(result, "REVERSAL")

    def test_fee_detected(self):
        result = _classify_transaction_type("DEBIT", False, "Annual fee deducted", None, "DEBIT")
        self.assertEqual(result, "FEE")

    def test_interest_detected(self):
        result = _classify_transaction_type("CREDIT", False, "FD interest credited", None, "CREDIT")
        self.assertEqual(result, "INTEREST")

    def test_tax_detected(self):
        result = _classify_transaction_type("DEBIT", False, "TDS deducted on interest", None, "DEBIT")
        self.assertEqual(result, "TAX")

    def test_debit_default_expense(self):
        result = _classify_transaction_type("DEBIT", False, "Paid Rs.300 to Swiggy", None, "DEBIT")
        self.assertEqual(result, "EXPENSE")

    def test_credit_default_income(self):
        result = _classify_transaction_type("CREDIT", False, "Salary credited Rs.50000", None, "CREDIT")
        self.assertEqual(result, "INCOME")


class TestParseDate(unittest.TestCase):

    def test_iso_date(self):
        self.assertEqual(_parse_date("2025-06-15"), "2025-06-15")

    def test_iso_timestamp_truncated(self):
        self.assertEqual(_parse_date("2025-06-15T10:30:00+05:30"), "2025-06-15")

    def test_dd_mm_yyyy_slash(self):
        self.assertEqual(_parse_date("15/06/2025"), "2025-06-15")

    def test_dd_mm_yyyy_dash(self):
        self.assertEqual(_parse_date("15-06-2025"), "2025-06-15")

    def test_none_returns_today(self):
        result = _parse_date(None)
        self.assertRegex(result, r"^\d{4}-\d{2}-\d{2}$")


# ─────────────────────────────────────────────────────────────────────────────
# Stage tests (mocked Supabase)
# ─────────────────────────────────────────────────────────────────────────────

class TestSpamFilter(unittest.TestCase):

    def setUp(self):
        self.agent = FinancialAgent()

    def test_unknown_with_no_real_signal_is_spam(self):
        self.assertTrue(self.agent._is_spam("UNKNOWN", "Congratulations! Pre-approved loan offer"))

    def test_unknown_with_real_signal_not_spam(self):
        self.assertFalse(self.agent._is_spam("UNKNOWN", "Your a/c XX1234 debited Rs.500 via UPI ref 123"))

    def test_known_spam_keyword_blocked(self):
        self.assertTrue(self.agent._is_spam("DEBIT", "Lifetime free credit card! Apply now"))

    def test_valid_debit_passes(self):
        self.assertFalse(self.agent._is_spam("DEBIT", "HDFC Bank: A/c XX4321 debited Rs.2500"))

    def test_valid_credit_passes(self):
        self.assertFalse(self.agent._is_spam("CREDIT", "Rs.50000 credited to your account. UPI ref 9876"))


class TestTransferDetection(unittest.TestCase):

    def setUp(self):
        self.agent = FinancialAgent()

    def test_keyword_rule_1(self):
        mock_client = MagicMock()
        result = self.agent._detect_transfer("HDFC to SBI transfer done", mock_client, 5000, "DEBIT", "2025-01-01")
        self.assertTrue(result)

    def test_owner_name_rule_2(self):
        mock_client = MagicMock()
        result = self.agent._detect_transfer("Transfer to Pradeep savings account", mock_client, 1000, "DEBIT", "2025-01-01")
        self.assertTrue(result)

    def test_no_transfer_signal(self):
        mock_client = MagicMock()
        # Mock no double-entry match
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        result = self.agent._detect_transfer("Paid Rs.500 to Swiggy for food", mock_client, 500, "DEBIT", "2025-01-01")
        self.assertFalse(result)


class TestMerchantNormalize(unittest.TestCase):

    def setUp(self):
        self.agent = FinancialAgent()

    def _make_client(self, canonical_match=None, contains_rules=None):
        """Build a mock client that returns specified rule lookups."""
        client = MagicMock()
        # Chain: .table().select().eq().limit().execute()
        exact_res = MagicMock()
        exact_res.data = [canonical_match] if canonical_match else []
        contains_res = MagicMock()
        contains_res.data = contains_rules or []

        # exact query
        client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = exact_res
        # contains query
        client.table.return_value.select.return_value.eq.return_value.execute.return_value = contains_res
        return client

    def test_canonical_match_found(self):
        rule = {"normalized_merchant": "Swiggy", "category_override": "Food"}
        client = self._make_client(canonical_match=rule)
        merchant, category = self.agent._normalize_merchant(client, "SWIGGY BANGALORE", "")
        self.assertEqual(merchant, "Swiggy")
        self.assertEqual(category, "Food")

    def test_empty_counterparty_returns_none(self):
        client = MagicMock()
        merchant, category = self.agent._normalize_merchant(client, "", "")
        self.assertIsNone(merchant)
        self.assertIsNone(category)


if __name__ == "__main__":
    unittest.main(verbosity=2)
