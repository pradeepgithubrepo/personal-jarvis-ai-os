# tests/test_consumer.py

import sys
import os
import json
import time
from loguru import logger
from unittest.mock import patch

# Add root folder to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import initialize_database, SessionLocal
from storage.models.mobile_signal import MobileSignal
from consumer.consumer_service import ConsumerService


class MockSupabaseClient:
    def __init__(self):
        self.url = "mock://supabase"
        self.key = "mock-key"
        self.bucket = "jarvis-signals"
        self.headers = {}
        # In-memory mock storage path -> content
        self.storage = {}

    def list_files(self, folder_name: str) -> list[str]:
        prefix = f"{folder_name}/"
        results = []
        for path in self.storage.keys():
            if path.startswith(prefix):
                results.append(path)
        return results

    def download_file(self, full_path: str) -> str:
        if full_path in self.storage:
            return self.storage[full_path]
        raise Exception(f"HTTP 404: Object not found")

    def upload_file(self, full_path: str, content: str) -> bool:
        self.storage[full_path] = content
        return True

    def delete_file(self, full_path: str) -> bool:
        if full_path in self.storage:
            del self.storage[full_path]
            return True
        return False

    def copy_file(self, src_path: str, dest_path: str) -> bool:
        if src_path in self.storage:
            self.storage[dest_path] = self.storage[src_path]
            return True
        return False

    def move_file(self, src_path: str, dest_path: str) -> bool:
        logger.info(f"Moving file '{src_path}' to '{dest_path}' in Supabase Storage...")
        if self.copy_file(src_path, dest_path):
            return self.delete_file(src_path)
        return False


def run_integration_test():
    logger.info("Initializing database...")
    initialize_database()

    # Clear existing test data from SQLite
    db = SessionLocal()
    try:
        db.query(MobileSignal).filter(MobileSignal.device_id == "test_device_1").delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()

    # Create Mock Supabase client
    supabase = MockSupabaseClient()
    
    unique_id = int(time.time() * 1000)
    filename = f"pradeep/pradeep_test_{unique_id}.json"
    
    # 1. Define mock signals
    payload = {
        "generatedAt": unique_id,
        "signals": [
            {
                "deviceId": "test_device_1",
                "source": "whatsapp",
                "sender": "John Doe",
                "message": f"Hello Jarvis {unique_id}",
                "timestamp": unique_id
            },
            {
                "deviceId": "test_device_1",
                "source": "sms",
                "sender": "BankAlert",
                "message": f"Your OTP is 123456",
                "timestamp": unique_id + 1000
            }
        ]
    }
    
    content = json.dumps(payload)
    
    # 2. Upload file to Mock Storage
    logger.info(f"Uploading mock signals to Supabase: {filename}")
    assert supabase.upload_file(filename, content), "Upload failed"
    logger.success("Upload succeeded!")

    # Patch SupabaseClient class in consumer_service module
    with patch("consumer.consumer_service.SupabaseClient", return_value=supabase):
        try:
            # 3. Verify files are listed
            listed_files = supabase.list_files("pradeep")
            assert filename in listed_files, f"Expected {filename} in listed files, got {listed_files}"
            logger.success("File listing verified!")

            # 4. Run the consumer sync
            logger.info("Running consumer sync...")
            consumer = ConsumerService()
            consumer.run_sync()

            # 5. Verify records inserted into SQLite DB
            db = SessionLocal()
            try:
                signals = db.query(MobileSignal).filter(MobileSignal.device_id == "test_device_1").all()
                assert len(signals) == 2, f"Expected 2 signals, found {len(signals)}"
                
                # Check fields
                whatsapp_signal = next(s for s in signals if s.source == "whatsapp")
                assert whatsapp_signal.sender == "John Doe"
                assert whatsapp_signal.message == f"Hello Jarvis {unique_id}"
                assert whatsapp_signal.mobile_timestamp == str(unique_id)
                assert whatsapp_signal.message_hash is not None
                
                logger.success("SQLite database records verified!")
                
                # 6. Test Deduplication
                # Re-upload the exact same file to Supabase to test if it gets deduplicated on next sync
                logger.info("Re-uploading for deduplication test...")
                assert supabase.upload_file(filename, content), "Re-upload failed"
                
                # Run sync again
                logger.info("Running consumer sync again (deduplication check)...")
                consumer.run_sync()
                
                # Verify no extra records were inserted (count remains 2)
                signals_after = db.query(MobileSignal).filter(MobileSignal.device_id == "test_device_1").all()
                assert len(signals_after) == 2, f"Expected 2 signals after deduplication run, found {len(signals_after)}"
                logger.success("Deduplication logic verified successfully!")

            finally:
                db.close()

            # 7. Verify local archive file exists
            archive_path = os.path.abspath(os.path.join("data/archive", filename))
            assert os.path.exists(archive_path), f"Expected archive file at {archive_path} to exist"
            with open(archive_path, "r", encoding="utf-8") as f:
                archive_data = json.load(f)
                assert archive_data["generatedAt"] == unique_id
            logger.success("Local archiving verified!")

            # 8. Verify the file is deleted from original Supabase folder and exists in archive
            listed_files_after = supabase.list_files("pradeep")
            assert filename not in listed_files_after, f"Expected {filename} to be deleted from pradeep/, but it is still there"
            
            archive_filename = f"archive/{filename.split('/')[-1]}"
            listed_archives = supabase.list_files("archive")
            assert archive_filename in listed_archives, f"Expected {archive_filename} to be moved under archive/, but not found"
            logger.success("Supabase Storage remote archiving verified!")

            # Clean up remote archive file to keep bucket clean
            supabase.delete_file(archive_filename)
            logger.success("Cleaned up mock archive file.")

            logger.success("ALL INTEGRATION TESTS PASSED SUCCESSFULLY!")

        except Exception as e:
            logger.error(f"Integration test failed: {e}")
            raise e


if __name__ == "__main__":
    run_integration_test()
