# consumer/consumer_service.py

import hashlib
from loguru import logger
from consumer.supabase_client import SupabaseClient
from consumer.file_processor import FileProcessor
from consumer.archive_manager import ArchiveManager
from storage.repositories.mobile_signal_repository import MobileSignalRepository
from storage.repositories.processed_file_repository import ProcessedFileRepository


class ConsumerService:

    def __init__(self):
        self.supabase_client = SupabaseClient()
        self.archive_manager = ArchiveManager()
        # The folders to scan on Supabase Storage
        self.folders = ["pradeep", "shobana", "incoming"]

    def run_sync(self):
        """
        Runs the full sync cycle:
        1. Lists files in configured folders.
        2. Downloads and parses each JSON file.
        3. Saves non-duplicate signals to SQLite.
        4. Archives files locally.
        5. Deletes files from Supabase Storage.
        """
        logger.info("Starting Consumer Ingestion Sync...")

        for folder in self.folders:
            try:
                files = self.supabase_client.list_files(folder)
                if not files:
                    logger.info(f"No files found in folder: {folder}")
                    continue

                for file_path in files:
                    self._process_file(file_path)

            except Exception as e:
                logger.error(f"Error processing folder '{folder}': {e}")

        logger.info("Consumer Ingestion Sync complete.")

    def _process_file(self, file_path: str):
        """
        Processes a single signal JSON file.
        """
        logger.info(f"Processing signal file: {file_path}")
        filename = file_path.split("/")[-1]
        bucket_name = self.supabase_client.bucket

        try:
            # 1. Download file content
            content = self.supabase_client.download_file(file_path)
            if not content:
                logger.warning(f"Downloaded empty content for: {file_path}")
                return

            # Compute content hash
            content_hash = hashlib.sha256(
                content.encode("utf-8") if isinstance(content, str) else content
            ).hexdigest()

            # Check if already processed
            if ProcessedFileRepository.exists_path_or_hash(file_path, content_hash):
                logger.info(f"File '{file_path}' or its content hash '{content_hash}' has already been processed. Skipping.")
                # Move the duplicate file out of active folder to avoid clutter
                if not file_path.startswith("archive/"):
                    logger.info(f"Moving duplicate/skipped file '{file_path}' to remote archive...")
                    self.supabase_client.move_file(file_path, f"archive/{filename}")
                return

            # 2. Parse signals
            try:
                signals = FileProcessor.parse_signals(content)
            except Exception as parse_err:
                logger.error(f"Failed to parse signals in file: {file_path}: {parse_err}")
                ProcessedFileRepository.register_file(
                    file_name=filename,
                    bucket_name=bucket_name,
                    file_path=file_path,
                    file_hash=content_hash,
                    status="FAILED"
                )
                return

            if not signals:
                logger.warning(f"No valid signals found in file: {file_path}")
                # We still register it as processed/skipped to avoid stuck queues
                ProcessedFileRepository.register_file(
                    file_name=filename,
                    bucket_name=bucket_name,
                    file_path=file_path,
                    file_hash=content_hash,
                    status="SKIPPED"
                )
                
            # 3. Insert non-duplicate signals into SQLite
            inserted_count = 0
            skipped_count = 0
            
            for signal in signals:
                msg_hash = signal["message_hash"]
                
                # Check for duplicates using SHA256 hash
                if MobileSignalRepository.exists_hash(msg_hash):
                    skipped_count += 1
                    continue
                
                # Insert if unique
                MobileSignalRepository.save_signal(
                    device_id=signal["device_id"],
                    source=signal["source"],
                    sender=signal["sender"],
                    message=signal["message"],
                    timestamp=signal["timestamp"],
                    message_hash=msg_hash
                )
                inserted_count += 1

            logger.info(
                f"File '{file_path}' results: inserted {inserted_count} signals, "
                f"skipped {skipped_count} duplicates."
            )

            # 4. Archive file locally on the laptop
            archived = self.archive_manager.archive_file(file_path, content)
            if not archived:
                logger.error(f"Failed to archive file '{file_path}' locally. Skipping Supabase archiving.")
                return

            # 5. Move file to Supabase remote archive folder
            dest_path = f"archive/{filename}"
            self.supabase_client.move_file(file_path, dest_path)

            # 6. Register file as successfully processed
            ProcessedFileRepository.register_file(
                file_name=filename,
                bucket_name=bucket_name,
                file_path=file_path,
                file_hash=content_hash,
                status="PROCESSED"
            )

        except Exception as e:
            logger.error(f"Failed to process file '{file_path}': {e}")
