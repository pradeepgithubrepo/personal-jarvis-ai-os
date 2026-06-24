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
        # Consolidated to 'incoming' folder only as the single entry point
        self.folders = ["incoming"]

    def run_sync(self):
        """
        Runs the full sync cycle:
        1. Lists files in configured folders.
        2. Downloads and parses each JSON file.
        3. Saves non-duplicate signals to SQLite.
        4. Archives files locally.
        5. Registers files in processed_files.
        6. Moves processed files to archive in Supabase Storage.
        """
        logger.info("Starting Consumer Ingestion Sync...")

        # Initialize counters
        metrics = {
            "files_found": 0,
            "files_processed": 0,
            "files_failed": 0,
            "signals_loaded": 0,
            "signals_skipped": 0,
            "signals_saved": 0
        }

        for folder in self.folders:
            try:
                files = self.supabase_client.list_files(folder)
                if not files:
                    logger.info(f"No files found in folder: {folder}")
                    continue

                metrics["files_found"] += len(files)

                for file_path in files:
                    res = self._process_file(file_path)
                    status = res.get("status")
                    
                    if status == "FAILED":
                        metrics["files_failed"] += 1
                    elif status in ("PROCESSED", "SKIPPED", "DUPLICATE"):
                        metrics["files_processed"] += 1
                        
                    metrics["signals_loaded"] += res.get("loaded", 0)
                    metrics["signals_skipped"] += res.get("skipped", 0)
                    metrics["signals_saved"] += res.get("saved", 0)

            except Exception as e:
                logger.error(f"Error processing folder '{folder}': {e}")

        # Display progress visibility statistics
        logger.info("==================================================")
        logger.info("           Consumer Ingestion Summary             ")
        logger.info("==================================================")
        logger.info(f"Files Found      : {metrics['files_found']}")
        logger.info(f"Files Processed  : {metrics['files_processed']}")
        logger.info(f"Files Failed     : {metrics['files_failed']}")
        logger.info(f"Signals Loaded   : {metrics['signals_loaded']}")
        logger.info(f"Signals Skipped  : {metrics['signals_skipped']}")
        logger.info(f"Signals Saved    : {metrics['signals_saved']}")
        logger.info("==================================================")
        logger.info("Consumer Ingestion Sync complete.")
        return metrics

    def _process_file(self, file_path: str) -> dict:
        """
        Processes a single signal JSON file.
        Returns a dict of counters/status for the file.
        """
        logger.info(f"Processing signal file: {file_path}")
        filename = file_path.split("/")[-1]
        bucket_name = self.supabase_client.bucket

        stats = {"status": "FAILED", "loaded": 0, "skipped": 0, "saved": 0}

        try:
            # 1. Download file content
            content = self.supabase_client.download_file(file_path)
            if not content:
                logger.warning(f"Downloaded empty content for: {file_path}")
                return stats

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
                stats["status"] = "DUPLICATE"
                return stats

            # 2. Parse signals
            try:
                signals = FileProcessor.parse_signals(content)
            except Exception as parse_err:
                logger.error(f"Failed to parse signals in file: {file_path}: {parse_err}")
                return stats

            # If empty signals list, proceed to archive & register as SKIPPED
            if not signals:
                logger.warning(f"No valid signals found in file: {file_path}")
                
                # Try local archival
                archived = self.archive_manager.archive_file(file_path, content)
                if not archived:
                    return stats

                # Try database registration
                registered = ProcessedFileRepository.register_file(
                    file_name=filename,
                    bucket_name=bucket_name,
                    file_path=file_path,
                    file_hash=content_hash,
                    status="SKIPPED"
                )
                if not registered:
                    return stats

                # Try moving to remote archive
                moved = self.supabase_client.move_file(file_path, f"archive/{filename}")
                if not moved:
                    return stats

                stats["status"] = "SKIPPED"
                return stats
                
            # 3. Insert non-duplicate signals into SQLite (preserving timestamps)
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
                logger.error(f"Failed to archive file '{file_path}' locally. Skipping registration and Supabase archiving.")
                return stats

            # 5. Register file as successfully processed in SQLite + Supabase
            registered = ProcessedFileRepository.register_file(
                file_name=filename,
                bucket_name=bucket_name,
                file_path=file_path,
                file_hash=content_hash,
                status="PROCESSED"
            )
            if not registered:
                logger.error(f"Failed to register processed file '{file_path}' in DB registry. Skipping Supabase archiving.")
                return stats

            # 6. Move file to Supabase remote archive folder
            dest_path = f"archive/{filename}"
            moved = self.supabase_client.move_file(file_path, dest_path)
            if not moved:
                logger.error(f"Failed to move file '{file_path}' to remote archive in Supabase Storage.")
                # We return success if DB registration succeeded because the file metadata is stored,
                # but log the failure of final physical relocation.
                return stats

            stats.update({
                "status": "PROCESSED",
                "loaded": len(signals),
                "skipped": skipped_count,
                "saved": inserted_count
            })
            return stats

        except Exception as e:
            logger.error(f"Failed to process file '{file_path}': {e}")
            return stats

