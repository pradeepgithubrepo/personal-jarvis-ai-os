import os
import sys
import json
import unittest
import uuid
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions
from src.agents.consumer.agent import ConsumerAgent
from src.agents.consumer.orchestrator import run_pipeline

class TestConsumerAgent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Load env
        dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
        load_dotenv(dotenv_path)
        
        cls.supabase_url = os.environ.get("SUPABASE_URL")
        cls.supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        
        if not cls.supabase_url or not cls.supabase_key:
            raise unittest.SkipTest("Supabase credentials missing from .env")
            
        options = ClientOptions(schema="jarvis_insights_schemav1")
        cls.client: Client = create_client(cls.supabase_url, cls.supabase_key, options=options)
        cls.bucket_name = "jarvis-signals"

    def setUp(self):
        # Clean up database records and storage files before each test to ensure isolation
        self.cleanup_database()
        self.cleanup_storage()

    def tearDown(self):
        # Clean up database records and storage files after each test
        self.cleanup_database()
        self.cleanup_storage()

    def cleanup_database(self):
        try:
            # Cascade delete all runs with version = 'v2.0.0-phase1a-test'
            # Delete events and processed_files automatically via FK cascade
            self.client.table("pipeline_runs").delete().eq("version", "v2.0.0-phase1a-test").execute()
            # Delete test mobile signals
            self.client.table("mobile_signals").delete().eq("device_id", "test_phone_suite").execute()
        except Exception as e:
            print(f"Database cleanup warning: {e}")

    def cleanup_storage(self):
        # Files that may be uploaded, archived or failed during tests
        test_files = [
            "incoming/test_single.json",
            "incoming/test_dup.json",
            "incoming/test_broken.json",
            "incoming/test_valid.json",
            "incoming/test_rerun.json",
            "archive/test_single.json",
            "archive/test_valid.json",
            "archive/test_rerun.json",
            "failed/test_broken.json"
        ]
        for path in test_files:
            try:
                self.client.storage.from_(self.bucket_name).remove([path])
            except Exception:
                pass

    def run_pipeline_with_test_version(self, trigger_type="MANUAL"):
        # Helper to run pipeline and override agent's version to 'v2.0.0-phase1a-test'
        # so we can track and cascade delete test runs easily.
        agent = ConsumerAgent(self.client)
        started_at = datetime.now(timezone.utc)
        
        # Override start_run to tag version as 'v2.0.0-phase1a-test'
        original_start_run = agent.start_run
        def mock_start_run(*args, **kwargs):
            run_id = original_start_run(*args, **kwargs)
            self.client.table("pipeline_runs").update({"version": "v2.0.0-phase1a-test"}).eq("run_id", str(run_id)).execute()
            return run_id
            
        agent.start_run = mock_start_run

        # Override discover_files to only return test files starting with 'test_'
        original_discover_files = agent.discover_files
        def mock_discover_files(bucket_name, folder):
            files = original_discover_files(bucket_name, folder)
            return [f for f in files if f.startswith("test_")]
            
        agent.discover_files = mock_discover_files
        
        # Override orchestrator's agent instantiation
        import src.agents.consumer.orchestrator as orch
        original_agent_class = orch.ConsumerAgent
        orch.ConsumerAgent = lambda client_obj: agent
        
        try:
            metrics = run_pipeline(self.client, trigger_type)
        finally:
            orch.ConsumerAgent = original_agent_class
            
        return metrics

    def test_1_single_file_success(self):
        # 1. Prepare valid file
        signal_data = {
            "generatedAt": 1782952265463,
            "signals": [
                {
                    "id": 1001,
                    "deviceId": "test_phone_suite",
                    "source": "test_source_suite",
                    "sender": "Sender A",
                    "message": "Hello Test 1",
                    "timestamp": 1782922228047
                },
                {
                    "id": 1002,
                    "deviceId": "test_phone_suite",
                    "source": "test_source_suite",
                    "sender": "Sender B",
                    "message": "Hello Test 2",
                    "timestamp": 1782922228052
                }
            ]
        }
        self.client.storage.from_(self.bucket_name).upload(
            "incoming/test_single.json",
            json.dumps(signal_data).encode("utf-8")
        )
        
        # 2. Run pipeline
        metrics = self.run_pipeline_with_test_version()
        
        # 3. Assertions
        self.assertEqual(metrics["status"], "SUCCESS")
        self.assertEqual(metrics["files_found"], 1)
        self.assertEqual(metrics["files_processed"], 1)
        self.assertEqual(metrics["files_skipped"], 0)
        self.assertEqual(metrics["files_failed"], 0)
        self.assertEqual(metrics["signals_created"], 2)

        # Assert DB writes
        res_signals = self.client.table("mobile_signals").select("*").eq("device_id", "test_phone_suite").execute()
        self.assertEqual(len(res_signals.data), 2)
        
        # Assert file is archived
        incoming_files = [f["name"] for f in self.client.storage.from_(self.bucket_name).list("incoming")]
        archive_files = [f["name"] for f in self.client.storage.from_(self.bucket_name).list("archive")]
        self.assertNotIn("test_single.json", incoming_files)
        self.assertIn("test_single.json", archive_files)

    def test_2_duplicate_file_skip(self):
        # 1. Run once to process file
        signal_data = {
            "generatedAt": 1782952265463,
            "signals": [
                {
                    "id": 1001,
                    "deviceId": "test_phone_suite",
                    "source": "test_source_suite",
                    "sender": "Sender A",
                    "message": "Hello Test 1",
                    "timestamp": 1782922228047
                }
            ]
        }
        file_bytes = json.dumps(signal_data).encode("utf-8")
        self.client.storage.from_(self.bucket_name).upload("incoming/test_single.json", file_bytes)
        
        # Process first run
        self.run_pipeline_with_test_version()
        
        # 2. Upload duplicate file content with a new name
        self.client.storage.from_(self.bucket_name).upload("incoming/test_dup.json", file_bytes)
        
        # Run second run
        metrics = self.run_pipeline_with_test_version()
        
        # 3. Assertions
        self.assertEqual(metrics["status"], "SUCCESS")
        self.assertEqual(metrics["files_found"], 1)
        self.assertEqual(metrics["files_processed"], 0)
        self.assertEqual(metrics["files_skipped"], 1)
        self.assertEqual(metrics["files_failed"], 0)
        self.assertEqual(metrics["signals_created"], 0)

        # Verify duplicate file is deleted from incoming/
        incoming_files = [f["name"] for f in self.client.storage.from_(self.bucket_name).list("incoming")]
        self.assertNotIn("test_dup.json", incoming_files)

    def test_3_partial_failure_broken_json(self):
        # 1. Upload broken json & a valid json file
        self.client.storage.from_(self.bucket_name).upload(
            "incoming/test_broken.json",
            b"{\"broken_json\": "
        )
        
        valid_signal = {
            "generatedAt": 1782952265463,
            "signals": [
                {
                    "id": 1003,
                    "deviceId": "test_phone_suite",
                    "source": "test_source_suite",
                    "sender": "Sender C",
                    "message": "Hello Test 3",
                    "timestamp": 1782922228060
                }
            ]
        }
        self.client.storage.from_(self.bucket_name).upload(
            "incoming/test_valid.json",
            json.dumps(valid_signal).encode("utf-8")
        )
        
        # 2. Run pipeline
        metrics = self.run_pipeline_with_test_version()
        
        # 3. Assertions
        self.assertEqual(metrics["status"], "PARTIAL_SUCCESS")
        self.assertEqual(metrics["files_found"], 2)
        self.assertEqual(metrics["files_processed"], 1)
        self.assertEqual(metrics["files_skipped"], 0)
        self.assertEqual(metrics["files_failed"], 1)
        self.assertEqual(metrics["signals_created"], 1)
        
        # Verify broken file is moved to failed/ folder
        incoming_files = [f["name"] for f in self.client.storage.from_(self.bucket_name).list("incoming")]
        failed_files = [f["name"] for f in self.client.storage.from_(self.bucket_name).list("failed")]
        self.assertNotIn("test_broken.json", incoming_files)
        self.assertIn("test_broken.json", failed_files)

    def test_4_supabase_unavailable(self):
        # 1. Initialize client with invalid credentials to simulate DB outage
        invalid_url = "https://invalid-subdomain-tbwnyuampjo.supabase.co"
        invalid_key = "invalid-key"
        invalid_client = create_client(invalid_url, invalid_key)
        
        # 2. Run orchestrator
        metrics = run_pipeline(invalid_client)
        
        # 3. Assertions
        self.assertEqual(metrics["status"], "FAILED")
        self.assertIn("error_message", metrics)
        self.assertTrue(len(metrics["error_message"]) > 0)

    def test_5_rerun_duplicate_signals(self):
        # 1. Process a signal first
        signal_data = {
            "generatedAt": 1782952265463,
            "signals": [
                {
                    "id": 1001,
                    "deviceId": "test_phone_suite",
                    "source": "test_source_suite",
                    "sender": "Sender A",
                    "message": "Hello Test 1",
                    "timestamp": 1782922228047
                }
            ]
        }
        self.client.storage.from_(self.bucket_name).upload(
            "incoming/test_single.json",
            json.dumps(signal_data).encode("utf-8")
        )
        self.run_pipeline_with_test_version()
        
        # Verify 1 signal is in DB
        res1 = self.client.table("mobile_signals").select("*").eq("device_id", "test_phone_suite").execute()
        self.assertEqual(len(res1.data), 1)
        
        # 2. Upload a new file (different name and content hash, so file is processed,
        # but contains the exact same signal values inside it to trigger signal duplicate check)
        rerun_data = {
            "generatedAt": 1782952265499, # different time so file hash is different
            "signals": [
                {
                    "id": 1001,
                    "deviceId": "test_phone_suite",
                    "source": "test_source_suite",
                    "sender": "Sender A",
                    "message": "Hello Test 1",
                    "timestamp": 1782922228047 # exact same message, sender, timestamp
                }
            ]
        }
        self.client.storage.from_(self.bucket_name).upload(
            "incoming/test_rerun.json",
            json.dumps(rerun_data).encode("utf-8")
        )
        
        metrics = self.run_pipeline_with_test_version()
        
        # 3. Assertions
        self.assertEqual(metrics["status"], "SUCCESS")
        self.assertEqual(metrics["files_found"], 1)
        self.assertEqual(metrics["files_processed"], 1)
        self.assertEqual(metrics["signals_created"], 0) # skipped inserting duplicate signal!

        # Assert no duplicate signals are stored in database
        res2 = self.client.table("mobile_signals").select("*").eq("device_id", "test_phone_suite").execute()
        self.assertEqual(len(res2.data), 1)

if __name__ == "__main__":
    unittest.main()
