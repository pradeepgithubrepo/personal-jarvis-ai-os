# services/sync_service.py

import os
import sys
import json
from datetime import datetime
from loguru import logger

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import SessionLocal
from sqlalchemy import text
from services.supabase_repo import supabase

SYNC_TABLES = [
    "mobile_signals", "qualified_signals", "understood_signals", 
    "financial_facts", "facts", "todo_items", "fyi_events", "daily_briefs"
]

TABLE_PK_MAP = {
    "mobile_signals": "id",
    "qualified_signals": "id",
    "understood_signals": "id",
    "financial_facts": "id",
    "facts": "fact_id",
    "todo_items": "todo_id",
    "fyi_events": "event_id",
    "daily_briefs": "brief_id"
}

class SyncService:

    @classmethod
    def log_audit(cls, db_session, entity: str, record_id: str, batch_id: str | None, operation: str, status: str, message: str):
        """Logs a sync operation to the local and remote audit logs."""
        # 1. Local Audit Log
        try:
            db_session.execute(text("""
                INSERT INTO sync_audit_log (entity_name, record_id, batch_id, operation, status, message, created_at)
                VALUES (:entity, :record_id, :batch_id, :operation, :status, :message, :created_at)
            """), {
                "entity": entity,
                "record_id": str(record_id),
                "batch_id": batch_id,
                "operation": operation,
                "status": status,
                "message": message,
                "created_at": datetime.utcnow()
            })
        except Exception as e:
            logger.error(f"Failed to write local audit log: {e}")

        # 2. Remote Audit Log
        try:
            supabase.table("sync_audit_log").insert({
                "entity_name": entity,
                "record_id": str(record_id),
                "batch_id": batch_id,
                "operation": operation,
                "status": status,
                "message": message,
                "created_at": datetime.utcnow().isoformat()
            }).execute()
        except Exception as e:
            logger.error(f"Failed to write remote audit log: {e}")

    @classmethod
    def get_last_pull_time(cls, db_session, entity: str) -> datetime:
        """Gets the last successful pull timestamp for the entity."""
        res = db_session.execute(text("SELECT last_pull_time FROM sync_metadata WHERE entity_name = :entity"), {"entity": entity}).scalar()
        if res:
            if isinstance(res, str):
                return datetime.fromisoformat(res.split(".")[0].replace("Z", "").replace(" ", "T"))
            return res
        return datetime(1970, 1, 1)

    @classmethod
    def update_pull_time(cls, db_session, entity: str, pull_time: datetime):
        """Updates the pull metadata timestamp for the entity."""
        db_session.execute(text("""
            INSERT INTO sync_metadata (entity_name, last_pull_time, updated_at)
            VALUES (:entity, :pull_time, :updated_at)
            ON CONFLICT(entity_name) DO UPDATE SET last_pull_time = :pull_time, updated_at = :updated_at
        """), {
            "entity": entity,
            "pull_time": pull_time,
            "updated_at": datetime.utcnow()
        })
        db_session.commit()

    @classmethod
    def pull_changes(cls) -> int:
        """Pulls delta changes from Supabase to local SQLite (Remote-Wins)."""
        logger.info("SyncService: Executing Pull Delta Changes...")
        db = SessionLocal()
        pulled_count = 0
        try:
            for table in SYNC_TABLES:
                pk = TABLE_PK_MAP[table]
                last_pull = cls.get_last_pull_time(db, table)
                
                # Fetch remote rows modified since last pull
                logger.info(f"SyncService: Pulling {table} changes since {last_pull.isoformat()}...")
                try:
                    remote_res = supabase.table(table).select("*").gt("updated_at", last_pull.isoformat()).execute()
                    remote_rows = remote_res.data or []
                except Exception as e:
                    logger.error(f"Failed to pull {table} from Supabase: {e}")
                    continue

                if not remote_rows:
                    continue

                logger.info(f"SyncService: Found {len(remote_rows)} remote changes for {table}")
                max_updated = last_pull

                for row in remote_rows:
                    pk_val = row[pk]
                    
                    # Convert jsonb / evidence fields to string if writing to sqlite
                    for col_key, val in list(row.items()):
                        if isinstance(val, (dict, list)):
                            row[col_key] = json.dumps(val)

                    # Check local row
                    local_row = db.execute(text(f"SELECT * FROM {table} WHERE {pk} = :pk_val"), {"pk_val": str(pk_val)}).fetchone()
                    
                    row_updated_str = row.get("updated_at", "").split(".")[0].replace("Z", "").replace("T", " ")
                    row_updated = datetime.fromisoformat(row_updated_str) if row_updated_str else datetime.utcnow()
                    
                    if row_updated > max_updated:
                        max_updated = row_updated

                    if not local_row:
                        # Insert local
                        cols = ", ".join(row.keys())
                        vals = ", ".join([f":{k}" for k in row.keys()])
                        db.execute(text(f"INSERT INTO {table} ({cols}) VALUES ({vals})"), row)
                        cls.log_audit(db, table, str(pk_val), row.get("batch_id"), "PULL_SUCCESS", "SUCCESS", "Inserted new remote row locally.")
                        pulled_count += 1
                    else:
                        # Conflict Check: Remote Wins
                        local_updated_str = local_row._mapping.get("updated_at")
                        local_updated = datetime.fromisoformat(local_updated_str.split(".")[0]) if local_updated_str else datetime(1970, 1, 1)

                        if row_updated > local_updated:
                            # Remote is newer: Overwrite local
                            set_clause = ", ".join([f"{k} = :{k}" for k in row.keys()])
                            db.execute(text(f"UPDATE {table} SET {set_clause} WHERE {pk} = :pk_val"), {**row, "pk_val": str(pk_val)})
                            
                            # Mark local status
                            db.execute(text(f"UPDATE {table} SET sync_status = 'CONFLICT_RESOLVED_REMOTE' WHERE {pk} = :pk_val"), {"pk_val": str(pk_val)})
                            
                            cls.log_audit(db, table, str(pk_val), row.get("batch_id"), "CONFLICT", "RESOLVED_REMOTE", "Remote row was newer; local record overwritten.")
                            pulled_count += 1
                
                cls.update_pull_time(db, table, max_updated)
            db.commit()
        finally:
            db.close()
        return pulled_count

    @classmethod
    def push_changes(cls) -> int:
        """Pushes pending local SQLite changes up to Supabase."""
        logger.info("SyncService: Executing Push Delta Changes...")
        db = SessionLocal()
        pushed_count = 0
        try:
            for table in SYNC_TABLES:
                pk = TABLE_PK_MAP[table]
                
                # Fetch pending SQLite rows
                cols_res = db.execute(text(f"PRAGMA table_info({table})")).fetchall()
                cols = [c[1] for c in cols_res]
                
                local_rows = db.execute(text(f"SELECT * FROM {table} WHERE sync_status = 'PENDING'")).fetchall()
                if not local_rows:
                    continue

                logger.info(f"SyncService: Found {len(local_rows)} pending changes for {table}")
                
                for row in local_rows:
                    row_dict = dict(zip(cols, row))
                    pk_val = row_dict[pk]
                    
                    # Clean/format dict for PostgREST upsert
                    cleaned = {}
                    for k, v in row_dict.items():
                        if isinstance(v, datetime):
                            cleaned[k] = v.isoformat()
                        elif k in ["sender_aliases", "receiver_aliases", "aliases", "metadata", "fact_value", "evidence", "source_reference", "contract_json"]:
                            if isinstance(v, str):
                                try:
                                    cleaned[k] = json.loads(v)
                                except Exception:
                                    cleaned[k] = v
                            else:
                                cleaned[k] = v
                        else:
                            cleaned[k] = v

                    # Pop primary keys if bigserial integer increment
                    if table in ["mobile_signals", "qualified_signals", "runtime_events"] and "id" in cleaned:
                        # Let Postgres generate BigSerial ID
                        cleaned.pop("id", None)

                    # Update status to SYNCED
                    cleaned["sync_status"] = "SYNCED"
                    if "updated_at" in cols:
                        cleaned["updated_at"] = datetime.utcnow().isoformat()

                    try:
                        # PostgREST Upsert
                        supabase.table(table).upsert(cleaned).execute()
                        
                        # Mark local as SYNCED
                        if "updated_at" in cols:
                            db.execute(text(f"UPDATE {table} SET sync_status = 'SYNCED', updated_at = :now WHERE {pk} = :pk_val"), {
                                "now": datetime.utcnow(),
                                "pk_val": str(pk_val)
                            })
                        else:
                            db.execute(text(f"UPDATE {table} SET sync_status = 'SYNCED' WHERE {pk} = :pk_val"), {
                                "pk_val": str(pk_val)
                            })
                        cls.log_audit(db, table, str(pk_val), row_dict.get("batch_id"), "PUSH_SUCCESS", "SUCCESS", "Local pending row successfully pushed and synced.")
                        pushed_count += 1
                    except Exception as e:
                        logger.error(f"Failed to push record {pk_val} in {table} to Supabase: {e}")
                        db.execute(text(f"UPDATE {table} SET sync_status = 'FAILED' WHERE {pk} = :pk_val"), {"pk_val": str(pk_val)})

            db.commit()
        finally:
            db.close()
        return pushed_count

    @classmethod
    def sync_all(cls) -> dict:
        """Runs a complete pull then push sync pass."""
        pulled = cls.pull_changes()
        pushed = cls.push_changes()
        return {"pulled": pulled, "pushed": pushed}
