# ui/cache_manager.py

import os
import json
from datetime import datetime
from loguru import logger
from configs.settings import settings
from consumer.supabase_client import SupabaseClient

CACHE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "cache"))
LAST_REFRESH_FILE = os.path.join(CACHE_DIR, ".last_refresh")

INSIGHT_FILES = [
    "daily_brief.json",
    "todos.json",
    "financial.json",
    "fyi.json",
    "family.json",
    "school.json",
    "travel.json",
    "health.json"
]

class CacheManager:
    @staticmethod
    def initialize_cache():
        """Ensure cache directory exists."""
        if not os.path.exists(CACHE_DIR):
            os.makedirs(CACHE_DIR, exist_ok=True)

    @staticmethod
    def get_last_refresh_time() -> str:
        """Returns the formatted last refresh time, or 'Never' if not refreshed yet."""
        CacheManager.initialize_cache()
        if os.path.exists(LAST_REFRESH_FILE):
            try:
                with open(LAST_REFRESH_FILE, "r") as f:
                    return f.read().strip()
            except Exception as e:
                logger.error(f"Error reading last refresh file: {e}")
        return "Never"

    @staticmethod
    def update_last_refresh_time():
        """Updates the last refresh time to the current local time."""
        CacheManager.initialize_cache()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(LAST_REFRESH_FILE, "w") as f:
                f.write(now_str)
        except Exception as e:
            logger.error(f"Error writing last refresh file: {e}")

    @staticmethod
    def download_all_insights() -> bool:
        """
        Downloads all 8 JSON insight files from Supabase Storage bucket 'jarvis-insights'
        and updates the local cache. Returns True if all files download successfully, False otherwise.
        """
        CacheManager.initialize_cache()
        bucket_name = getattr(settings, "supabase_insights_bucket", "jarvis-insights")
        client = SupabaseClient(bucket=bucket_name)
        
        logger.info(f"Downloading all insights from Supabase bucket '{bucket_name}' to local cache...")
        success_count = 0
        
        for filename in INSIGHT_FILES:
            try:
                # download_file fetches authenticated file from bucket at the given path
                content = client.download_file(filename)
                if content:
                    local_path = os.path.join(CACHE_DIR, filename)
                    with open(local_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    success_count += 1
                else:
                    logger.warning(f"Downloaded empty content for {filename}")
            except Exception as e:
                logger.error(f"Failed to download {filename} from Supabase: {e}")
                
        if success_count == len(INSIGHT_FILES):
            CacheManager.update_last_refresh_time()
            logger.success("All insights successfully downloaded and cached.")
            return True
        else:
            logger.warning(f"Only {success_count}/{len(INSIGHT_FILES)} insights were cached.")
            if success_count > 0:
                # Still update refresh time if we got at least some updates
                CacheManager.update_last_refresh_time()
            return False

    @staticmethod
    def load_insight(filename: str) -> dict:
        """
        Loads a specific insight JSON from the local cache.
        If file is missing in cache, attempts to download it.
        Returns a dict.
        """
        CacheManager.initialize_cache()
        local_path = os.path.join(CACHE_DIR, filename)
        
        if not os.path.exists(local_path):
            logger.info(f"Cache miss for {filename}. Attempting download...")
            bucket_name = getattr(settings, "supabase_insights_bucket", "jarvis-insights")
            client = SupabaseClient(bucket=bucket_name)
            try:
                content = client.download_file(filename)
                if content:
                    with open(local_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    CacheManager.update_last_refresh_time()
                else:
                    return {}
            except Exception as e:
                logger.error(f"Failed to download missing file {filename}: {e}")
                return {}
                
        try:
            with open(local_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error parsing local cache file {filename}: {e}")
            return {}
