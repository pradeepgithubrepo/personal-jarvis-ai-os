import uuid
import re
from src.agents.consumer.agent import ConsumerAgent
from src.agents.consumer.parsers.pdf_parser import parse_pdf
from src.agents.consumer.normalizers.financial_normalizer import normalize_financial_tx

def parse_sbi_text(text: str) -> list[dict]:
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    transactions = []
    
    start_idx = -1
    for idx, line in enumerate(lines):
        if "Balance" in line and ("STATEMENT OF ACCOUNT" in text or "Statement From" in text):
            start_idx = idx + 1
            break  # Fix: only use FIRST occurrence; multi-page headers kept overwriting this
            
    if start_idx == -1:
        start_idx = 0
        
    i = start_idx
    current_tx = None
    
    while i < len(lines):
        line = lines[i]
        
        if "Statement Summary" in line or "Brought Forward" in line or "Total Credits" in line:
            break
            
        date_match = re.match(r'^(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})(.*)$', line)
        if date_match:
            if current_tx:
                transactions.append(current_tx)
                
            post_date = date_match.group(1)
            value_date = date_match.group(2)
            rest = date_match.group(3).strip()
            
            current_tx = {
                "date": post_date,
                "value_date": value_date,
                "description_lines": [rest] if rest else [],
                "amount": 0.0,
                "transaction_type": "DEBIT",
                "balance": 0.0,
                "reference_number": ""
            }
            i += 1
        else:
            if current_tx:
                credit_match = re.match(r'^-\s+-\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s*(?:CR)?$', line)
                debit_match = re.match(r'^-\s+([\d,]+\.\d{2})\s+-\s+([\d,]+\.\d{2})\s*(?:CR)?$', line)
                
                if credit_match:
                    current_tx["amount"] = float(credit_match.group(1).replace(",", ""))
                    current_tx["balance"] = float(credit_match.group(2).replace(",", ""))
                    current_tx["transaction_type"] = "CREDIT"
                elif debit_match:
                    current_tx["amount"] = float(debit_match.group(1).replace(",", ""))
                    current_tx["balance"] = float(debit_match.group(2).replace(",", ""))
                    current_tx["transaction_type"] = "DEBIT"
                else:
                    current_tx["description_lines"].append(line)
            i += 1
            
    if current_tx:
        transactions.append(current_tx)
        
    for tx in transactions:
        desc = " ".join(tx["description_lines"]).strip()
        desc = re.sub(r'\d+Page no\.', '', desc).strip()
        desc = re.sub(r'Page no\.', '', desc).strip()
        tx["description"] = desc
        tx["counterparty"] = desc
        del tx["description_lines"]
        
        ref_match = re.search(r'(?:IMPS|UPI)/(\d+)', desc, re.IGNORECASE)
        if ref_match:
            tx["reference_number"] = ref_match.group(1)
        else:
            ref_match2 = re.search(r'\b(IY\d{20,22})\b', desc)
            if ref_match2:
                tx["reference_number"] = ref_match2.group(1)
            else:
                ref_match3 = re.search(r'\b(\d{12,15})\b', desc)
                if ref_match3:
                    tx["reference_number"] = ref_match3.group(1)
                    
    return transactions

def match_hdfc_line_end(line: str) -> dict | None:
    # Try three-amount format (Withdrawal, Deposit, Balance)
    three_match = re.search(
        r"(?:(\d{12})\s+)?"
        r"(\d{2}/\d{2}/\d{2,4})\s+"
        r"([\d,]+\.\d{2})\s+"
        r"([\d,]+\.\d{2})\s+"
        r"([\d,]+\.\d{2})(?:\s*CR)?$",
        line
    )
    if three_match:
        ref_num = three_match.group(1) or ""
        val_date = three_match.group(2)
        withdrawal = float(three_match.group(3).replace(",", ""))
        deposit = float(three_match.group(4).replace(",", ""))
        balance = float(three_match.group(5).replace(",", ""))
        
        tx_type = "DEBIT"
        amount = withdrawal
        if deposit > 0.0:
            tx_type = "CREDIT"
            amount = deposit
            
        return {
            "ref_number": ref_num,
            "value_date": val_date,
            "amount": amount,
            "balance": balance,
            "transaction_type": tx_type,
            "match_start": three_match.start()
        }
        
    # Try two-amount format (Amount, Balance)
    two_match = re.search(
        r"(?:(\d{12})\s+)?"
        r"(\d{2}/\d{2}/\d{2,4})\s+"
        r"([\d,]+\.\d{2})\s+"
        r"([\d,]+\.\d{2})(?:\s*CR)?$",
        line
    )
    if two_match:
        ref_num = two_match.group(1) or ""
        val_date = two_match.group(2)
        amount = float(two_match.group(3).replace(",", ""))
        balance = float(two_match.group(4).replace(",", ""))
        
        tx_type = "DEBIT"
        if "CR" in line or "CREDIT" in line.upper() or "DEP" in line.upper():
            tx_type = "CREDIT"
            
        return {
            "ref_number": ref_num,
            "value_date": val_date,
            "amount": amount,
            "balance": balance,
            "transaction_type": tx_type,
            "match_start": two_match.start()
        }
        
    return None

def parse_hdfc_text(text: str) -> list[dict]:
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    transactions = []
    current_tx = None
    
    for line in lines:
        date_match = re.match(r"^(\d{2}/\d{2}/\d{2,4})(?:\s+(.*))?$", line)
        if date_match:
            if current_tx:
                # Flush previous transaction
                transactions.append(current_tx)
                current_tx = None
                
            date_str = date_match.group(1)
            rest = date_match.group(2) or ""
            
            # Check if this line also contains the ending amount block (single-line transaction)
            end_data = match_hdfc_line_end(rest if rest else "")
            if end_data:
                narration = rest[:end_data["match_start"]].strip()
                transactions.append({
                    "date": date_str,
                    "value_date": end_data["value_date"],
                    "description": narration,
                    "counterparty": narration,
                    "transaction_type": end_data["transaction_type"],
                    "reference_number": end_data["ref_number"],
                    "amount": end_data["amount"],
                    "balance": end_data["balance"]
                })
            else:
                current_tx = {
                    "date": date_str,
                    "description_lines": [rest] if rest else [],
                    "ref_number": "",
                    "value_date": date_str,
                    "amount": 0.0,
                    "balance": 0.0,
                    "transaction_type": "DEBIT"
                }
        elif current_tx:
            end_data = match_hdfc_line_end(line)
            if end_data:
                prefix = line[:end_data["match_start"]].strip()
                if prefix:
                    current_tx["description_lines"].append(prefix)
                
                narration = " ".join(current_tx["description_lines"])
                transactions.append({
                    "date": current_tx["date"],
                    "value_date": end_data["value_date"],
                    "description": narration,
                    "counterparty": narration,
                    "transaction_type": end_data["transaction_type"],
                    "reference_number": end_data["ref_number"],
                    "amount": end_data["amount"],
                    "balance": end_data["balance"]
                })
                current_tx = None
            else:
                if any(x in line for x in ["Statement Summary", "Brought Forward", "Total Credits", "Total Debits", "HDFC BANK LIMITED"]):
                    current_tx = None
                else:
                    current_tx["description_lines"].append(line)
                    
    if current_tx:
        # Fallback flush
        narration = " ".join(current_tx["description_lines"])
        transactions.append({
            "date": current_tx["date"],
            "value_date": current_tx["value_date"],
            "description": narration,
            "counterparty": narration,
            "transaction_type": current_tx["transaction_type"],
            "reference_number": current_tx["ref_number"],
            "amount": current_tx["amount"],
            "balance": current_tx["balance"]
        })
        
    return transactions

def collect_bank_statement(client, run_id: uuid.UUID, bucket_name: str) -> dict:
    agent = ConsumerAgent(client)
    from_dir = "incoming/statements"
    to_dir = "archive/statements"
    
    agent.log_event(run_id, "INFO", "bank_statement_collector", "COLLECTOR_STARTED", "Bank statement collector started")
    
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
            agent.log_event(run_id, "INFO", "bank_statement_collector", "FILE_DISCOVERED", f"Discovered bank statement: {path}")
            
            try:
                data = agent.download_file(bucket_name, path)
            except Exception as e:
                metrics["files_failed"] += 1
                agent.log_event(run_id, "ERROR", "bank_statement_collector", "PARSER_ERROR", f"Failed to download {path}: {str(e)}")
                continue
                
            file_hash = agent.calculate_hash(data)
            if agent.check_duplicate(file_hash):
                metrics["files_skipped"] += 1
                agent.log_event(run_id, "INFO", "bank_statement_collector", "DUPLICATE_FILE", f"Skipping duplicate bank statement: {file_name}")
                try:
                    client.storage.from_(bucket_name).remove([path])
                except Exception:
                    pass
                continue
                
            try:
                parsed_doc = parse_pdf(data)
                agent.log_event(run_id, "INFO", "bank_statement_collector", "PDF_PARSED", f"Parsed PDF text for statement: {file_name}")
            except Exception as e:
                metrics["files_failed"] += 1
                agent.log_event(run_id, "ERROR", "bank_statement_collector", "PARSER_ERROR", f"Failed to parse PDF {file_name}: {str(e)}")
                try:
                    client.storage.from_(bucket_name).move(path, f"failed/statements/{file_name}")
                except Exception:
                    pass
                continue
                
            # Determine bank type (SBI or HDFC)
            is_sbi = "State Bank of India" in parsed_doc.text or "SBI" in parsed_doc.text
            is_hdfc = "HDFC BANK" in parsed_doc.text or "HDFC" in parsed_doc.text
            
            transactions = []
            if is_sbi:
                agent.log_event(run_id, "INFO", "bank_statement_collector", "JSON_PARSED", f"Identified SBI statement format for {file_name}")
                for page_text in parsed_doc.pages:
                    transactions.extend(parse_sbi_text(page_text))
            elif is_hdfc:
                agent.log_event(run_id, "INFO", "bank_statement_collector", "JSON_PARSED", f"Identified HDFC statement format for {file_name}")
                for page_text in parsed_doc.pages:
                    transactions.extend(parse_hdfc_text(page_text))
            else:
                metrics["files_failed"] += 1
                agent.log_event(run_id, "ERROR", "bank_statement_collector", "PARSER_ERROR", f"Unknown bank format in PDF {file_name}")
                try:
                    client.storage.from_(bucket_name).move(path, f"failed/statements/{file_name}")
                except Exception:
                    pass
                continue
                
            normalized_list = []
            for tx in transactions:
                normalized = normalize_financial_tx(tx, "bank_statement", file_name, file_hash)
                normalized_list.append(normalized)
                
            signals_created_file = agent.persist_signals_bulk(run_id, normalized_list)
            metrics["signals_created"] += signals_created_file
                    
            agent.log_event(run_id, "INFO", "bank_statement_collector", "SIGNALS_EXTRACTED", f"Extracted {signals_created_file} transactions from {file_name}")
            
            try:
                agent.archive_file(run_id, file_hash, file_name, "bank_statement", bucket_name, from_dir, to_dir)
                metrics["files_processed"] += 1
            except Exception as e:
                metrics["files_failed"] += 1
                agent.log_event(run_id, "ERROR", "bank_statement_collector", "PARSER_ERROR", f"Failed to archive bank statement {file_name}: {str(e)}")
                
        agent.log_event(run_id, "INFO", "bank_statement_collector", "COLLECTOR_COMPLETED", f"Bank statement collector completed: {metrics}")
    except Exception as e:
        agent.log_event(run_id, "ERROR", "bank_statement_collector", "PARSER_ERROR", f"Critical error in bank statement collector: {str(e)}")
        
    return metrics
