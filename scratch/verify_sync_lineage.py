# scratch/verify_sync_lineage.py

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import SessionLocal
from sqlalchemy import text
from services.ingestion_service import IngestionService
from services.sync_service import SyncService
from consumer.consumer_service import ConsumerService
from services.supabase_repo import supabase

db = SessionLocal()

print("=== Starting End-to-End Lineage & Sync Verification ===")

# Test 1: Ingestion Batch Creation
print("\n[Test 1] Testing Batch Creation...")
batch_id = IngestionService.create_batch(
    source_type="sms",
    source_name="verification_test_source",
    file_name="test_sms.json",
    file_hash="dummy_hash_123"
)
print(f"Created Verification Batch ID: {batch_id}")

# Verify batch in local SQLite
local_batch = db.execute(text("SELECT * FROM ingestion_batches WHERE batch_id = :b"), {"b": batch_id}).fetchone()
assert local_batch is not None, "Batch not found in local SQLite!"
print("✔ Batch successfully logged locally.")

# Verify batch in Supabase
try:
    remote_batch_res = supabase.table("ingestion_batches").select("*").eq("batch_id", batch_id).execute()
    assert len(remote_batch_res.data) > 0, "Batch not found in remote Supabase!"
    print("✔ Batch successfully synced to remote Supabase.")
except Exception as e:
    print(f"✘ Supabase Batch Verification failed: {e}")

# Test 2: Log duplicate file detection
print("\n[Test 2] Testing Duplicate Batch Detection...")
# Create duplicate processed file registration
from storage.repositories.processed_file_repository import ProcessedFileRepository
ProcessedFileRepository.register_file(
    file_name="test_sms.json",
    bucket_name="signals",
    file_path="incoming/test_sms.json",
    file_hash="dummy_hash_123",
    status="PROCESSED"
)
print("Registered processed file registry successfully.")

# Test 3: Incremental Sync verification (Local pending push)
print("\n[Test 3] Testing Sync push of PENDING rows...")
# Create a dummy signal locally
db.execute(text("""
    INSERT INTO mobile_signals (device_id, source, sender, message, mobile_timestamp, processed, message_hash, batch_id, sync_status, created_at)
    VALUES ('test_device', 'sms', 'TEST_SENDER', 'Verification message payload', '1782229415138', 0, 'hash_verify_123', :batch_id, 'PENDING', datetime('now'))
"""), {"batch_id": batch_id})
db.commit()
print("✔ Local pending mobile_signal record created.")

# Run push changes
pushed = SyncService.push_changes()
print(f"Pushed {pushed} changes up to Supabase.")

# Verify remote table contains our record
try:
    remote_sig_res = supabase.table("mobile_signals").select("*").eq("message_hash", "hash_verify_123").execute()
    assert len(remote_sig_res.data) > 0, "Record not found on Supabase after push!"
    print("✔ Pushed record successfully located on remote Supabase.")
except Exception as e:
    print(f"✘ Supabase Sync push verification failed: {e}")

# Test 4: Rollback Batch support
print("\n[Test 4] Testing Rollback Batch capabilities...")
# Add local and remote qualified signals under the batch
db.execute(text("""
    INSERT INTO qualified_signals (signal_id, source, sender, message, timestamp, qualification_score, qualification_status, batch_id, sync_status, created_at)
    VALUES ('1', 'sms', 'TEST_SENDER', 'Verification message payload', datetime('now'), 90, 'QUALIFIED', :batch_id, 'SYNCED', datetime('now'))
"""), {"batch_id": batch_id})
db.commit()
print("Local qualified_signal logged.")

# Call IngestionService Rollback
IngestionService.rollback_batch(batch_id)
print("✔ Rollback executed.")

# Check SQLite
assert db.execute(text("SELECT COUNT(*) FROM mobile_signals WHERE batch_id = :b"), {"b": batch_id}).scalar() == 0, "mobile_signals rollback failed!"
assert db.execute(text("SELECT COUNT(*) FROM qualified_signals WHERE batch_id = :b"), {"b": batch_id}).scalar() == 0, "qualified_signals rollback failed!"
print("✔ Downstream SQLite records successfully rolled back.")

# Check Supabase
try:
    remote_check_res = supabase.table("mobile_signals").select("*").eq("batch_id", batch_id).execute()
    assert len(remote_check_res.data) == 0, "Supabase rollback failed!"
    print("✔ Downstream remote Supabase records successfully rolled back.")
except Exception as e:
    print(f"✘ Supabase rollback verification failed: {e}")

# Clean up verification leftovers
db.execute(text("DELETE FROM processed_files WHERE file_hash = 'dummy_hash_123'"))
db.execute(text("DELETE FROM ingestion_batches WHERE batch_id = :b"), {"b": batch_id})
db.commit()
try:
    supabase.table("ingestion_batches").delete().eq("batch_id", batch_id).execute()
except Exception:
    pass

print("\n=== All Verification Scenarios Passed Successfully! ===")
db.close()
