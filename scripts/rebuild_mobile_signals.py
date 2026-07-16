import os
import sys
import json
import uuid
import hashlib
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.consumer.normalizers.whatsapp_normalizer import normalize_whatsapp_msg
from src.agents.consumer.normalizers.sms_normalizer import normalize_sms_msg
from src.agents.consumer.normalizers.financial_normalizer import normalize_financial_tx
from src.agents.consumer.parsers.pdf_parser import parse_pdf
from src.agents.consumer.collectors.gpay_collector import parse_gpay_text
from src.agents.consumer.collectors.bank_statement_collector import parse_sbi_text, parse_hdfc_text
from src.agents.consumer.agent import ConsumerAgent

def clear_tables(client):
    print("Clearing tables in reverse dependency order...")
    # Delete signal_routes
    try:
        res = client.table("signal_routes").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        print(f"  Cleared signal_routes: {len(res.data) if res.data else 0} records")
    except Exception as e:
        print(f"  Warning clearing signal_routes: {e}")
        
    # Delete understood_signals
    try:
        res = client.table("understood_signals").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        print(f"  Cleared understood_signals: {len(res.data) if res.data else 0} records")
    except Exception as e:
        print(f"  Warning clearing understood_signals: {e}")
        
    # Delete qualified_signals
    try:
        res = client.table("qualified_signals").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        print(f"  Cleared qualified_signals: {len(res.data) if res.data else 0} records")
    except Exception as e:
        print(f"  Warning clearing qualified_signals: {e}")
        
    # Delete mobile_signals
    try:
        res = client.table("mobile_signals").delete().neq("id", -1).execute()
        print(f"  Cleared mobile_signals: {len(res.data) if res.data else 0} records")
    except Exception as e:
        print(f"  Warning clearing mobile_signals: {e}")
        
    # Delete processed_files
    try:
        res = client.table("processed_files").delete().neq("file_name", "nonexistent_placeholder_name").execute()
        print(f"  Cleared processed_files: {len(res.data) if res.data else 0} records")
    except Exception as e:
        print(f"  Warning clearing processed_files: {e}")
        
    print("Database tables cleared successfully.\n")

def main():
    load_dotenv()
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not supabase_key:
        print("Error: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set.")
        sys.exit(1)
        
    options = ClientOptions(schema="jarvis_insights_schemav1")
    client: Client = create_client(supabase_url, supabase_key, options=options)
    agent = ConsumerAgent(client)
    
    bucket_name = "jarvis-signals"
    
    # 1. Destructive Truncation
    clear_tables(client)
    
    # Create a run_id for this recovery run
    run_id = uuid.uuid4()
    started_at = datetime.now(timezone.utc).isoformat()
    
    # Register run in pipeline_runs
    client.table("pipeline_runs").insert({
        "run_id": str(run_id),
        "pipeline_name": "consumer_sync",
        "phase": "phase1b",
        "trigger_type": "RECOVERY",
        "started_at": started_at,
        "status": "STARTED",
        "host_name": "JarvisRecovery",
        "user_name": "prad",
        "version": "v2.0.0-recovery",
        "metadata": {"description": "Intentional DB rebuild from source files"}
    }).execute()
    
    # Define source folders
    folders = [
        # Incoming folders
        ("incoming", "legacy"),
        ("incoming/whatsapp", "whatsapp"),
        ("incoming/sms", "sms"),
        ("incoming/gpay", "gpay_pdf"),
        ("incoming/statements", "bank_statement_pdf"),
        
        # Archive folders
        ("archive", "legacy"),
        ("archive/whatsapp", "whatsapp"),
        ("archive/sms", "sms"),
        ("archive/gpay", "gpay_pdf"),
        ("archive/statements", "bank_statement_pdf")
    ]
    
    print("Discovering source files in storage bucket...")
    discovered_files = []
    for folder_path, default_source_type in folders:
        try:
            files = client.storage.from_(bucket_name).list(folder_path)
            for f in files:
                name = f.get("name")
                if not name or name == ".emptyFolderPlaceholder":
                    continue
                # Exclude folders
                is_dir = False
                if "metadata" not in f or f["metadata"] is None:
                    if not f.get("id"):
                        is_dir = True
                if is_dir:
                    continue
                    
                path = f"{folder_path}/{name}"
                discovered_files.append({
                    "folder": folder_path,
                    "name": name,
                    "path": path,
                    "default_source": default_source_type
                })
        except Exception as e:
            print(f"  Error listing {folder_path}: {e}")
            
    print(f"Discovered {len(discovered_files)} total files.\n")
    
    # Recovery Metrics
    metrics = {
        "total_files": len(discovered_files),
        "json_files": 0,
        "pdf_files": 0,
        "sms_signals": 0,
        "whatsapp_signals": 0,
        "gpay_signals": 0,
        "bank_statement_signals": 0,
        "skipped_files": 0,
        "failed_files": 0,
        "archive_files_recovered": 0,
        "dates": []
    }
    
    # Deduplicate by file path to prevent processing same file multiple times
    processed_paths = set()
    
    for file_info in discovered_files:
        path = file_info["path"]
        if path in processed_paths:
            continue
        processed_paths.add(path)
        
        name = file_info["name"]
        folder = file_info["folder"]
        
        print(f"Processing: {path} ...")
        
        # Check archive count
        if folder.startswith("archive"):
            metrics["archive_files_recovered"] += 1
            
        try:
            data = client.storage.from_(bucket_name).download(path)
        except Exception as e:
            print(f"  Failed to download: {e}")
            metrics["failed_files"] += 1
            continue
            
        file_hash = agent.calculate_hash(data)
        
        # Insert processed_files record first for tracking
        try:
            client.table("processed_files").upsert({
                "file_hash": file_hash,
                "file_name": name,
                "source_type": file_info["default_source"].replace("_pdf", ""),
                "first_seen_at": datetime.now(timezone.utc).isoformat(),
                "run_id": str(run_id)
            }).execute()
        except Exception as e:
            print(f"  Warning writing processed_files: {e}")
            
        # Check PDF vs JSON
        is_pdf = name.lower().endswith(".pdf")
        
        if is_pdf:
            metrics["pdf_files"] += 1
            try:
                parsed_doc = parse_pdf(data)
                pdf_text = parsed_doc.text
            except Exception as e:
                print(f"  Failed to parse PDF: {e}")
                metrics["failed_files"] += 1
                continue
                
            pdf_text_lower = pdf_text.lower()
            filename_lower = name.lower()
            
            is_gpay = "upitransactionid" in pdf_text_lower or "google pay" in pdf_text_lower or "gpay" in filename_lower
            is_hdfc = "hdfc bank" in pdf_text_lower
            is_sbi = "state bank of india" in pdf_text_lower
            
            if not is_gpay and not is_sbi and not is_hdfc:
                if "paid to" in pdf_text_lower or "received from" in pdf_text_lower:
                    is_gpay = True
                    
            if is_gpay:
                try:
                    transactions = []
                    for page_text in parsed_doc.pages:
                        transactions.extend(parse_gpay_text(page_text))
                    
                    normalized_list = []
                    for tx in transactions:
                        normalized = normalize_financial_tx(tx, "gpay", name, file_hash)
                        normalized_list.append(normalized)
                        if normalized.get("source_event_time"):
                            metrics["dates"].append(normalized["source_event_time"])
                            
                    signals_created = agent.persist_signals_bulk(run_id, normalized_list)
                    metrics["gpay_signals"] += signals_created
                    print(f"  Parsed as GPay PDF. Created {signals_created} signals.")
                except Exception as e:
                    print(f"  Error processing GPay PDF: {e}")
                    metrics["failed_files"] += 1
            elif is_sbi or is_hdfc:
                try:
                    transactions = []
                    if is_sbi:
                        for page_text in parsed_doc.pages:
                            transactions.extend(parse_sbi_text(page_text))
                    else:
                        for page_text in parsed_doc.pages:
                            transactions.extend(parse_hdfc_text(page_text))
                            
                    normalized_list = []
                    for tx in transactions:
                        normalized = normalize_financial_tx(tx, "bank_statement", name, file_hash)
                        normalized_list.append(normalized)
                        if normalized.get("source_event_time"):
                            metrics["dates"].append(normalized["source_event_time"])
                            
                    signals_created = agent.persist_signals_bulk(run_id, normalized_list)
                    metrics["bank_statement_signals"] += signals_created
                    print(f"  Parsed as Bank Statement PDF ({'SBI' if is_sbi else 'HDFC'}). Created {signals_created} signals.")
                except Exception as e:
                    print(f"  Error processing Bank Statement PDF: {e}")
                    metrics["failed_files"] += 1
            else:
                print(f"  Unknown PDF layout. Skipped.")
                metrics["skipped_files"] += 1
                
        else:
            # JSON format
            metrics["json_files"] += 1
            try:
                content = json.loads(data.decode("utf-8"))
            except Exception as e:
                print(f"  Failed to parse JSON: {e}")
                metrics["failed_files"] += 1
                continue
                
            if "signals" in content:
                # Legacy root folder format
                try:
                    signals = content.get("signals", [])
                    for sig in signals:
                        sig["source_file_name"] = name
                        # Preserve event timestamp for date coverage checks
                        timestamp_ms = sig.get("timestamp")
                        if timestamp_ms:
                            dt = datetime.fromtimestamp(timestamp_ms / 1000.0, tz=timezone.utc)
                            metrics["dates"].append(dt.isoformat())
                            
                    signals_created = agent.persist_signals_bulk(run_id, signals)
                    # Classify based on legacy source field if possible
                    for sig in signals:
                        source = str(sig.get("source", "")).lower()
                        if "whatsapp" in source:
                            metrics["whatsapp_signals"] += 1
                        elif "sms" in source:
                            metrics["sms_signals"] += 1
                        else:
                            metrics["sms_signals"] += 1  # default fallback
                    print(f"  Parsed as Legacy Root JSON. Created {signals_created} signals.")
                except Exception as e:
                    print(f"  Error processing Legacy JSON: {e}")
                    metrics["failed_files"] += 1
            elif "messages" in content:
                if "chat_name" in content:
                    # WhatsApp JSON
                    try:
                        chat_name = content.get("chat_name", "unknown")
                        messages = content.get("messages", [])
                        normalized_list = []
                        for msg in messages:
                            normalized = normalize_whatsapp_msg(msg, chat_name, name, file_hash)
                            normalized_list.append(normalized)
                            if normalized.get("source_event_time"):
                                metrics["dates"].append(normalized["source_event_time"])
                                
                        signals_created = agent.persist_signals_bulk(run_id, normalized_list)
                        metrics["whatsapp_signals"] += signals_created
                        print(f"  Parsed as WhatsApp JSON. Created {signals_created} signals.")
                    except Exception as e:
                        print(f"  Error processing WhatsApp JSON: {e}")
                        metrics["failed_files"] += 1
                else:
                    # SMS JSON
                    try:
                        messages = content.get("messages", [])
                        normalized_list = []
                        for msg in messages:
                            normalized = normalize_sms_msg(msg, name, file_hash)
                            normalized_list.append(normalized)
                            if normalized.get("source_event_time"):
                                metrics["dates"].append(normalized["source_event_time"])
                                
                        signals_created = agent.persist_signals_bulk(run_id, normalized_list)
                        metrics["sms_signals"] += signals_created
                        print(f"  Parsed as SMS JSON. Created {signals_created} signals.")
                    except Exception as e:
                        print(f"  Error processing SMS JSON: {e}")
                        metrics["failed_files"] += 1
            else:
                print(f"  Unknown JSON structure (neither signals nor messages found). Skipped.")
                metrics["skipped_files"] += 1
                    
    # Calculate date coverage
    min_date = "N/A"
    max_date = "N/A"
    if metrics["dates"]:
        parsed_dates = []
        for d in metrics["dates"]:
            try:
                # Remove Z and take first 19 chars for sorting
                clean_d = d.replace("Z", "").split("+")[0]
                parsed_dates.append(datetime.fromisoformat(clean_d))
            except Exception:
                pass
        if parsed_dates:
            min_date = min(parsed_dates).strftime("%Y-%m-%d %H:%M:%S UTC")
            max_date = max(parsed_dates).strftime("%Y-%m-%d %H:%M:%S UTC")
            
    # Mark run complete
    client.table("pipeline_runs").update({
        "status": "SUCCESS",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "duration_ms": 0,
        "files_found": metrics["total_files"],
        "files_processed": metrics["total_files"] - metrics["skipped_files"] - metrics["failed_files"],
        "files_skipped": metrics["skipped_files"],
        "files_failed": metrics["failed_files"],
        "signals_created": metrics["sms_signals"] + metrics["whatsapp_signals"] + metrics["gpay_signals"] + metrics["bank_statement_signals"]
    }).eq("run_id", str(run_id)).execute()
    
    # Output the report block
    print("\n" + "="*50)
    print("MOBILE_SIGNALS_RECOVERY_SUMMARY")
    print("="*50)
    print(f"Total Files Processed: {metrics['total_files']}")
    print(f"JSON Files Processed: {metrics['json_files']}")
    print(f"PDF Files Processed: {metrics['pdf_files']}")
    print(f"SMS Signals Created: {metrics['sms_signals']}")
    print(f"WhatsApp Signals Created: {metrics['whatsapp_signals']}")
    print(f"GPay Transactions Created: {metrics['gpay_signals']}")
    print(f"Bank Statement Transactions Created: {metrics['bank_statement_signals']}")
    print(f"Skipped Files: {metrics['skipped_files']}")
    print(f"Failed Files: {metrics['failed_files']}")
    print(f"Archive Files Recovered: {metrics['archive_files_recovered']}")
    print(f"Date Coverage: {min_date} to {max_date}")
    print("="*50)

if __name__ == "__main__":
    main()
