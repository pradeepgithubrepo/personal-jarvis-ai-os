# tests/test_financial_intelligence.py

import sys
import os
import json
import unittest
from datetime import datetime

# Add root folder to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import initialize_database, SessionLocal
from storage.models.signal import Signal
from storage.models.signal_classification import SignalClassification
from storage.models.financial_event import FinancialEvent
from storage.models.financial_transaction_classification import FinancialTransactionClassification
from storage.models.monthly_spending_summary import MonthlySpendingSummary
from storage.models.monthly_category_spend import MonthlyCategorySpend
from storage.models.monthly_category_trend import MonthlyCategoryTrend
from services.signal_processor import SignalProcessor
from services.financial_intelligence import FinancialIntelligenceService
from fastapi.testclient import TestClient
from app.main import app


class TestFinancialIntelligence(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database()
        cls.client = TestClient(app)

    def setUp(self):
        self.db = SessionLocal()
        # Clean up database
        self.db.query(FinancialEvent).delete()
        self.db.query(SignalClassification).delete()
        self.db.query(FinancialTransactionClassification).delete()
        self.db.query(MonthlySpendingSummary).delete()
        self.db.query(MonthlyCategorySpend).delete()
        self.db.query(MonthlyCategoryTrend).delete()
        self.db.query(Signal).filter(Signal.summary.like("%[TEST_FIN_INT]%")).delete(synchronize_session=False)
        self.db.commit()

    def tearDown(self):
        self.db.query(FinancialEvent).delete()
        self.db.query(SignalClassification).delete()
        self.db.query(FinancialTransactionClassification).delete()
        self.db.query(MonthlySpendingSummary).delete()
        self.db.query(MonthlyCategorySpend).delete()
        self.db.query(MonthlyCategoryTrend).delete()
        self.db.query(Signal).filter(Signal.summary.like("%[TEST_FIN_INT]%")).delete(synchronize_session=False)
        self.db.commit()
        self.db.close()

    def test_financial_intelligence_pipeline(self):
        # 1. Add mock signals
        # Internal transfer debit leg (June 1)
        sig_transfer_debit = Signal(
            source="sms",
            signal_type="financial_transaction",
            category="finance",
            importance="low",
            summary="[TEST_FIN_INT] Rs. 5000 debited from SBI account",
            raw_json=json.dumps({"amount": 5000, "transaction_type": "debit", "paid_to": "HDFC Account"}),
            created_at=datetime(2026, 6, 1, 10, 0, 0)
        )
        # Internal transfer credit leg (June 1)
        sig_transfer_credit = Signal(
            source="sms",
            signal_type="financial_transaction",
            category="finance",
            importance="low",
            summary="[TEST_FIN_INT] Rs. 5000 credited to HDFC account",
            raw_json=json.dumps({"amount": 5000, "transaction_type": "credit", "merchant": "SBI Account"}),
            created_at=datetime(2026, 6, 1, 10, 5, 0)
        )
        # Outflow expense 1 (June 5) - Grocery
        sig_exp1 = Signal(
            source="sms",
            signal_type="financial_transaction",
            category="finance",
            importance="low",
            summary="[TEST_FIN_INT] Rs 500 spent on Zepto",
            raw_json=json.dumps({"amount": 500, "transaction_type": "debit", "merchant": "Zepto"}),
            created_at=datetime(2026, 6, 5, 12, 0, 0)
        )
        # Outflow expense 2 (June 10) - Fish
        sig_exp2 = Signal(
            source="sms",
            signal_type="financial_transaction",
            category="finance",
            importance="low",
            summary="[TEST_FIN_INT] Rs 1200 spent on meen shop",
            raw_json=json.dumps({"amount": 1200, "transaction_type": "debit", "paid_to": "meen shop"}),
            created_at=datetime(2026, 6, 10, 15, 0, 0)
        )
        # Outflow expense 3 (July 2) - Grocery
        sig_exp3 = Signal(
            source="sms",
            signal_type="financial_transaction",
            category="finance",
            importance="low",
            summary="[TEST_FIN_INT] Rs 800 spent on Blinkit",
            raw_json=json.dumps({"amount": 800, "transaction_type": "debit", "merchant": "Blinkit"}),
            created_at=datetime(2026, 7, 2, 12, 0, 0)
        )

        self.db.add(sig_transfer_debit)
        self.db.add(sig_transfer_credit)
        self.db.add(sig_exp1)
        self.db.add(sig_exp2)
        self.db.add(sig_exp3)
        self.db.commit()

        # Classify signals to FINANCIAL category
        for sig in [sig_transfer_debit, sig_transfer_credit, sig_exp1, sig_exp2, sig_exp3]:
            classification = SignalClassification(
                signal_id=sig.id,
                category="FINANCIAL",
                confidence=1.0,
                processed_at=datetime.utcnow()
            )
            self.db.add(classification)
        self.db.commit()

        # Run extraction
        extracted_count = SignalProcessor.extract_financial_events()
        self.assertGreaterEqual(extracted_count, 5)

        # Run pipeline
        FinancialIntelligenceService.run_pipeline()

        # 2. Assert Internal Transfers are detected and classified as INTERNAL_TRANSFER
        debit_transfer_event = self.db.query(FinancialEvent).filter(
            FinancialEvent.title.like("%Rs. 5000 debited%")
        ).first()
        self.assertEqual(debit_transfer_event.category, "INTERNAL_TRANSFER")

        # 3. Assert summaries
        june_summary = self.db.query(MonthlySpendingSummary).filter(
            MonthlySpendingSummary.month_key == "2026-06"
        ).first()
        self.assertIsNotNone(june_summary)
        self.assertEqual(june_summary.total_spend, 1700.0)  # 500 (Zepto) + 1200 (meen)
        self.assertEqual(june_summary.transaction_count, 2)

        july_summary = self.db.query(MonthlySpendingSummary).filter(
            MonthlySpendingSummary.month_key == "2026-07"
        ).first()
        self.assertIsNotNone(july_summary)
        self.assertEqual(july_summary.total_spend, 800.0)  # 800 (Blinkit)
        self.assertEqual(july_summary.transaction_count, 1)

        # 4. Assert Category Spends
        june_spends = self.db.query(MonthlyCategorySpend).filter(
            MonthlyCategorySpend.month_key == "2026-06"
        ).all()
        self.assertEqual(len(june_spends), 2)
        grocery_spend = next(s for s in june_spends if s.category_name == "GROCERY")
        self.assertEqual(grocery_spend.amount, 500.0)

        # 5. Verify REST API endpoints
        # Summary Endpoint
        res_summary = self.client.get("/financial/summary")
        self.assertEqual(res_summary.status_code, 200)
        summary_data = res_summary.json()
        self.assertEqual(len(summary_data), 2)
        self.assertEqual(summary_data[0]["month_key"], "2026-07")

        # Categories Endpoint
        res_categories = self.client.get("/financial/categories?month_key=2026-06")
        self.assertEqual(res_categories.status_code, 200)
        category_data = res_categories.json()
        self.assertEqual(len(category_data), 2)

        # Trends Endpoint
        res_trends = self.client.get("/financial/trends?month_key=2026-07")
        self.assertEqual(res_trends.status_code, 200)
        trend_data = res_trends.json()
        self.assertEqual(len(trend_data), 1)

        # Drilldown Endpoint
        res_drilldown = self.client.get("/financial/drilldown?month_key=2026-06&category_name=GROCERY")
        self.assertEqual(res_drilldown.status_code, 200)
        drilldown_data = res_drilldown.json()
        self.assertEqual(len(drilldown_data), 1)
        self.assertEqual(drilldown_data[0]["paid_to"], "Zepto")
        self.assertEqual(drilldown_data[0]["amount"], 500.0)


if __name__ == "__main__":
    unittest.main()
