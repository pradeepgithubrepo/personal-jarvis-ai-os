# services/supabase_sync_service.py

import json
from loguru import logger
from configs.settings import settings
from storage.db.database import SessionLocal
from storage.models.daily_brief import DailyBrief
from consumer.supabase_client import SupabaseClient


class SupabaseSyncService:
    """
    Milestone 6 - Supabase Feedback Loop
    Synchronizes local structured daily briefs back to Supabase.
    """

    @classmethod
    def sync_brief_for_date(cls, date_str: str) -> bool:
        """
        Loads the daily brief for the specified date_str (YYYY-MM-DD) from local SQLite,
        and uploads it as a JSON file to the 'jarvis-insights' Supabase bucket.
        Returns True if successful, False otherwise.
        Does not raise exceptions, logging warnings instead to prevent breaking local runs.
        """
        logger.info(f"Starting feedback loop sync for daily brief: {date_str}")
        
        db = SessionLocal()
        try:
            # 1. Fetch brief from local database
            db_brief = db.query(DailyBrief).filter(DailyBrief.date == date_str).first()
            if not db_brief:
                logger.warning(f"No daily brief found in local database for date {date_str}. Aborting sync.")
                return False

            # Ensure the JSON is parseable and valid
            try:
                brief_data = json.loads(db_brief.content_json)
            except Exception as parse_err:
                logger.error(f"Failed to parse daily brief JSON for {date_str}: {parse_err}")
                return False

            # Pretty print JSON content for upload
            serialized_content = json.dumps(brief_data, indent=2)

            # 2. Upload to Supabase 'jarvis-insights' bucket
            bucket_name = getattr(settings, "supabase_insights_bucket", "jarvis-insights")
            client = SupabaseClient(bucket=bucket_name)

            destination_path = f"daily_briefs/{date_str}.json"
            logger.info(f"Uploading daily brief to bucket '{bucket_name}' at path '{destination_path}'...")
            
            success = client.upload_file(destination_path, serialized_content)
            if success:
                logger.success(f"Successfully synced daily brief for {date_str} to Supabase bucket '{bucket_name}'.")
                return True
            else:
                logger.error(f"Failed to upload daily brief for {date_str} to Supabase storage.")
                return False

        except Exception as e:
            logger.warning(f"An unexpected error occurred during Supabase sync for date {date_str}: {e}")
            return False
        finally:
            db.close()
