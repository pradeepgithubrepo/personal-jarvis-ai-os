import uuid
from src.agents.consumer.agent import ConsumerAgent
from src.agents.consumer.parsers.whatsapp_parser import parse_whatsapp
from src.agents.consumer.normalizers.whatsapp_normalizer import normalize_whatsapp_msg

def collect_whatsapp(client, run_id: uuid.UUID, bucket_name: str) -> dict:
    agent = ConsumerAgent(client)
    from_dir = "incoming/whatsapp"
    to_dir = "archive/whatsapp"
    
    agent.log_event(run_id, "INFO", "whatsapp_collector", "COLLECTOR_STARTED", "WhatsApp collector started")
    
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
            agent.log_event(run_id, "INFO", "whatsapp_collector", "FILE_DISCOVERED", f"Discovered WhatsApp file: {path}")
            
            try:
                data = agent.download_file(bucket_name, path)
            except Exception as e:
                metrics["files_failed"] += 1
                agent.log_event(run_id, "ERROR", "whatsapp_collector", "PARSER_ERROR", f"Failed to download {path}: {str(e)}")
                continue
                
            file_hash = agent.calculate_hash(data)
            if agent.check_duplicate(file_hash):
                metrics["files_skipped"] += 1
                agent.log_event(run_id, "INFO", "whatsapp_collector", "DUPLICATE_FILE", f"Skipping duplicate WhatsApp file: {file_name}")
                try:
                    client.storage.from_(bucket_name).remove([path])
                except Exception:
                    pass
                continue
                
            try:
                content = parse_whatsapp(data)
                agent.log_event(run_id, "INFO", "whatsapp_collector", "JSON_PARSED", f"Parsed WhatsApp JSON: {file_name}")
            except Exception as e:
                metrics["files_failed"] += 1
                agent.log_event(run_id, "ERROR", "whatsapp_collector", "PARSER_ERROR", f"Failed to parse WhatsApp JSON {file_name}: {str(e)}")
                try:
                    client.storage.from_(bucket_name).move(path, f"failed/whatsapp/{file_name}")
                except Exception:
                    pass
                continue
                
            chat_name = content.get("chat_name", "unknown")
            messages = content.get("messages", [])
            
            normalized_list = []
            for msg in messages:
                normalized = normalize_whatsapp_msg(msg, chat_name, file_name, file_hash)
                normalized_list.append(normalized)
                
            signals_created_file = agent.persist_signals_bulk(run_id, normalized_list)
            metrics["signals_created"] += signals_created_file
                    
            agent.log_event(run_id, "INFO", "whatsapp_collector", "SIGNALS_EXTRACTED", f"Extracted {signals_created_file} signals from {file_name}")
            
            try:
                agent.archive_file(run_id, file_hash, file_name, "whatsapp", bucket_name, from_dir, to_dir)
                metrics["files_processed"] += 1
            except Exception as e:
                metrics["files_failed"] += 1
                agent.log_event(run_id, "ERROR", "whatsapp_collector", "PARSER_ERROR", f"Failed to archive WhatsApp file {file_name}: {str(e)}")
                
        agent.log_event(run_id, "INFO", "whatsapp_collector", "COLLECTOR_COMPLETED", f"WhatsApp collector completed: {metrics}")
    except Exception as e:
        agent.log_event(run_id, "ERROR", "whatsapp_collector", "PARSER_ERROR", f"Critical error in WhatsApp collector: {str(e)}")
        
    return metrics
