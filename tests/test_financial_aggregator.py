# tests/test_financial_aggregator.py

import sys
import os
import unittest
import uuid
from datetime import datetime

# Add root folder to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from unittest.mock import patch
from services.financial_aggregator import FinancialAggregator


class TestFinancialAggregator(unittest.TestCase):

    @patch("services.supabase_repo.SupabaseRepo.reclassify_financial_event")
    @patch("services.supabase_repo.SupabaseRepo.save_transaction_classification")
    def test_internal_transfer_detection(self, mock_save_class, mock_reclassify):
        # 1. Create mock financial events
        mock_events = [
            {
                "financial_event_id": "d114b579-6f0a-54cf-bc67-09bb7a454d4b",
                "amount": 5000.0,
                "currency": "INR",
                "category": "finance",
                "event_timestamp": "2026-06-01T10:00:00",
                "source_signal_id": "signal-debit-transfer"
            },
            {
                "financial_event_id": "c114b579-6f0a-54cf-bc67-09bb7a454d4b",
                "amount": 5000.0,
                "currency": "INR",
                "category": "finance",
                "event_timestamp": "2026-06-01T10:05:00",
                "source_signal_id": "signal-credit-transfer"
            },
            {
                "financial_event_id": "e114b579-6f0a-54cf-bc67-09bb7a454d4b",
                "amount": 500.0,
                "currency": "INR",
                "category": "finance",
                "event_timestamp": "2026-06-05T12:00:00",
                "source_signal_id": "signal-grocery"
            }
        ]

        # 2. Mock signal messages mapping
        mock_messages = {
            "signal-debit-transfer": "SBI Account XX123: Rs 5000.00 debited to HDFC Bank",
            "signal-credit-transfer": "HDFC Account XX987: Rs 5000.00 credited from SBI",
            "signal-grocery": "Rs 500 spent on Zepto"
        }

        # Run internal transfer detection
        transfer_ids = FinancialAggregator.detect_internal_transfers(mock_events, mock_messages)
        
        # Verify that both legs are identified as internal transfers
        self.assertIn("d114b579-6f0a-54cf-bc67-09bb7a454d4b", transfer_ids)
        self.assertIn("c114b579-6f0a-54cf-bc67-09bb7a454d4b", transfer_ids)
        self.assertNotIn("e114b579-6f0a-54cf-bc67-09bb7a454d4b", transfer_ids)


if __name__ == "__main__":
    unittest.main()
