# consumer/archive_manager.py

import os
from loguru import logger


class ArchiveManager:

    def __init__(self, archive_dir="data/archive"):
        # Resolve path relative to workspace or absolute
        self.archive_dir = os.path.abspath(archive_dir)

    def archive_file(self, full_path: str, content: str) -> bool:
        """
        Saves the raw JSON file contents locally to the archive folder,
        preserving the relative directory structure (e.g. data/archive/pradeep/filename.json).
        """
        target_path = os.path.join(self.archive_dir, full_path)
        target_dir = os.path.dirname(target_path)

        try:
            os.makedirs(target_dir, exist_ok=True)
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.success(f"Successfully archived file locally at: {target_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to archive file '{full_path}' locally: {e}")
            return False
