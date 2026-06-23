# storage/repositories/processed_file_repository.py

from loguru import logger
from storage.db.database import SessionLocal
from storage.models.processed_file import ProcessedFile


class ProcessedFileRepository:

    @staticmethod
    def exists_path_or_hash(file_path: str, file_hash: str) -> bool:
        """
        Checks if a file with the given path or content hash has already been registered.
        """
        session = SessionLocal()
        try:
            query = session.query(ProcessedFile).filter(
                (ProcessedFile.file_path == file_path) |
                (ProcessedFile.file_hash == file_hash)
            )
            return query.first() is not None
        except Exception as e:
            logger.error(f"Error checking processed file existence: {e}")
            return False
        finally:
            session.close()

    @staticmethod
    def register_file(file_name: str, bucket_name: str, file_path: str, file_hash: str, status: str) -> bool:
        """
        Registers a file in the database registry.
        """
        session = SessionLocal()
        try:
            record = ProcessedFile(
                file_name=file_name,
                bucket_name=bucket_name,
                file_path=file_path,
                file_hash=file_hash,
                status=status
            )
            session.add(record)
            session.commit()
            logger.success(f"Registered file {file_path} in local DB registry (Status: {status}).")
            
            # Sync to Supabase
            try:
                from services.supabase_repo import SupabaseRepo
                SupabaseRepo.register_processed_file(
                    file_name=file_name,
                    bucket_name=bucket_name,
                    file_path=file_path,
                    file_hash=file_hash,
                    status=status
                )
            except Exception as se:
                logger.warning(f"Could not sync processed file to Supabase registry: {se}")

            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to register file {file_path} in local DB: {e}")
            return False
        finally:
            session.close()
