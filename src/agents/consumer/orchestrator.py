import json
import time
from datetime import datetime, timezone
import uuid
from supabase import Client
from src.agents.consumer.agent import ConsumerAgent

from src.agents.consumer.collectors.whatsapp_collector import collect_whatsapp
from src.agents.consumer.collectors.sms_collector import collect_sms
from src.agents.consumer.parsers.pdf_parser import parse_pdf
from src.agents.consumer.collectors.gpay_collector import parse_gpay_text
from src.agents.consumer.collectors.bank_statement_collector import parse_sbi_text, parse_hdfc_text
from src.agents.consumer.normalizers.financial_normalizer import normalize_financial_tx

def process_pdf_files(client, run_id: uuid.UUID, bucket_name: str) -> dict:
    agent = ConsumerAgent(client)
    folders = ["incoming", "incoming/statements", "incoming/gpay"]
    
    metrics = {
        "files_processed": 0,
        "files_skipped": 0,
        "files_failed": 0,
        "signals_created": 0
    }
    
    discovered_files = []
    for folder in folders:
        try:
            files = agent.discover_files(bucket_name, folder)
            for f in files:
                if f.lower().endswith(".pdf"):
                    discovered_files.append((folder, f))
        except Exception as e:
            agent.log_event(
                run_id=run_id,
                severity="ERROR",
                component="consumer_agent",
                event_type="FOLDER_DISCOVERY_FAILED",
                message=f"Failed to discover PDFs in {folder}: {str(e)}"
            )
            
    for from_dir, file_name in discovered_files:
        path = f"{from_dir}/{file_name}"
        agent.log_event(
            run_id=run_id,
            severity="INFO",
            component="consumer_agent",
            event_type="FILE_DISCOVERED",
            message=f"Discovered PDF file: {path}"
        )
        
        try:
            data = agent.download_file(bucket_name, path)
        except Exception as e:
            metrics["files_failed"] += 1
            agent.log_event(
                run_id=run_id,
                severity="ERROR",
                component="consumer_agent",
                event_type="FILE_DOWNLOAD_FAILED",
                message=f"Failed to download {path}: {str(e)}"
            )
            continue
            
        file_hash = agent.calculate_hash(data)
        if agent.check_duplicate(file_hash):
            metrics["files_skipped"] += 1
            agent.log_event(
                run_id=run_id,
                severity="INFO",
                component="consumer_agent",
                event_type="DUPLICATE_FILE",
                message=f"Skipping duplicate PDF file: {file_name}"
            )
            try:
                client.storage.from_(bucket_name).remove([path])
            except Exception:
                pass
            continue
            
        try:
            parsed_doc = parse_pdf(data)
            pdf_text = parsed_doc.text
        except Exception as e:
            metrics["files_failed"] += 1
            agent.log_event(
                run_id=run_id,
                severity="ERROR",
                component="consumer_agent",
                event_type="FILE_PARSE_FAILED",
                message=f"Failed to parse PDF {file_name}: {str(e)}"
            )
            try:
                client.storage.from_(bucket_name).move(path, f"failed/statements/{file_name}")
            except Exception:
                pass
            continue
            
        pdf_text_lower = pdf_text.lower()
        filename_lower = file_name.lower()
        
        is_gpay = "upitransactionid" in pdf_text_lower or "google pay" in pdf_text_lower or "gpay" in filename_lower
        is_hdfc = "hdfc bank" in pdf_text_lower
        is_sbi = "state bank of india" in pdf_text_lower
        
        if not is_gpay and not is_sbi and not is_hdfc:
            if "paid to" in pdf_text_lower or "received from" in pdf_text_lower:
                is_gpay = True
                
        if is_gpay:
            source_type = "gpay"
            to_dir = "archive/gpay"
        elif is_sbi or is_hdfc:
            source_type = "bank_statement"
            to_dir = "archive/statements"
        else:
            metrics["files_failed"] += 1
            agent.log_event(
                run_id=run_id,
                severity="ERROR",
                component="consumer_agent",
                event_type="UNKNOWN_PDF_FORMAT",
                message=f"Unknown bank or GPay format in PDF {file_name}"
            )
            try:
                client.storage.from_(bucket_name).move(path, f"failed/statements/{file_name}")
            except Exception:
                pass
            continue
            
        agent.log_event(
            run_id=run_id,
            severity="INFO",
            component="consumer_agent",
            event_type="PDF_IDENTIFIED",
            message=f"Identified PDF format for {file_name} as: {source_type}"
        )
        
        try:
            transactions = []
            if is_gpay:
                for page_text in parsed_doc.pages:
                    transactions.extend(parse_gpay_text(page_text))
            elif is_sbi:
                for page_text in parsed_doc.pages:
                    transactions.extend(parse_sbi_text(page_text))
            elif is_hdfc:
                for page_text in parsed_doc.pages:
                    transactions.extend(parse_hdfc_text(page_text))
                    
            normalized_list = []
            for tx in transactions:
                normalized = normalize_financial_tx(tx, source_type, file_name, file_hash)
                normalized_list.append(normalized)
                
            signals_created_file = agent.persist_signals_bulk(run_id, normalized_list)
            metrics["signals_created"] += signals_created_file
            
            agent.log_event(
                run_id=run_id,
                severity="INFO",
                component="consumer_agent",
                event_type="SIGNALS_EXTRACTED",
                message=f"Extracted {signals_created_file} transactions from {file_name}"
            )
            
            try:
                agent.archive_file(run_id, file_hash, file_name, source_type, bucket_name, from_dir, to_dir)
                metrics["files_processed"] += 1
            except Exception as e:
                metrics["files_failed"] += 1
                agent.log_event(
                    run_id=run_id,
                    severity="ERROR",
                    component="consumer_agent",
                    event_type="FILE_ARCHIVE_FAILED",
                    message=f"Failed to archive file {file_name}: {str(e)}"
                )
        except Exception as e:
            metrics["files_failed"] += 1
            agent.log_event(
                run_id=run_id,
                severity="ERROR",
                component="consumer_agent",
                event_type="PDF_PROCESSING_FAILED",
                message=f"Error processing {file_name}: {str(e)}"
            )
            
    return metrics

def run_pipeline(client: Client, trigger_type: str = "MANUAL") -> dict:
    agent = ConsumerAgent(client)
    started_at = datetime.now(timezone.utc)
    
    try:
        run_id = agent.start_run(
            pipeline_name="consumer_sync",
            phase="phase1b",
            trigger_type=trigger_type
        )
    except Exception as e:
        print(f"Error starting pipeline run: {e}")
        return {
            "status": "FAILED",
            "error_message": f"Could not connect to Supabase to start run: {str(e)}",
            "files_found": 0,
            "files_processed": 0,
            "files_skipped": 0,
            "files_failed": 0,
            "signals_created": 0,
            "duration_ms": 0
        }

    metrics = {
        "status": "SUCCESS",
        "files_found": 0,
        "files_processed": 0,
        "files_skipped": 0,
        "files_failed": 0,
        "signals_created": 0,
        "duration_ms": 0
    }
    
    bucket_name = "jarvis-signals"
    
    try:
        m_wa = collect_whatsapp(client, run_id, bucket_name)
        m_sms = collect_sms(client, run_id, bucket_name)
        m_pdf = process_pdf_files(client, run_id, bucket_name)
        
        root_folder = "incoming"
        root_files = agent.discover_files(bucket_name, root_folder)
        
        for name in root_files:
            if name in ["whatsapp", "sms", "gpay", "statements", "failed", "archive", "daily_briefs"]:
                continue
            if not name.endswith(".json"):
                continue
                
            path = f"{root_folder}/{name}"
            agent.log_event(
                run_id=run_id,
                severity="INFO",
                component="consumer_agent",
                event_type="FILE_DISCOVERED",
                message=f"Discovered root file: {path}"
            )
            
            try:
                data = agent.download_file(bucket_name, path)
            except Exception as e:
                metrics["files_failed"] += 1
                agent.log_event(
                    run_id=run_id,
                    severity="ERROR",
                    component="consumer_agent",
                    event_type="FILE_DOWNLOAD_FAILED",
                    message=f"Failed to download {path}: {str(e)}"
                )
                continue
                
            file_hash = agent.calculate_hash(data)
            if agent.check_duplicate(file_hash):
                metrics["files_skipped"] += 1
                agent.log_event(
                    run_id=run_id,
                    severity="INFO",
                    component="consumer_agent",
                    event_type="DUPLICATE_FILE",
                    message=f"Duplicate file skipped: {name}"
                )
                try:
                    client.storage.from_(bucket_name).remove([path])
                except Exception:
                    pass
                continue
                
            try:
                content = json.loads(data.decode("utf-8"))
                signals = content.get("signals", [])
                for sig in signals:
                    sig["source_file_name"] = name
            except Exception as e:
                metrics["files_failed"] += 1
                agent.log_event(
                    run_id=run_id,
                    severity="ERROR",
                    component="consumer_agent",
                    event_type="FILE_PARSE_FAILED",
                    message=f"Failed to parse JSON file {name}: {str(e)}"
                )
                try:
                    client.storage.from_(bucket_name).move(path, f"failed/{name}")
                except Exception:
                    pass
                continue
                
            signals_created_file = agent.persist_signals_bulk(run_id, signals)
            metrics["signals_created"] += signals_created_file
                    
            try:
                agent.archive_file(run_id, file_hash, name, "legacy", bucket_name, root_folder, "archive")
                metrics["files_processed"] += 1
            except Exception as e:
                metrics["files_failed"] += 1
                agent.log_event(
                    run_id=run_id,
                    severity="ERROR",
                    component="consumer_agent",
                    event_type="FILE_ARCHIVE_FAILED",
                    message=f"Failed to archive file {name}: {str(e)}"
                )
                
        metrics["files_processed"] += m_wa["files_processed"] + m_sms["files_processed"] + m_pdf["files_processed"]
        metrics["files_skipped"] += m_wa["files_skipped"] + m_sms["files_skipped"] + m_pdf["files_skipped"]
        metrics["files_failed"] += m_wa["files_failed"] + m_sms["files_failed"] + m_pdf["files_failed"]
        metrics["signals_created"] += m_wa["signals_created"] + m_sms["signals_created"] + m_pdf["signals_created"]
        metrics["files_found"] = metrics["files_processed"] + metrics["files_skipped"] + metrics["files_failed"]
        
        if metrics["files_failed"] > 0:
            if metrics["files_processed"] > 0 or metrics["files_skipped"] > 0:
                metrics["status"] = "PARTIAL_SUCCESS"
            else:
                metrics["status"] = "FAILED"
        else:
            metrics["status"] = "SUCCESS"
            
        metrics["duration_ms"] = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
        agent.complete_run(run_id, metrics)
        
    except Exception as e:
        metrics["status"] = "FAILED"
        agent.fail_run(run_id, str(e), started_at)
        
    return metrics
