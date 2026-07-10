import uuid
from datetime import datetime, timezone

def normalize_whatsapp_msg(msg: dict, chat_name: str, file_name: str, file_hash: str) -> dict:
    sender = msg.get("sender", "unknown")
    message_text = msg.get("message", "")
    timestamp_ms = msg.get("timestamp")
    
    if timestamp_ms:
        dt = datetime.fromtimestamp(timestamp_ms / 1000.0, tz=timezone.utc)
        source_event_time = dt.isoformat()
    else:
        source_event_time = datetime.now(timezone.utc).isoformat()
        
    signal_id = str(uuid.uuid4())
    
    return {
        "signal_id": signal_id,
        "source_type": "whatsapp",
        "source_subtype": "chat",
        "source_file_name": file_name,
        "source_file_hash": file_hash,
        "source_event_time": source_event_time,
        "source_ingested_at": datetime.now(timezone.utc).isoformat(),
        "sender": sender,
        "receiver": msg.get("receiver", "pprad"),
        "content": message_text,
        "metadata": {
            "chat_name": chat_name,
            "attachment_indicator": msg.get("attachment_indicator", False)
        }
    }
