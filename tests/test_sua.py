import os
import unittest
import uuid
import random
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions

from src.agents.sua.agent import SignalUnderstandingAgent
from src.agents.sua.orchestrator import run_pipeline

class TestSignalUnderstandingAgent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Load env variables
        dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
        load_dotenv(dotenv_path)
        
        cls.supabase_url = os.environ.get("SUPABASE_URL")
        cls.supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        
        if not cls.supabase_url or not cls.supabase_key:
            raise unittest.SkipTest("Supabase credentials missing from .env")
            
        options = ClientOptions(schema="jarvis_insights_schemav1")
        cls.client: Client = create_client(cls.supabase_url, cls.supabase_key, options=options)
        
        # Check if qualified_signals table exists in Supabase schema cache
        try:
            cls.client.table("qualified_signals").select("id").limit(1).execute()
            cls.tables_exist = True
        except Exception:
            cls.tables_exist = False

    def setUp(self):
        self.cleanup_database()
        
    def tearDown(self):
        self.cleanup_database()
        
    def cleanup_database(self):
        try:
            # Delete any test pipeline runs
            self.client.table("pipeline_runs").delete().eq("version", "v2.0.0-phase2a-test").execute()
            if self.tables_exist:
                self.client.table("qualified_signals").delete().eq("source", "sua_test_suite").execute()
            # Clean up mobile signals
            self.client.table("mobile_signals").delete().eq("source", "sua_test_suite").execute()
        except Exception as e:
            pass

    def test_agent_contract_parsing(self):
        # Initialize agent
        agent = SignalUnderstandingAgent()
        
        # Test financial signal
        sig = {
            "message": "Alert: Your account has been debited with INR 5,000.00 by UPI-AMAZON-TXN99.",
            "sender": "HDFC-BANK",
            "source": "sms",
            "timestamp": "2026-07-09T11:00:00Z"
        }
        res = agent.understand_signal(sig)
        
        self.assertEqual(res["signal_type"], "FINANCIAL")
        self.assertGreaterEqual(res["importance"], 0.7)
        self.assertIn("contract_json", res)
        
        contract = res["contract_json"]
        self.assertIsNotNone(contract)
        self.assertIn("financial_candidate", contract)
        self.assertTrue(contract["financial_candidate"])
        
    def test_agent_fallback_heuristics(self):
        # Test fallback with invalid Ollama URL
        agent = SignalUnderstandingAgent(model_name="qwen2.5:1.5b")
        agent.llm_client.ollama_url = "http://127.0.0.1:9999"  # invalid port to force fallback
        
        sig = {
            "message": "Alert: Your account xx3221 debited Rs. 500.00.",
            "sender": "HDFC",
            "source": "sms",
            "timestamp": "2026-07-09T11:00:00Z"
        }
        res = agent.understand_signal(sig)
        self.assertEqual(res["signal_type"], "FINANCIAL")
        self.assertEqual(res["processing_path"], "fallback")
        self.assertEqual(res["contract_json"]["amount"], 500.0)

    def test_orchestrator_delta_processing(self):
        if not self.tables_exist:
            raise unittest.SkipTest("qualified_signals table does not exist in Supabase (SQL DDL needs to be run)")
            
        # 1. Insert a qualified signal manually
        raw_sig_id = random.randint(10000000, 99999999) # BIGINT ID
        
        # We need a raw mobile signal first because qualified_signals has FK constraint on mobile_signals
        mobile_row = {
            "id": raw_sig_id,
            "device_id": "test_phone_suite",
            "source": "sua_test_suite",
            "sender": "TESTER",
            "message": "Please call Shobana tonight",
            "mobile_timestamp": datetime.now(timezone.utc).isoformat(),
            "message_hash": str(uuid.uuid4()),
            "processed": False
        }
        self.client.table("mobile_signals").insert(mobile_row).execute()
        
        qualified_row = {
            "id": str(uuid.uuid4()),
            "signal_id": raw_sig_id,
            "source": "sua_test_suite",
            "sender": "TESTER",
            "message": "Please call Shobana tonight",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "qualification_score": 95.0,
            "qualification_status": "QUALIFIED"
        }
        self.client.table("qualified_signals").insert(qualified_row).execute()
        
        # 2. Run pipeline
        metrics = run_pipeline(self.client, trigger_type="TEST", model_name="qwen2.5:1.5b")
        
        self.assertEqual(metrics["status"], "SUCCESS")
        self.assertGreaterEqual(metrics["signals_processed"], 1)
        self.assertGreaterEqual(metrics["signals_understood"], 1)
        
        # 3. Clean up the inserted raw signal
        self.client.table("mobile_signals").delete().eq("id", raw_sig_id).execute()
        
if __name__ == "__main__":
    unittest.main()
