# scripts/reprocess_pradeep_history.py

import os
import sys
import time
import uuid
import hashlib
import threading
from datetime import datetime
from loguru import logger

# Add root folder to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from configs.settings import settings
from configs.constants import TaskType
from storage.db.database import SessionLocal
from storage.models.mobile_signal import MobileSignal
from storage.repositories.mobile_signal_repository import MobileSignalRepository
from storage.repositories.signal_repository import SignalRepository
from storage.repositories.processed_file_repository import ProcessedFileRepository
from storage.repositories.classification_cache_repository import ClassificationCacheRepository
from skills.mobile.mobile_intent_extractor import MobileIntentExtractor
from intelligence.routing.router import IntelligenceRouter
from consumer.supabase_client import SupabaseClient
from consumer.file_processor import FileProcessor
from services.system_initializer import initialize_system
from services.mobile_signal_pipeline import MobileSignalPipeline
from services.signal_processor import SignalProcessor
from services.financial_aggregator import FinancialAggregator
from services.supabase_repo import SupabaseRepo

# Thread lock to serialize printing progress
print_lock = threading.Lock()

class ReprocessMetrics:
    # Thread-safe global metrics container
    counters = {
        "files_found": 0,
        "files_processed": 0,
        "signals_loaded": 0,
        "signals_processed": 0,
        "saved_signals": 0,
        "todos_created": 0,
        "financial_events": 0,
        "fyi_events": 0,
        "facts_created": 0,
        "errors": 0,
        
        # Optimization Stats
        "cache_hits": 0,
        "cache_misses": 0,
        "pre_classified": 0,
        "llm_calls_executed": 0,
        "llm_calls_avoided": 0
    }
    run_start_time = 0.0

def print_progress(force=False):
    """Prints the current progress counters cleanly to stdout with ETA and throughput."""
    with print_lock:
        now = time.time()
        if not force and getattr(print_progress, "last_print", 0) + 2.0 > now:
            return
        print_progress.last_print = now

        elapsed = now - ReprocessMetrics.run_start_time if ReprocessMetrics.run_start_time > 0 else 0.0
        if elapsed > 0:
            throughput = (ReprocessMetrics.counters["signals_processed"] / elapsed) * 60.0
        else:
            throughput = 0.0

        total_signals = ReprocessMetrics.counters["signals_loaded"]
        processed = ReprocessMetrics.counters["signals_processed"]
        remaining = max(0, total_signals - processed)
        
        if throughput > 0:
            eta_minutes = remaining / throughput
            if eta_minutes >= 1.0:
                eta_str = f"{eta_minutes:.1f} minutes"
            else:
                eta_str = f"{eta_minutes * 60:.0f} seconds"
        else:
            eta_str = "Calculating..."

        print(f"\nProgress Update [{datetime.now().strftime('%H:%M:%S')}]:")
        print(f"  Signals Loaded        : {total_signals}")
        print(f"  Processed             : {processed} / {total_signals}")
        print(f"  Remaining             : {remaining}")
        print(f"  Cache Hits            : {ReprocessMetrics.counters['cache_hits']}")
        print(f"  Cache Misses          : {ReprocessMetrics.counters['cache_misses']}")
        print(f"  Pre-Classified        : {ReprocessMetrics.counters['pre_classified']}")
        print(f"  LLM Calls Executed    : {ReprocessMetrics.counters['llm_calls_executed']}")
        print(f"  LLM Calls Avoided     : {ReprocessMetrics.counters['llm_calls_avoided']}")
        print(f"  Throughput            : {throughput:.1f} signals/min")
        print(f"  ETA                   : {eta_str}")
        print(f"  Errors                : {ReprocessMetrics.counters['errors']}")
        print("-" * 50)
        sys.stdout.flush()

# Setup Wrapper Decorators to count database writes and cache actions dynamically
def setup_decorators():
    # 1. Processed Signals (count when MobileSignalRepository.mark_signals_processed is called)
    orig_mark_processed = MobileSignalRepository.mark_signals_processed
    @staticmethod
    def wrapped_mark_processed(ids):
        res = orig_mark_processed(ids)
        if ids:
            ReprocessMetrics.counters["signals_processed"] += len(ids)
            print_progress()
        return res
    MobileSignalRepository.mark_signals_processed = wrapped_mark_processed

    # 2. Saved Signals (from MobileSignalPipeline saving to SQLite signals table)
    orig_create_signal = SignalRepository.create_signal
    @staticmethod
    def wrapped_create_signal(*args, **kwargs):
        res = orig_create_signal(*args, **kwargs)
        ReprocessMetrics.counters["saved_signals"] += 1
        print_progress()
        return res
    SignalRepository.create_signal = wrapped_create_signal

    # 3. Cache Hits/Misses
    orig_cache_get = ClassificationCacheRepository.get
    @staticmethod
    def wrapped_cache_get(cache_key):
        res = orig_cache_get(cache_key)
        if res is not None:
            ReprocessMetrics.counters["cache_hits"] += 1
            ReprocessMetrics.counters["llm_calls_avoided"] += 1
            print_progress()
        else:
            ReprocessMetrics.counters["cache_misses"] += 1
            print_progress()
        return res
    ClassificationCacheRepository.get = wrapped_cache_get

    # 4. Pre-Classified Layer Match
    orig_pre_classify = MobileIntentExtractor._rule_based_pre_classify
    def wrapped_pre_classify(self, signal):
        res = orig_pre_classify(self, signal)
        if res is not None:
            ReprocessMetrics.counters["pre_classified"] += 1
            ReprocessMetrics.counters["llm_calls_avoided"] += 1
            print_progress()
        return res
    MobileIntentExtractor._rule_based_pre_classify = wrapped_pre_classify

    # 5. LLM calls executed (Router ask for TaskType.EMAIL)
    orig_router_ask = IntelligenceRouter.ask
    def wrapped_router_ask(self, prompt, task_type):
        if task_type == TaskType.EMAIL:
            ReprocessMetrics.counters["llm_calls_executed"] += 1
            print_progress()
        return orig_router_ask(self, prompt, task_type)
    IntelligenceRouter.ask = wrapped_router_ask

    # 6. Todos Created in Supabase
    orig_create_todo = SupabaseRepo.create_todo
    @classmethod
    def wrapped_create_todo(cls, *args, **kwargs):
        res = orig_create_todo(*args, **kwargs)
        if res:
            ReprocessMetrics.counters["todos_created"] += 1
            print_progress()
        return res
    SupabaseRepo.create_todo = wrapped_create_todo

    # 7. Financial Events Created in Supabase
    orig_create_financial_event = SupabaseRepo.create_financial_event
    @classmethod
    def wrapped_create_financial_event(cls, *args, **kwargs):
        res = orig_create_financial_event(*args, **kwargs)
        if res:
            ReprocessMetrics.counters["financial_events"] += 1
            print_progress()
        return res
    SupabaseRepo.create_financial_event = wrapped_create_financial_event

    # 8. FYI Events Created in Supabase
    orig_create_fyi_event = SupabaseRepo.create_fyi_event
    @classmethod
    def wrapped_create_fyi_event(cls, *args, **kwargs):
        res = orig_create_fyi_event(*args, **kwargs)
        if res:
            ReprocessMetrics.counters["fyi_events"] += 1
            print_progress()
        return res
    SupabaseRepo.create_fyi_event = wrapped_create_fyi_event

    # 9. Facts Created in Supabase
    orig_store_fact = SupabaseRepo.store_fact
    @classmethod
    def wrapped_store_fact(cls, *args, **kwargs):
        res = orig_store_fact(*args, **kwargs)
        if res:
            ReprocessMetrics.counters["facts_created"] += 1
            print_progress()
        return res
    SupabaseRepo.store_fact = wrapped_store_fact

def discover_files(client: SupabaseClient, folder_name: str) -> list[dict]:
    """Retrieves file list with metadata (name, size, timestamps) from Supabase."""
    import httpx
    url = f"{client.url}/storage/v1/object/list/{client.bucket}"
    prefix = f"{folder_name}/"
    payload = {
        "prefix": prefix,
        "limit": 1000,
        "sortBy": {
            "column": "name",
            "order": "asc"
        }
    }
    headers = {
        **client.headers,
        "Content-Type": "application/json"
    }

    try:
        logger.info(f"Retrieving raw list of files for metadata discovery under prefix '{prefix}'...")
        r = httpx.post(url, headers=headers, json=payload, timeout=30.0)
        if r.status_code != 200:
            logger.error(f"Failed to fetch file metadata. HTTP {r.status_code}: {r.text}")
            return []
        
        items = r.json()
        valid_items = []
        for item in items:
            name = item.get("name")
            if not name or name == ".emptyFolderPlaceholder":
                continue
            valid_items.append(item)
        return valid_items
    except Exception as e:
        logger.exception(f"Error during file discovery: {e}")
        ReprocessMetrics.counters["errors"] += 1
        return []

def main():
    start_time = time.time()
    
    logger.info("Initializing Jarvis system runtime context...")
    initialize_system()
    setup_decorators()

    # Step 1 - Discover Files
    folder_name = "pradeep"
    client = SupabaseClient()
    discovered = discover_files(client, folder_name)
    
    total_files = len(discovered)
    ReprocessMetrics.counters["files_found"] = total_files

    total_size = sum(item.get("metadata", {}).get("size") or item.get("size") or 0 for item in discovered)
    
    oldest_file = None
    latest_file = None
    oldest_time = None
    latest_time = None

    for item in discovered:
        name = item.get("name")
        created_at_str = item.get("created_at") or item.get("updated_at")
        if created_at_str:
            try:
                dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                if oldest_time is None or dt < oldest_time:
                    oldest_time = dt
                    oldest_file = f"{folder_name}/{name}"
                if latest_time is None or dt > latest_time:
                    latest_time = dt
                    latest_file = f"{folder_name}/{name}"
            except Exception:
                pass

    if oldest_file is None and discovered:
        sorted_by_name = sorted(discovered, key=lambda x: x.get("name", ""))
        oldest_file = f"{folder_name}/{sorted_by_name[0].get('name')}"
        latest_file = f"{folder_name}/{sorted_by_name[-1].get('name')}"

    print("\n" + "=" * 50)
    print("         HISTORICAL SIGNAL FILE DISCOVERY")
    print("=" * 50)
    print(f"Total Files Found     : {total_files}")
    print(f"Total Size            : {total_size:,} bytes")
    print(f"Oldest File           : {oldest_file or 'None'}")
    print(f"Latest File           : {latest_file or 'None'}")
    print("=" * 50 + "\n")
    sys.stdout.flush()

    if total_files == 0:
        logger.info("No files found to process. Exiting reprocessing script.")
        return

    # Keep track of files loaded to archive them at the end of processing
    loaded_files = []

    # Step 2 - Load & Ingest Unique Signals into mobile_signals landing table
    logger.info("Starting historical ingestion loader...")
    for idx, item in enumerate(discovered):
        name = item.get("name")
        file_path = f"{folder_name}/{name}"
        logger.info(f"Ingesting file {idx + 1}/{total_files}: {file_path}")

        try:
            content = client.download_file(file_path)
            if not content:
                logger.warning(f"File {file_path} content is empty. Skipping.")
                ReprocessMetrics.counters["files_processed"] += 1
                continue

            content_hash = hashlib.sha256(
                content.encode("utf-8") if isinstance(content, str) else content
            ).hexdigest()

            # Check if file has already been processed (deduplication)
            if ProcessedFileRepository.exists_path_or_hash(file_path, content_hash):
                logger.info(f"File {file_path} or hash already processed. Skipping.")
                ReprocessMetrics.counters["files_processed"] += 1
                continue

            signals = FileProcessor.parse_signals(content)
            # Keep only whatsapp and sms signals
            whatsapp_sms_signals = [s for s in signals if s.get("source") in ("whatsapp", "sms")]
            
            inserted_count = 0
            for sig in whatsapp_sms_signals:
                msg_hash = sig["message_hash"]
                if MobileSignalRepository.exists_hash(msg_hash):
                    continue

                MobileSignalRepository.save_signal(
                    device_id=sig["device_id"],
                    source=sig["source"],
                    sender=sig["sender"],
                    message=sig["message"],
                    timestamp=sig["timestamp"],
                    message_hash=msg_hash
                )
                inserted_count += 1

            logger.info(f"Loaded {inserted_count} new unique signals from {file_path}")
            loaded_files.append((file_path, name, content_hash))
            ReprocessMetrics.counters["files_processed"] += 1

        except Exception as e:
            logger.exception(f"Error ingesting file {file_path}: {e}")
            ReprocessMetrics.counters["errors"] += 1

    # Record run_start_time now that signals are loaded and processing begins
    ReprocessMetrics.run_start_time = time.time()

    # Step 3 & 4 - Pass raw landing data through optimized multi-threaded LLM & Extraction Pipelines
    logger.info("Entering LLM Signal Processing and Tagging...")
    pipeline = MobileSignalPipeline()
    
    # Initialize the total number of unprocessed signals to load
    db = SessionLocal()
    try:
        count = db.query(MobileSignal).filter(MobileSignal.processed == False).count()
        ReprocessMetrics.counters["signals_loaded"] = count
        logger.info(f"Loaded {count} unprocessed mobile signals to process from SQLite database.")
    finally:
        db.close()

    while True:
        db = SessionLocal()
        try:
            unprocessed_count = db.query(MobileSignal).filter(MobileSignal.processed == False).count()
            if unprocessed_count == 0:
                logger.info("All landing signals processed by LLM pipeline.")
                break
            logger.info(f"Running LLM pipeline batch: {unprocessed_count} unprocessed signals left...")
        finally:
            db.close()
        
        try:
            pipeline.run()
        except Exception as e:
            logger.exception(f"LLM pipeline batch execution failed: {e}")
            ReprocessMetrics.counters["errors"] += 1
            # Prevent infinite loop on persistent failure
            break

    # Run Classifications
    logger.info("Running signal categories classification...")
    try:
        classified = SignalProcessor.process_all_signals()
        logger.info(f"Classified {classified} signals.")
    except Exception as e:
        logger.exception(f"Classification failed: {e}")
        ReprocessMetrics.counters["errors"] += 1

    # Run Todos Extraction
    logger.info("Running TODO extraction pipeline...")
    try:
        todos = SignalProcessor.extract_todos()
        logger.info(f"Extracted {todos} TODOs.")
    except Exception as e:
        logger.exception(f"TODO extraction failed: {e}")
        ReprocessMetrics.counters["errors"] += 1

    # Run Financial Event Extraction
    logger.info("Running Financial Event extraction pipeline...")
    try:
        financials = SignalProcessor.extract_financial_events()
        logger.info(f"Extracted {financials} Financial Events.")
    except Exception as e:
        logger.exception(f"Financial Event extraction failed: {e}")
        ReprocessMetrics.counters["errors"] += 1

    # Run FYI Event Extraction
    logger.info("Running FYI Event extraction pipeline...")
    try:
        fyis = SignalProcessor.extract_fyi_events()
        logger.info(f"Extracted {fyis} FYI Events.")
    except Exception as e:
        logger.exception(f"FYI Event extraction failed: {e}")
        ReprocessMetrics.counters["errors"] += 1

    # Run Financial Aggregator Pipeline (aggregates transactions, updates mapping categories, summaries, trends)
    logger.info("Running Financial Aggregator spending rollups...")
    try:
        FinancialAggregator.run_aggregation()
        logger.success("Financial Aggregator aggregation complete.")
    except Exception as e:
        logger.exception(f"Financial Aggregator failed: {e}")
        ReprocessMetrics.counters["errors"] += 1

    # Step 5 - Clean up / remote archiving of successfully processed files
    logger.info("Archiving successfully processed files on Supabase Storage...")
    for file_path, filename, content_hash in loaded_files:
        try:
            dest_path = f"archive/{filename}"
            if client.move_file(file_path, dest_path):
                # Register in database registry to ensure they are marked processed
                ProcessedFileRepository.register_file(
                    file_name=filename,
                    bucket_name=client.bucket,
                    file_path=file_path,
                    file_hash=content_hash,
                    status="PROCESSED"
                )
                logger.info(f"Successfully archived file {file_path} to {dest_path}")
            else:
                logger.error(f"Failed to move file {file_path} to remote archive.")
                ReprocessMetrics.counters["errors"] += 1
        except Exception as e:
            logger.exception(f"Error archiving file {file_path}: {e}")
            ReprocessMetrics.counters["errors"] += 1

    # Display final progress and summary
    print_progress(force=True)
    elapsed_time = time.time() - start_time
    m, s = divmod(elapsed_time, 60)
    h, m = divmod(m, 60)

    print("\n" + "=" * 50)
    print("         Historical Processing Complete")
    print("=" * 50)
    print(f"Files Processed       : {ReprocessMetrics.counters['files_processed']}")
    print(f"Signals Loaded        : {ReprocessMetrics.counters['signals_loaded']}")
    print(f"Signals Processed     : {ReprocessMetrics.counters['signals_processed']}")
    print(f"Saved Signals         : {ReprocessMetrics.counters['saved_signals']}")
    print(f"Todos Created         : {ReprocessMetrics.counters['todos_created']}")
    print(f"Financial Events      : {ReprocessMetrics.counters['financial_events']}")
    print(f"FYI Events            : {ReprocessMetrics.counters['fyi_events']}")
    print(f"Facts Created         : {ReprocessMetrics.counters['facts_created']}")
    print(f"Elapsed Time          : {int(h):02d}:{int(m):02d}:{int(s):02d}")
    print("=" * 50 + "\n")
    sys.stdout.flush()

if __name__ == "__main__":
    main()
