import uuid
from datetime import datetime, timezone

def normalize_financial_tx(tx: dict, source_subtype: str, file_name: str, file_hash: str) -> dict:
    date_str = tx.get("date", "")
    time_str = tx.get("time", "")
    
    dt = None
    if source_subtype == "gpay":
        try:
            # Format: "02 Apr, 2026 08:39AM"
            dt_str = f"{date_str.strip()} {time_str.strip()}"
            dt = datetime.strptime(dt_str, "%d %b, %Y %I:%M%p")
            dt = dt.replace(tzinfo=timezone.utc)
        except Exception:
            try:
                # Try fallback format if no time is provided
                dt = datetime.strptime(date_str.strip(), "%d %b, %Y")
                dt = dt.replace(tzinfo=timezone.utc)
            except Exception:
                pass
    elif source_subtype == "bank_statement":
        try:
            # Format: "04/04/2026"
            dt = datetime.strptime(date_str.strip(), "%d/%m/%Y")
            dt = dt.replace(tzinfo=timezone.utc)
        except Exception:
            try:
                # Try fallback "dd/mm/yy" format
                dt = datetime.strptime(date_str.strip(), "%d/%m/%y")
                dt = dt.replace(tzinfo=timezone.utc)
            except Exception:
                pass
            
    if dt is None:
        dt = datetime.now(timezone.utc)
        
    source_event_time = dt.isoformat()
    signal_id = str(uuid.uuid4())
    
    fin_tx = {
        "transaction_date": source_event_time,
        "amount": tx.get("amount", 0.0),
        "currency": "INR",
        "transaction_type": tx.get("transaction_type", "DEBIT"),
        "description": tx.get("description", tx.get("details", "")),
        "reference_number": tx.get("reference_number", ""),
        "counterparty": tx.get("counterparty", "")
    }
    
    sender = tx.get("counterparty", "unknown")
    receiver = "pprad"
    if tx.get("transaction_type") == "DEBIT":
        sender = "pprad"
        receiver = tx.get("counterparty", "unknown")
        
    return {
        "signal_id": signal_id,
        "source_type": "financial",
        "source_subtype": source_subtype,
        "source_file_name": file_name,
        "source_file_hash": file_hash,
        "source_event_time": source_event_time,
        "source_ingested_at": datetime.now(timezone.utc).isoformat(),
        "sender": sender,
        "receiver": receiver,
        "content": tx.get("description", tx.get("details", "")),
        "metadata": fin_tx
    }
