import uuid
import re
from src.agents.consumer.agent import ConsumerAgent
from src.agents.consumer.parsers.pdf_parser import parse_pdf
from src.agents.consumer.normalizers.financial_normalizer import normalize_financial_tx

def parse_gpay_text(text: str) -> list[dict]:
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    transactions = []
    
    i = 0
    while i < len(lines):
        # Match date: e.g. "02 Apr, 2026"
        if re.match(r'^\d{2}\s+[A-Za-z]{3},\s+\d{4}$', lines[i]):
            date_str = lines[i]
            time_str = ""
            details = ""
            tx_id = ""
            paid_by = ""
            amount_str = ""
            
            i += 1
            if i < len(lines) and re.match(r'^\d{2}:\d{2}\s*[AP]M$', lines[i]):
                time_str = lines[i]
                i += 1
                
            if i < len(lines) and (lines[i].startswith("Paid to") or lines[i].startswith("Received from") or lines[i].startswith("Self transfer to")):
                details = lines[i]
                i += 1
                
            if i < len(lines) and lines[i].startswith("UPITransactionID:"):
                tx_id = lines[i].replace("UPITransactionID:", "").strip()
                i += 1
                
            if i < len(lines) and (lines[i].startswith("Paidby") or lines[i].startswith("Paidto") or lines[i].startswith("Receivedby")):
                paid_by = lines[i]
                i += 1
                
            if i < len(lines) and lines[i].startswith("₹"):
                amount_str = lines[i].replace("₹", "").replace(",", "").strip()
                i += 1
                
            if details and amount_str:
                try:
                    amount = float(amount_str)
                except ValueError:
                    amount = 0.0
                    
                tx_type = "DEBIT"
                counterparty = details
                if details.startswith("Paid to"):
                    tx_type = "DEBIT"
                    counterparty = details.replace("Paid to", "").strip()
                elif details.startswith("Received from"):
                    tx_type = "CREDIT"
                    counterparty = details.replace("Received from", "").strip()
                elif details.startswith("Self transfer to"):
                    tx_type = "DEBIT"
                    counterparty = details.replace("Self transfer to", "").strip()
                
                transactions.append({
                    "date": date_str,
                    "time": time_str,
                    "description": details,
                    "counterparty": counterparty,
                    "transaction_type": tx_type,
                    "reference_number": tx_id,
                    "payment_method": paid_by,
                    "amount": amount
                })
        else:
            i += 1
            
    return transactions

def collect_gpay(client, run_id: uuid.UUID, bucket_name: str) -> dict:
    agent = ConsumerAgent(client)
    from_dir = "incoming/gpay"
    to_dir = "archive/gpay"
    
    agent.log_event(run_id, "INFO", "gpay_collector", "COLLECTOR_STARTED", "GPay collector started")
    
    metrics = {
        "files_processed": 0,
        "files_skipped": 0,
        "files_failed": 0,
        "signals_created": 0
    }
    
    try:
        files = agent.discover_files(bucket_name, from_dir)
        for file_name in files:
            path = f"{from_dir}/{file_name}"
            agent.log_event(run_id, "INFO", "gpay_collector", "FILE_DISCOVERED", f"Discovered GPay file: {path}")
            
            try:
                data = agent.download_file(bucket_name, path)
            except Exception as e:
                metrics["files_failed"] += 1
                agent.log_event(run_id, "ERROR", "gpay_collector", "PARSER_ERROR", f"Failed to download {path}: {str(e)}")
                continue
                
            file_hash = agent.calculate_hash(data)
            if agent.check_duplicate(file_hash):
                metrics["files_skipped"] += 1
                agent.log_event(run_id, "INFO", "gpay_collector", "DUPLICATE_FILE", f"Skipping duplicate GPay file: {file_name}")
                try:
                    client.storage.from_(bucket_name).remove([path])
                except Exception:
                    pass
                continue
                
            try:
                parsed_doc = parse_pdf(data)
                agent.log_event(run_id, "INFO", "gpay_collector", "PDF_PARSED", f"Parsed PDF text for: {file_name}")
            except Exception as e:
                metrics["files_failed"] += 1
                agent.log_event(run_id, "ERROR", "gpay_collector", "PARSER_ERROR", f"Failed to parse PDF {file_name}: {str(e)}")
                try:
                    client.storage.from_(bucket_name).move(path, f"failed/gpay/{file_name}")
                except Exception:
                    pass
                continue
                
            # Parse GPay transactions from PDF text pages
            transactions = []
            for idx, page_text in enumerate(parsed_doc.pages):
                txs = parse_gpay_text(page_text)
                transactions.extend(txs)
                
            normalized_list = []
            for tx in transactions:
                normalized = normalize_financial_tx(tx, "gpay", file_name, file_hash)
                normalized_list.append(normalized)
                
            signals_created_file = agent.persist_signals_bulk(run_id, normalized_list)
            metrics["signals_created"] += signals_created_file
                    
            agent.log_event(run_id, "INFO", "gpay_collector", "SIGNALS_EXTRACTED", f"Extracted {signals_created_file} transactions from {file_name}")
            
            try:
                agent.archive_file(run_id, file_hash, file_name, "gpay", bucket_name, from_dir, to_dir)
                metrics["files_processed"] += 1
            except Exception as e:
                metrics["files_failed"] += 1
                agent.log_event(run_id, "ERROR", "gpay_collector", "PARSER_ERROR", f"Failed to archive GPay file {file_name}: {str(e)}")
                
        agent.log_event(run_id, "INFO", "gpay_collector", "COLLECTOR_COMPLETED", f"GPay collector completed: {metrics}")
    except Exception as e:
        agent.log_event(run_id, "ERROR", "gpay_collector", "PARSER_ERROR", f"Critical error in GPay collector: {str(e)}")
        
    return metrics
