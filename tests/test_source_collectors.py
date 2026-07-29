import os
import io
import json
import unittest
import uuid
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions
from src.agents.consumer.agent import ConsumerAgent
from src.agents.consumer.orchestrator import run_pipeline
import src.agents.consumer.parsers.pdf_parser as pdf_p

class TestSourceCollectors(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
        load_dotenv(dotenv_path)
        
        cls.supabase_url = os.environ.get("SUPABASE_URL")
        cls.supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        
        if not cls.supabase_url or not cls.supabase_key:
            raise unittest.SkipTest("Supabase credentials missing from .env")
            
        options = ClientOptions(schema="jarvis_insights_schemav1")
        cls.client: Client = create_client(cls.supabase_url, cls.supabase_key, options=options)
        cls.bucket_name = "jarvis-signals"
        
        # Download the real statements once for use in GPay and SBI tests
        try:
            cls.real_gpay_bytes = cls.client.storage.from_(cls.bucket_name).download("incoming/gpay_statement_20260401_20260630.pdf")
            cls.real_sbi_bytes = cls.client.storage.from_(cls.bucket_name).download("incoming/Email_Statement_080720262113519349631.pdf")
        except Exception as e:
            raise unittest.SkipTest(f"Failed to pre-download test PDFs: {e}")

    def setUp(self):
        self.cleanup_database()
        self.cleanup_storage()
        
        # Setup HDFC PDF parser mock
        self.original_parse_pdf = pdf_p.parse_pdf
        def mock_parse_pdf(file_bytes):
            try:
                # If bytes is our dummy 4 bytes, return HDFC mock document
                if file_bytes == b"HDFC":
                    mock_text = (
                        "HDFC BANK\n"
                        "STATEMENT OF ACCOUNT\n"
                        "02/04/2026 UPI-RADHA RADHA-HDFC3221-120940047278 120940047278 02/04/2026 1,536.00 22,148.82\n"
                        "04/04/2026 UPI-NAGARAJAN A-HDFC3221-609454912968 609454912968 04/04/2026 1,314.00 23,462.82CR\n"
                    )
                    return pdf_p.ParsedDocument(text=mock_text, pages=[mock_text])
            except Exception:
                pass
            return self.original_parse_pdf(file_bytes)
            
        pdf_p.parse_pdf = mock_parse_pdf
        
        # Override imported parse_pdf inside collector module namespaces
        import src.agents.consumer.collectors.bank_statement_collector as bsc
        import src.agents.consumer.collectors.gpay_collector as gpc
        bsc.parse_pdf = mock_parse_pdf
        gpc.parse_pdf = mock_parse_pdf

    def tearDown(self):
        pdf_p.parse_pdf = self.original_parse_pdf
        import src.agents.consumer.collectors.bank_statement_collector as bsc
        import src.agents.consumer.collectors.gpay_collector as gpc
        bsc.parse_pdf = self.original_parse_pdf
        gpc.parse_pdf = self.original_parse_pdf
        self.cleanup_database()
        self.cleanup_storage()

    def cleanup_database(self):
        try:
            self.client.table("pipeline_runs").delete().eq("version", "v2.0.0-phase1b-test").execute()
            # Clean up signals created by test runs based on file names
            test_filenames = ["test_wa.json", "test_sms.json", "test_gpay.pdf", "test_sbi.pdf", "test_hdfc.pdf"]
            for fname in test_filenames:
                self.client.table("mobile_signals").delete().filter("metadata->>source_file_name", "eq", fname).execute()
        except Exception as e:
            print(f"Database cleanup warning: {e}")

    def cleanup_storage(self):
        paths_to_delete = [
            "incoming/whatsapp/test_wa.json",
            "incoming/sms/test_sms.json",
            "incoming/gpay/test_gpay.pdf",
            "incoming/statements/test_sbi.pdf",
            "incoming/statements/test_hdfc.pdf",
            "archive/whatsapp/test_wa.json",
            "archive/sms/test_sms.json",
            "archive/gpay/test_gpay.pdf",
            "archive/statements/test_sbi.pdf",
            "archive/statements/test_hdfc.pdf",
            "failed/whatsapp/test_wa.json",
            "failed/sms/test_sms.json",
            "failed/gpay/test_gpay.pdf",
            "failed/statements/test_sbi.pdf",
            "failed/statements/test_hdfc.pdf",
        ]
        for path in paths_to_delete:
            try:
                self.client.storage.from_(self.bucket_name).remove([path])
            except Exception:
                pass

    def run_pipeline_with_test_version(self, trigger_type="MANUAL"):
        agent = ConsumerAgent(self.client)
        original_start_run = agent.start_run
        
        def mock_start_run(*args, **kwargs):
            run_id = original_start_run(*args, **kwargs)
            self.client.table("pipeline_runs").update({"version": "v2.0.0-phase1b-test"}).eq("run_id", str(run_id)).execute()
            return run_id
            
        agent.start_run = mock_start_run
        
        # Override discover_files to bypass legacy root files during tests
        original_discover_files = agent.discover_files
        def mock_discover_files(bucket_name, folder):
            if folder == "incoming":
                return []
            return original_discover_files(bucket_name, folder)
        agent.discover_files = mock_discover_files
        
        import src.agents.consumer.orchestrator as orch
        original_agent_class = orch.ConsumerAgent
        orch.ConsumerAgent = lambda client_obj: agent
        
        try:
            metrics = run_pipeline(self.client, trigger_type)
        finally:
            orch.ConsumerAgent = original_agent_class
            
        return metrics

    def test_1_whatsapp_ingestion(self):
        # 1. Upload WhatsApp JSON
        wa_data = {
            "chat_name": "Senthil RFC",
            "messages": [
                {
                    "sender": "Senthil RFC",
                    "message": "Reacted 👍 to \"📄 personal Agent.pdf (4 pages)\"",
                    "timestamp": 1782210550848,
                    "attachment_indicator": False,
                    "receiver": "test_phone_suite"
                }
            ]
        }
        self.client.storage.from_(self.bucket_name).upload(
            "incoming/whatsapp/test_wa.json",
            json.dumps(wa_data).encode("utf-8")
        )
        
        # 2. Run pipeline
        metrics = self.run_pipeline_with_test_version()
        
        # 3. Assertions
        self.assertEqual(metrics["status"], "SUCCESS")
        self.assertEqual(metrics["signals_created"], 1)
        
        # Assert database content
        res = self.client.table("mobile_signals").select("*").filter("metadata->>source_file_name", "eq", "test_wa.json").execute()
        self.assertEqual(len(res.data), 1)
        
        sig = res.data[0]
        self.assertEqual(sig["source"], "whatsapp")
        self.assertEqual(sig["sender"], "Senthil RFC")
        self.assertEqual(sig["message"], "Reacted 👍 to \"📄 personal Agent.pdf (4 pages)\"")
        self.assertEqual(sig["device_id"], "pradeep")
        self.assertEqual(sig["metadata"]["receiver"], "test_phone_suite")
        
        # Assert event time preserved: 1782210550848 milliseconds
        expected_time = datetime.fromtimestamp(1782210550848 / 1000.0, tz=timezone.utc).isoformat()
        self.assertEqual(datetime.fromisoformat(sig["mobile_timestamp"]), datetime.fromisoformat(expected_time))
        
        # Assert archived
        archive_files = [f["name"] for f in self.client.storage.from_(self.bucket_name).list("archive/whatsapp")]
        self.assertIn("test_wa.json", archive_files)

    def test_2_sms_ingestion(self):
        # 1. Upload SMS JSON
        sms_data = {
            "messages": [
                {
                    "sender": "VM-HDFCBK-S",
                    "message": "UPI LITE Top-up amounting to Rs.500.00 has been successful.",
                    "timestamp": 1782209436034,
                    "receiver": "test_phone_suite"
                }
            ]
        }
        self.client.storage.from_(self.bucket_name).upload(
            "incoming/sms/test_sms.json",
            json.dumps(sms_data).encode("utf-8")
        )
        
        # 2. Run pipeline
        metrics = self.run_pipeline_with_test_version()
        
        # 3. Assertions
        self.assertEqual(metrics["status"], "SUCCESS")
        self.assertEqual(metrics["signals_created"], 1)
        
        # Assert database content
        res = self.client.table("mobile_signals").select("*").filter("metadata->>source_file_name", "eq", "test_sms.json").execute()
        self.assertEqual(len(res.data), 1)
        
        sig = res.data[0]
        self.assertEqual(sig["source"], "sms")
        self.assertEqual(sig["sender"], "VM-HDFCBK-S")
        self.assertEqual(sig["device_id"], "pradeep")
        self.assertEqual(sig["metadata"]["receiver"], "test_phone_suite")
        
        expected_time = datetime.fromtimestamp(1782209436034 / 1000.0, tz=timezone.utc).isoformat()
        self.assertEqual(datetime.fromisoformat(sig["mobile_timestamp"]), datetime.fromisoformat(expected_time))
        
        # Assert archived
        archive_files = [f["name"] for f in self.client.storage.from_(self.bucket_name).list("archive/sms")]
        self.assertIn("test_sms.json", archive_files)

    def test_3_gpay_ingestion(self):
        # 1. Copy real GPay PDF as test_gpay.pdf
        self.client.storage.from_(self.bucket_name).upload(
            "incoming/gpay/test_gpay.pdf",
            self.real_gpay_bytes
        )
        
        # 2. Run pipeline
        metrics = self.run_pipeline_with_test_version()
        
        # 3. Assertions
        self.assertEqual(metrics["status"], "SUCCESS")
        self.assertEqual(metrics["files_processed"], 1)
        self.assertEqual(metrics["signals_created"], 277) # 278 parsed, 1 duplicate skipped
        
        # Assert database content
        res = self.client.table("mobile_signals").select("*").filter("metadata->>source_file_name", "eq", "test_gpay.pdf").execute()
        self.assertEqual(len(res.data), 277)
        
        # Test first record
        sig = res.data[0]
        self.assertEqual(sig["source"], "gpay")
        self.assertEqual(sig["sender"], "pprad") # DEBIT
        self.assertEqual(sig["device_id"], "pradeep")
        self.assertEqual(sig["metadata"]["receiver"], "Radha Radha")
        self.assertEqual(sig["message"], "Paid to Radha Radha")
        
        # Assert archived
        archive_files = [f["name"] for f in self.client.storage.from_(self.bucket_name).list("archive/gpay")]
        self.assertIn("test_gpay.pdf", archive_files)

    def test_4_bank_statement_ingestion(self):
        # 1. Copy real SBI statement as test_sbi.pdf
        self.client.storage.from_(self.bucket_name).upload(
            "incoming/statements/test_sbi.pdf",
            self.real_sbi_bytes
        )
        # 2. Upload dummy HDFC file to parse (which is intercepted by mock)
        self.client.storage.from_(self.bucket_name).upload(
            "incoming/statements/test_hdfc.pdf",
            b"HDFC"
        )
        
        # 3. Run pipeline
        metrics = self.run_pipeline_with_test_version()
        
        # 4. Assertions
        self.assertEqual(metrics["status"], "SUCCESS")
        self.assertEqual(metrics["files_processed"], 2) # Both HDFC and SBI statements
        self.assertEqual(metrics["signals_created"], 51) # 49 SBI + 2 HDFC transactions
        
        # Assert SBI database content
        sbi_res = self.client.table("mobile_signals").select("*").filter("metadata->>source_file_name", "eq", "test_sbi.pdf").execute()
        self.assertEqual(len(sbi_res.data), 49)
        
        # Assert HDFC database content
        hdfc_res = self.client.table("mobile_signals").select("*").filter("metadata->>source_file_name", "eq", "test_hdfc.pdf").execute()
        self.assertEqual(len(hdfc_res.data), 2)
        
        # Verify HDFC credit and debit
        debit_tx = next(tx for tx in hdfc_res.data if tx["message"].startswith("UPI-RADHA"))
        credit_tx = next(tx for tx in hdfc_res.data if tx["message"].startswith("UPI-NAGARAJAN"))
        
        self.assertEqual(debit_tx["metadata"]["transaction_type"], "DEBIT")
        self.assertEqual(debit_tx["metadata"]["amount"], 1536.0)
        self.assertEqual(credit_tx["metadata"]["transaction_type"], "CREDIT")
        self.assertEqual(credit_tx["metadata"]["amount"], 1314.0)

    def test_5_mixed_batch(self):
        # 1. Upload all formats simultaneously
        wa_data = {
            "chat_name": "Senthil RFC",
            "messages": [
                {
                    "sender": "Senthil RFC",
                    "message": "Reacted 👍",
                    "timestamp": 1782210550848,
                    "receiver": "test_phone_suite"
                }
            ]
        }
        sms_data = {
            "messages": [
                {
                    "sender": "VM-HDFCBK-S",
                    "message": "Ref No 617487742734",
                    "timestamp": 1782209436034,
                    "receiver": "test_phone_suite"
                }
            ]
        }
        self.client.storage.from_(self.bucket_name).upload("incoming/whatsapp/test_wa.json", json.dumps(wa_data).encode("utf-8"))
        self.client.storage.from_(self.bucket_name).upload("incoming/sms/test_sms.json", json.dumps(sms_data).encode("utf-8"))
        self.client.storage.from_(self.bucket_name).upload("incoming/gpay/test_gpay.pdf", self.real_gpay_bytes)
        self.client.storage.from_(self.bucket_name).upload("incoming/statements/test_sbi.pdf", self.real_sbi_bytes)
        self.client.storage.from_(self.bucket_name).upload("incoming/statements/test_hdfc.pdf", b"HDFC")
        
        # 2. Run pipeline
        metrics = self.run_pipeline_with_test_version()
        
        # 3. Assertions
        self.assertEqual(metrics["status"], "SUCCESS")
        self.assertEqual(metrics["files_processed"], 5)
        self.assertEqual(metrics["signals_created"], 330) # 1 WA + 1 SMS + 277 GPay + 49 SBI + 2 HDFC = 330 signals

if __name__ == "__main__":
    unittest.main()
