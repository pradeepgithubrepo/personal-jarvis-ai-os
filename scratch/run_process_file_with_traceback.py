import os
import sys
import traceback
import dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
dotenv.load_dotenv(".env")

from services.system_initializer import initialize_system
from consumer.consumer_service import ConsumerService

def main():
    initialize_system()
    service = ConsumerService()
    files = service.supabase_client.list_files("incoming")
    if not files:
        print("No files found!")
        return
        
    target_file = files[0]
    print(f"Tracing processing of: {target_file}")
    
    # Let's run the steps of _process_file manually so we see the traceback
    file_path = target_file
    filename = file_path.split("/")[-1]
    bucket_name = service.supabase_client.bucket
    
    content = service.supabase_client.download_file(file_path)
    import hashlib
    content_hash = hashlib.sha256(
        content.encode("utf-8") if isinstance(content, str) else content
    ).hexdigest()
    
    from storage.repositories.processed_file_repository import ProcessedFileRepository
    if ProcessedFileRepository.exists_path_or_hash(file_path, content_hash):
        print("Already processed.")
        return
        
    from services.ingestion_service import IngestionService
    source_type = "whatsapp" if "whatsapp" in filename.lower() else "sms"
    batch_id = IngestionService.create_batch(
        source_type=source_type,
        source_name=f"File Ingestion: {filename}",
        file_name=filename,
        file_hash=content_hash
    )
    
    from consumer.file_processor import FileProcessor
    signals = FileProcessor.parse_signals(content)
    
    print(f"Signals parsed: {len(signals)}")
    if not signals:
        print("No signals found.")
        return
        
    from storage.repositories.mobile_signal_repository import MobileSignalRepository
    inserted_count = 0
    skipped_count = 0
    
    for signal in signals:
        msg_hash = signal["message_hash"]
        if MobileSignalRepository.exists_hash(msg_hash):
            skipped_count += 1
            continue
        
        MobileSignalRepository.save_signal(
            device_id=signal["device_id"],
            source=signal["source"],
            sender=signal["sender"],
            message=signal["message"],
            timestamp=signal["timestamp"],
            message_hash=msg_hash,
            batch_id=batch_id
        )
        inserted_count += 1
        
    print(f"Inserted: {inserted_count}, Skipped: {skipped_count}")
    
    archived = service.archive_manager.archive_file(file_path, content)
    print(f"Archived locally: {archived}")
    
    registered = ProcessedFileRepository.register_file(
        file_name=filename,
        bucket_name=bucket_name,
        file_path=file_path,
        file_hash=content_hash,
        status="PROCESSED"
    )
    print(f"Registered: {registered}")
    
    dest_path = f"archive/{filename}"
    moved = service.supabase_client.move_file(file_path, dest_path)
    print(f"Moved: {moved}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        traceback.print_exc()
