# services/ingestion_service.py

import os
import sys
from datetime import datetime
import uuid
from loguru import logger

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import SessionLocal
from sqlalchemy import text
from services.supabase_repo import supabase

LINEAGE_TABLES = [
    "mobile_signals", "qualified_signals", "understood_signals", 
    "financial_facts", "facts", "todo_items", "fyi_events", "daily_briefs"
]

class IngestionService:

    @classmethod
    def create_batch(cls, source_type: str, source_name: str, file_name: str | None = None, file_hash: str | None = None) -> str:
        """Creates a new ingestion batch in both SQLite and Supabase."""
        batch_id = f"B{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        now_str = datetime.utcnow().isoformat()
        
        logger.info(f"Creating ingestion batch: {batch_id} (source: {source_name})")

        # 1. Save to Supabase
        try:
            supabase.table("ingestion_batches").insert({
                "batch_id": batch_id,
                "source_type": source_type,
                "source_name": source_name,
                "file_name": file_name,
                "file_hash": file_hash,
                "status": "STARTED",
                "started_at": now_str,
                "created_at": now_str,
                "updated_at": now_str
            }).execute()
        except Exception as e:
            logger.error(f"Failed to save batch {batch_id} to Supabase: {e}")

        # 2. Save to SQLite
        db = SessionLocal()
        try:
            db.execute(text("""
                INSERT INTO ingestion_batches 
                (batch_id, source_type, source_name, file_name, file_hash, status, started_at, created_at, updated_at)
                VALUES (:batch_id, :source_type, :source_name, :file_name, :file_hash, 'STARTED', :started_at, :created_at, :updated_at)
            """), {
                "batch_id": batch_id,
                "source_type": source_type,
                "source_name": source_name,
                "file_name": file_name,
                "file_hash": file_hash,
                "started_at": datetime.utcnow(),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })
            db.commit()
        except Exception as e:
            logger.error(f"Failed to save batch {batch_id} to SQLite: {e}")
        finally:
            db.close()

        return batch_id

    @classmethod
    def update_batch_metrics(cls, batch_id: str, raw: int, accepted: int, duplicates: int, rejected: int):
        """Updates the metrics of a batch."""
        now_str = datetime.utcnow().isoformat()

        # 1. Update Supabase
        try:
            supabase.table("ingestion_batches").update({
                "raw_records": raw,
                "accepted_records": accepted,
                "duplicate_records": duplicates,
                "rejected_records": rejected,
                "updated_at": now_str
            }).eq("batch_id", batch_id).execute()
        except Exception as e:
            logger.error(f"Failed to update batch metrics on Supabase: {e}")

        # 2. Update SQLite
        db = SessionLocal()
        try:
            db.execute(text("""
                UPDATE ingestion_batches 
                SET raw_records = :raw, accepted_records = :accepted, 
                    duplicate_records = :duplicates, rejected_records = :rejected,
                    updated_at = :updated_at
                WHERE batch_id = :batch_id
            """), {
                "batch_id": batch_id,
                "raw": raw,
                "accepted": accepted,
                "duplicates": duplicates,
                "rejected": rejected,
                "updated_at": datetime.utcnow()
            })
            db.commit()
        except Exception as e:
            logger.error(f"Failed to update batch metrics on SQLite: {e}")
        finally:
            db.close()

    @classmethod
    def complete_batch(cls, batch_id: str):
        """Completes a batch."""
        now_str = datetime.utcnow().isoformat()

        # 1. Update Supabase
        try:
            supabase.table("ingestion_batches").update({
                "status": "COMPLETED",
                "completed_at": now_str,
                "updated_at": now_str
            }).eq("batch_id", batch_id).execute()
        except Exception as e:
            logger.error(f"Failed to complete batch on Supabase: {e}")

        # 2. Update SQLite
        db = SessionLocal()
        try:
            db.execute(text("""
                UPDATE ingestion_batches 
                SET status = 'COMPLETED', completed_at = :completed_at, updated_at = :updated_at
                WHERE batch_id = :batch_id
            """), {
                "batch_id": batch_id,
                "completed_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })
            db.commit()
        except Exception as e:
            logger.error(f"Failed to complete batch on SQLite: {e}")
        finally:
            db.close()

    @classmethod
    def fail_batch(cls, batch_id: str, error_message: str):
        """Marks a batch as failed."""
        now_str = datetime.utcnow().isoformat()

        # 1. Update Supabase
        try:
            supabase.table("ingestion_batches").update({
                "status": "FAILED",
                "completed_at": now_str,
                "error_message": error_message,
                "updated_at": now_str
            }).eq("batch_id", batch_id).execute()
        except Exception as e:
            logger.error(f"Failed to mark batch failed on Supabase: {e}")

        # 2. Update SQLite
        db = SessionLocal()
        try:
            db.execute(text("""
                UPDATE ingestion_batches 
                SET status = 'FAILED', completed_at = :completed_at, 
                    error_message = :error_message, updated_at = :updated_at
                WHERE batch_id = :batch_id
            """), {
                "batch_id": batch_id,
                "completed_at": datetime.utcnow(),
                "error_message": error_message,
                "updated_at": datetime.utcnow()
            })
            db.commit()
        except Exception as e:
            logger.error(f"Failed to mark batch failed on SQLite: {e}")
        finally:
            db.close()

    @classmethod
    def rollback_batch(cls, batch_id: str):
        """
        Deletes all records associated with this batch_id across the 8 lineage tables
        and marks the batch as ROLLED_BACK.
        """
        logger.info(f"Rolling back batch: {batch_id}")

        # 1. Delete downstream records on Supabase
        for table in LINEAGE_TABLES:
            try:
                supabase.table(table).delete().eq("batch_id", batch_id).execute()
                logger.info(f"Deleted records from Supabase table '{table}' for batch '{batch_id}'")
            except Exception as e:
                logger.error(f"Failed to rollback Supabase table {table}: {e}")

        # 2. Delete downstream records on SQLite
        db = SessionLocal()
        try:
            for table in LINEAGE_TABLES:
                db.execute(text(f"DELETE FROM {table} WHERE batch_id = :batch_id"), {"batch_id": batch_id})
            
            # 3. Update batch status
            db.execute(text("""
                UPDATE ingestion_batches 
                SET status = 'ROLLED_BACK', updated_at = :updated_at 
                WHERE batch_id = :batch_id
            """), {
                "batch_id": batch_id,
                "updated_at": datetime.utcnow()
            })
            db.commit()
        except Exception as e:
            logger.error(f"Failed to rollback SQLite records: {e}")
        finally:
            db.close()

        # 4. Update batch status on Supabase
        try:
            supabase.table("ingestion_batches").update({
                "status": "ROLLED_BACK",
                "updated_at": datetime.utcnow().isoformat()
            }).eq("batch_id", batch_id).execute()
        except Exception as e:
            logger.error(f"Failed to update batch status to ROLLED_BACK on Supabase: {e}")

    @classmethod
    def replay_batch(cls, batch_id: str):
        """
        Rolls back the batch first, then resets its status to 'STARTED'
        so it can be re-run cleanly.
        """
        cls.rollback_batch(batch_id)
        
        # Reset status to STARTED
        now_str = datetime.utcnow().isoformat()
        try:
            supabase.table("ingestion_batches").update({
                "status": "STARTED",
                "updated_at": now_str
            }).eq("batch_id", batch_id).execute()
        except Exception as e:
            logger.error(f"Failed to update replay status on Supabase: {e}")

        db = SessionLocal()
        try:
            db.execute(text("""
                UPDATE ingestion_batches 
                SET status = 'STARTED', updated_at = :updated_at 
                WHERE batch_id = :batch_id
            """), {
                "batch_id": batch_id,
                "updated_at": datetime.utcnow()
            })
            db.commit()
        except Exception as e:
            logger.error(f"Failed to reset replay status on SQLite: {e}")
        finally:
            db.close()
