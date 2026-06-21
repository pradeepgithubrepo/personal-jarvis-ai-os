# consumer/supabase_client.py

import httpx
from loguru import logger
from configs.settings import settings


class SupabaseClient:

    def __init__(self):
        self.url = settings.supabase_url
        self.key = settings.supabase_key
        self.bucket = settings.supabase_bucket
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}"
        }

    def list_files(self, folder_name: str) -> list[str]:
        """
        Lists files inside the specified folder in the bucket.
        Skips placeholders like '.emptyFolderPlaceholder'.
        Returns a list of full paths relative to the bucket.
        """
        list_url = f"{self.url}/storage/v1/object/list/{self.bucket}"
        
        # We search inside folder_name/ (with trailing slash)
        prefix = f"{folder_name}/"
        payload = {
            "prefix": prefix,
            "limit": 100,
            "sortBy": {
                "column": "name",
                "order": "asc"
            }
        }

        try:
            logger.info(f"Listing files in Supabase bucket '{self.bucket}' under prefix '{prefix}'...")
            response = httpx.post(
                list_url,
                headers={**self.headers, "Content-Type": "application/json"},
                json=payload,
                timeout=30.0
            )

            if response.status_code != 200:
                logger.error(f"Failed to list files. HTTP {response.status_code}: {response.text}")
                return []

            items = response.json()
            file_paths = []
            for item in items:
                name = item.get("name")
                if not name:
                    continue
                # Skip the placeholder files created by Supabase UI
                if name == ".emptyFolderPlaceholder":
                    continue
                # Construct the full path (relative to the bucket)
                full_path = f"{folder_name}/{name}"
                file_paths.append(full_path)

            logger.info(f"Found {len(file_paths)} files to process in '{prefix}'")
            return file_paths

        except Exception as e:
            logger.exception(f"Error listing files from Supabase: {e}")
            return []

    def download_file(self, full_path: str) -> str:
        """
        Downloads a file from the bucket by its full path.
        """
        download_url = f"{self.url}/storage/v1/object/authenticated/{self.bucket}/{full_path}"
        try:
            logger.info(f"Downloading file '{full_path}' from Supabase...")
            response = httpx.get(
                download_url,
                headers=self.headers,
                timeout=30.0
            )

            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}: {response.text}")

            return response.text

        except Exception as e:
            logger.error(f"Error downloading file '{full_path}' from Supabase: {e}")
            raise

    def delete_file(self, full_path: str) -> bool:
        """
        Deletes a file from the bucket by its full path.
        """
        delete_url = f"{self.url}/storage/v1/object/{self.bucket}"
        payload = {
            "prefixes": [full_path]
        }
        try:
            logger.info(f"Deleting file '{full_path}' from Supabase...")
            response = httpx.request(
                "DELETE",
                delete_url,
                headers={**self.headers, "Content-Type": "application/json"},
                json=payload,
                timeout=30.0
            )

            if response.status_code == 200:
                logger.success(f"Successfully deleted file '{full_path}' from Supabase Storage.")
                return True
            else:
                logger.error(f"Failed to delete file '{full_path}'. HTTP {response.status_code}: {response.text}")
                return False

        except Exception as e:
            logger.exception(f"Error deleting file '{full_path}' from Supabase: {e}")
            return False

    def copy_file(self, src_path: str, dest_path: str) -> bool:
        """
        Copies a file from src_path to dest_path within the bucket.
        """
        copy_url = f"{self.url}/storage/v1/object/copy"
        payload = {
            "bucketId": self.bucket,
            "sourceKey": src_path,
            "destinationKey": dest_path
        }
        try:
            logger.info(f"Copying file '{src_path}' to '{dest_path}' in Supabase Storage...")
            response = httpx.post(
                copy_url,
                headers={**self.headers, "Content-Type": "application/json"},
                json=payload,
                timeout=30.0
            )

            if response.status_code == 200:
                logger.success(f"Successfully copied file '{src_path}' to '{dest_path}' in Supabase Storage.")
                return True
            else:
                logger.error(f"Failed to copy file '{src_path}' to '{dest_path}'. HTTP {response.status_code}: {response.text}")
                return False

        except Exception as e:
            logger.exception(f"Error copying file '{src_path}' to '{dest_path}' in Supabase: {e}")
            return False

    def upload_file(self, full_path: str, content: str) -> bool:
        """
        Uploads a file to the bucket by its full path.
        """
        upload_url = f"{self.url}/storage/v1/object/{self.bucket}/{full_path}"
        try:
            logger.info(f"Uploading file '{full_path}' to Supabase...")
            response = httpx.post(
                upload_url,
                headers={**self.headers, "Content-Type": "application/json"},
                content=content.encode("utf-8") if isinstance(content, str) else content,
                timeout=30.0
            )

            if response.status_code == 200:
                logger.success(f"Successfully uploaded file '{full_path}' to Supabase Storage.")
                return True
            else:
                logger.error(f"Failed to upload file '{full_path}'. HTTP {response.status_code}: {response.text}")
                return False

        except Exception as e:
            logger.exception(f"Error uploading file '{full_path}' to Supabase: {e}")
            return False

    def move_file(self, src_path: str, dest_path: str) -> bool:
        """
        Moves a file by copying it to the destination and then deleting the source.
        Falls back to download + upload if the copy API fails.
        """
        logger.info(f"Moving file '{src_path}' to '{dest_path}' in Supabase Storage...")
        
        # Try copying first
        if self.copy_file(src_path, dest_path):
            return self.delete_file(src_path)
            
        logger.warning(f"Copy API failed for '{src_path}' -> '{dest_path}'. Falling back to download and upload...")
        try:
            # Fallback: Download, Upload to dest, then delete source
            content = self.download_file(src_path)
            if self.upload_file(dest_path, content):
                return self.delete_file(src_path)
        except Exception as e:
            logger.error(f"Fallback move failed: {e}")
            
        return False
