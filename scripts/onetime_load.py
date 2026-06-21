# scripts/onetime_load.py

import os
import sys
import json
import hashlib
import time
from loguru import logger
from sqlalchemy import text
from concurrent.futures import ThreadPoolExecutor

# Add root folder to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import initialize_database, SessionLocal, engine
from storage.models.mobile_signal import MobileSignal
from storage.models.signal import Signal
from storage.repositories.mobile_signal_repository import MobileSignalRepository
from storage.repositories.signal_repository import SignalRepository
from consumer.file_processor import compute_message_hash


def load_dump_file() -> dict:
    """
    Attempts to load complete dump.json from various locations.
    """
    paths_to_try = [
        "complete dump.json",
        "complete_dump.json",
        "/home/prad/.gemini/antigravity-ide/brain/451a98b1-c3b5-403e-b807-bebe68b23c78/scratch/dump_preview.json"
    ]
    
    for path in paths_to_try:
        if os.path.exists(path):
            logger.info(f"Loading complete dump from local path: {path}")
            with open(path, "r", encoding="utf-8") as f:
                try:
                    return json.load(f)
                except Exception as e:
                    logger.error(f"Failed to parse {path}: {e}")
                    
    # Dynamic download fallback
    logger.info("Local files not found. Attempting to download complete dump.json from Supabase...")
    import httpx
    SUPABASE_URL = "https://tbwnyuampjoamgarwwoo.supabase.co"
    BUCKET_NAME = "jarvis-signals"
    ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRid255dWFtcGpvYW1nYXJ3d29vIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODE5MzUwOTYsImV4cCI6MjA5NzUxMTA5Nn0.3CdCtROBH2l0wq8GVir9_3rWWZUtD9w2UWsz9caM3cg"
    
    url = f"{SUPABASE_URL}/storage/v1/object/authenticated/{BUCKET_NAME}/complete dump.json"
    headers = {
        "apikey": ANON_KEY,
        "Authorization": f"Bearer {ANON_KEY}",
    }
    
    response = httpx.get(url, headers=headers, timeout=60.0)
    if response.status_code == 200:
        logger.success("Downloaded successfully from Supabase!")
        return response.json()
    else:
        raise Exception(f"Failed to download complete dump.json. HTTP {response.status_code}: {response.text}")


def clean_signals_table():
    """
    Clears the signals table to ensure a clean slate for the test load.
    """
    logger.info("Cleaning up signals table...")
    db = SessionLocal()
    try:
        db.query(Signal).delete()
        db.commit()
        logger.success("Signals table cleared successfully!")
    finally:
        db.close()


def process_and_insert_records(dump_data: dict):
    """
    Filters for 500 SMS (transaction alerts) and all available WhatsApp records,
    ensures no duplicates exist, and inserts them into mobile_signals.
    """
    signals = dump_data.get("signals", [])
    logger.info(f"Total signals in dump: {len(signals)}")
    
    # 1. Filter sources
    whatsapp_candidates = [s for s in signals if s.get("source") == "whatsapp"]
    sms_candidates = [s for s in signals if s.get("source") == "sms"]
    
    logger.info(f"Found {len(whatsapp_candidates)} WhatsApp candidates and {len(sms_candidates)} SMS candidates.")
    
    # 2. Select high-quality SMS transaction records (excluding OTPs)
    bank_keywords = ["debited", "credited", "spent on", "card ending", "a/c ending", "vpa", "transacted"]
    sms_txns = []
    for s in sms_candidates:
        msg = s.get("message", "").lower()
        if any(kw in msg for kw in bank_keywords) and "otp" not in msg:
            sms_txns.append(s)
            
    logger.info(f"Filtered to {len(sms_txns)} SMS bank transaction records (non-OTP).")
    
    # Take up to 500 SMS records and all available WhatsApp records
    selected_sms = sms_txns[:500]
    selected_whatsapp = whatsapp_candidates[:500] # should be 12
    
    to_insert = []
    inserted_hashes = set()
    
    db = SessionLocal()
    try:
        # Load existing mobile signal hashes to avoid duplicates
        existing_hashes = {h[0] for h in db.query(MobileSignal.message_hash).all() if h[0]}
        logger.info(f"Loaded {len(existing_hashes)} existing message hashes from database.")
        
        # Helper to process selection
        def prepare_records(records, label):
            added_count = 0
            for r in records:
                sender = r.get("sender", "")
                message = r.get("message", "")
                timestamp = r.get("timestamp", 0)
                device_id = r.get("deviceId", "pradeep_phone")
                source = r.get("source", "sms")
                
                msg_hash = compute_message_hash(sender, message, timestamp)
                
                # Deduplication checks
                if msg_hash in existing_hashes or msg_hash in inserted_hashes:
                    continue
                    
                mobile_sig = MobileSignal(
                    device_id=device_id,
                    source=source,
                    sender=sender,
                    message=message,
                    mobile_timestamp=str(timestamp),
                    message_hash=msg_hash,
                    processed=False
                )
                to_insert.append(mobile_sig)
                inserted_hashes.add(msg_hash)
                added_count += 1
            logger.info(f"Selected {added_count} unique {label} records for ingestion.")
            
        prepare_records(selected_sms, "SMS")
        prepare_records(selected_whatsapp, "WhatsApp")
        
        if to_insert:
            logger.info(f"Inserting {len(to_insert)} signals into mobile_signals table...")
            db.add_all(to_insert)
            db.commit()
            logger.success(f"Successfully inserted {len(to_insert)} records.")
        else:
            logger.info("No new unique records to insert.")
            
    finally:
        db.close()


def process_single_signal(msg_id, device_id, source, sender, message):
    """
    Thread worker task to process a single signal using the LLM and filter logic.
    """
    db = SessionLocal()
    try:
        signal_dict = {
            "source": source,
            "sender": sender,
            "message": message
        }
        
        # 1. Rule-based Noise Filter check
        from skills.mobile.mobile_noise_filter import MobileNoiseFilter
        if MobileNoiseFilter.is_noise(signal_dict):
            db.query(MobileSignal).filter(MobileSignal.id == msg_id).update({MobileSignal.processed: True})
            db.commit()
            logger.info(f"Mobile Signal ID {msg_id} dropped as noise.")
            return

        # 2. LLM Intent & Detail Extraction
        from skills.mobile.mobile_intent_extractor import MobileIntentExtractor
        extractor = MobileIntentExtractor()
        
        try:
            extracted = extractor.extract_intent(signal_dict)
            category = extracted.get("category", "general")
            signal_type = extracted.get("intent", "unknown")
            importance = extracted.get("priority", "medium")
            summary = extracted.get("summary") or message[:200]
            details = extracted.get("details", {})

            # OTP/Ignore check - discard right away
            if signal_type == "otp" or importance == "ignore":
                db.query(MobileSignal).filter(MobileSignal.id == msg_id).update({MobileSignal.processed: True})
                db.commit()
                logger.info(f"OTP/Ignore mobile signal ID {msg_id} discarded.")
                return

            # Cross-channel duplicate check
            from storage.repositories.signal_repository import SignalRepository
            if SignalRepository.is_duplicate_signal(category, signal_type, details, summary):
                db.query(MobileSignal).filter(MobileSignal.id == msg_id).update({MobileSignal.processed: True})
                db.commit()
                logger.info(f"Cross-channel duplicate detected for mobile signal: {summary}. Skipping.")
                return

            # Store structured signal
            signal_obj = Signal(
                source=source,
                signal_type=signal_type,
                category=category,
                importance=importance,
                summary=summary,
                raw_json=json.dumps(details) if details else None
            )
            db.add(signal_obj)
            
            # Create task in the tasks table if action required
            if extracted.get("action_required", False):
                from storage.models.task import Task
                task_obj = Task(
                    title=summary,
                    category=category,
                    priority=importance,
                    source=source,
                    due_date=extracted.get("due_date")
                )
                db.add(task_obj)

            # Mark processed
            db.query(MobileSignal).filter(MobileSignal.id == msg_id).update({MobileSignal.processed: True})
            db.commit()
            logger.success(f"Structured and saved mobile signal ID {msg_id}")

        except Exception as ex:
            logger.error(f"Failed to extract or save mobile signal ID {msg_id}: {ex}")

    finally:
        db.close()


def run_pipeline():
    """
    Runs the processing pipeline concurrently using ThreadPoolExecutor.
    """
    logger.info("Starting concurrent batch processing pipeline...")
    
    db = SessionLocal()
    try:
        # Fetch all unprocessed signals
        unprocessed = db.query(MobileSignal).filter(MobileSignal.processed == False).all()
        logger.info(f"Loaded {len(unprocessed)} unprocessed signals for concurrent execution.")
    finally:
        db.close()
        
    if not unprocessed:
        return
        
    # Process using ThreadPoolExecutor (limited to 5 workers to keep local CPU / Ollama stable)
    max_workers = 5
    logger.info(f"Spawning thread pool with {max_workers} workers...")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for msg in unprocessed:
            futures.append(
                executor.submit(
                    process_single_signal,
                    msg.id,
                    msg.device_id,
                    msg.source,
                    msg.sender,
                    msg.message
                )
            )
            
        # Wait for all to finish
        for i, future in enumerate(futures):
            try:
                future.result()
            except Exception as e:
                logger.error(f"Thread worker error at index {i}: {e}")
                
    logger.success("All mobile signals processed successfully in thread pool!")


def print_quality_evaluation():
    """
    Gathers and prints statistical counts and examples of structured outputs to evaluate quality.
    """
    logger.info("Gathering quality evaluation statistics...")
    db = SessionLocal()
    try:
        signals = db.query(Signal).all()
        print("\n" + "="*60)
        print("          QUALITY EVALUATION SUMMARY")
        print("="*60)
        print(f"Total Structured Signals Saved: {len(signals)}")
        
        # 1. Distribution by Source
        sources = [s.source for s in signals]
        print("\n1. Distribution by Source:")
        for src, count in sorted(dict_count(sources).items()):
            print(f"  - {src.upper()}: {count}")
            
        # 2. Distribution by Category
        categories = [s.category for s in signals]
        print("\n2. Distribution by Category:")
        for cat, count in sorted(dict_count(categories).items()):
            print(f"  - {cat}: {count}")
            
        # 3. Distribution by Importance/Priority
        importances = [s.importance for s in signals]
        print("\n3. Distribution by Importance/Priority:")
        for imp, count in sorted(dict_count(importances).items()):
            print(f"  - {imp}: {count}")

        # 4. Distribution by Signal Type / Intent
        types = [s.signal_type for s in signals]
        print("\n4. Distribution by Intent Type:")
        for stype, count in sorted(dict_count(types).items()):
            print(f"  - {stype}: {count}")

        # 5. Output Samples
        print("\n" + "-"*60)
        print("                 STRUCTURED OUTPUT SAMPLES")
        print("-"*60)
        for i, s in enumerate(signals[:8]):
            print(f"\nSample #{i+1}: Source = {s.source} | Category = {s.category} | Priority = {s.importance}")
            print(f"Summary: {s.summary}")
            try:
                details = json.loads(s.raw_json) if s.raw_json else {}
                print(f"Structured Details: {json.dumps(details, indent=2)}")
            except Exception:
                print(f"Raw JSON: {s.raw_json}")
        print("="*60 + "\n")
        
    finally:
        db.close()


def dict_count(lst: list) -> dict:
    from collections import Counter
    return Counter(lst)


def main():
    initialize_database()
    clean_signals_table()
    
    try:
        dump_data = load_dump_file()
        process_and_insert_records(dump_data)
        run_pipeline()
        print_quality_evaluation()
    except Exception as e:
        logger.exception(f"Onetime load failed: {e}")


if __name__ == "__main__":
    main()
