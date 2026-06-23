# scripts/load_historical_to_postgres.py

import os
import sys
import json
import uuid
import re
from datetime import datetime
from loguru import logger

# Add root folder to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import SessionLocal
from storage.models.signal import Signal
from services.supabase_repo import SupabaseRepo, supabase
from services.signal_processor import SignalProcessor

def migrate():
    logger.info("Starting historical SMS signal processing and Postgres migration...")
    
    db = SessionLocal()
    try:
        # 1. Fetch up to 500 of the latest SMS signals
        sms_signals = db.query(Signal).filter(
            Signal.source == "sms"
        ).order_by(
            Signal.created_at.desc()
        ).limit(500).all()
        
        logger.info(f"Retrieved {len(sms_signals)} latest SMS signals from SQLite.")
        
        if not sms_signals:
            logger.info("No SMS signals found in SQLite to process.")
            return

        migrated_signals = 0
        migrated_todos = 0
        migrated_financials = 0
        migrated_fyis = 0

        for signal in sms_signals:
            # Deterministic UUID for the signal
            signal_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"signal-{signal.id}")
            
            # Safely parse raw_json
            details = {}
            if signal.raw_json:
                try:
                    details = json.loads(signal.raw_json) or {}
                except Exception:
                    pass

            # 2. Save Signal to Supabase Postgres
            ok = SupabaseRepo.save_signal(
                signal_id=signal_uuid,
                source=signal.source,
                sender=details.get("paid_from") or details.get("sender") or "",
                message=signal.summary,
                signal_timestamp=signal.created_at,
                created_at=signal.created_at,
                raw_signal_id=str(signal.id),
                metadata=details
            )
            if not ok:
                logger.error(f"Failed to save signal ID {signal.id} to Supabase Postgres. Skipping extraction.")
                continue
                
            migrated_signals += 1

            # 3. Categorized Extraction & Loading
            cat = (signal.category or "general").upper()
            
            # --- TODOS ---
            if cat == "TODO":
                # Determine due date
                due_date_str = details.get("due_date")
                due_date_dt = None
                if due_date_str:
                    normalized = SignalProcessor.parse_and_normalize_due_date(due_date_str, signal.created_at)
                    if normalized:
                        try:
                            due_date_dt = datetime.strptime(normalized, "%Y-%m-%d")
                        except Exception:
                            pass
                if not due_date_dt:
                    due_date_dt = signal.created_at

                todo_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"todo-{signal.id}")
                if SupabaseRepo.create_todo(
                    todo_id=todo_uuid,
                    title=signal.summary,
                    description=details.get("description", ""),
                    priority=signal.importance,
                    status="OPEN",
                    due_date=due_date_dt,
                    source_signal_id=signal_uuid
                ):
                    migrated_todos += 1

            # --- FINANCIAL / INSURANCE ---
            elif cat in ("FINANCIAL", "INSURANCE"):
                # Determine transaction type
                if cat == "INSURANCE":
                    tx_type = "renewal"
                else:
                    tx_type = details.get("transaction_type", "debit")
                
                # Parse amount
                amount_candidate = details.get("amount")
                amount = SignalProcessor.parse_amount(amount_candidate) if amount_candidate else 0.0

                merchant = details.get("paid_to") or details.get("merchant") or ""
                currency = details.get("currency") or "INR"

                event_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"financial-{signal.id}")
                if SupabaseRepo.create_financial_event(
                    event_id=event_uuid,
                    merchant=merchant,
                    amount=amount if amount is not None else 0.0,
                    currency=currency,
                    category=details.get("category") or "General",
                    status="OPEN",
                    event_timestamp=signal.created_at,
                    source_signal_id=signal_uuid
                ):
                    migrated_financials += 1

            # --- FYI ---
            elif cat == "FYI":
                content = details.get("message_content") or details.get("summary") or signal.summary
                fyi_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"fyi-{signal.id}")
                if SupabaseRepo.create_fyi_event(
                    event_id=fyi_uuid,
                    title=signal.summary,
                    summary=content,
                    category=signal.signal_type or "general_notification",
                    read_flag=False,
                    source_signal_id=signal_uuid
                ):
                    migrated_fyis += 1

        logger.success("==================================================")
        logger.success("         POSTGRES MIGRATION RUN COMPLETE")
        logger.success("==================================================")
        logger.success(f"Signals Migrated        : {migrated_signals}")
        logger.success(f"Todos Created           : {migrated_todos}")
        logger.success(f"Financial Events Created: {migrated_financials}")
        logger.success(f"FYI Events Created      : {migrated_fyis}")
        logger.success("==================================================")

    finally:
        db.close()

if __name__ == "__main__":
    migrate()
