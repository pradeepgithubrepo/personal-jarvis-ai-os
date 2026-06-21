# consumer/file_processor.py

import json
import hashlib
from loguru import logger


def compute_message_hash(sender: str, message: str, timestamp: str | int) -> str:
    """
    Computes SHA256(sender + message + timestamp) to uniquely identify a signal.
    """
    raw_str = f"{sender}{message}{str(timestamp)}"
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()


class FileProcessor:

    @staticmethod
    def parse_signals(json_content: str) -> list[dict]:
        """
        Parses a raw JSON signal dump and returns a list of processed signals
        with their unique message hashes.
        """
        try:
            data = json.loads(json_content)
            signals_list = data.get("signals", [])
            
            processed_signals = []
            for item in signals_list:
                sender = item.get("sender", "")
                message = item.get("message", "")
                timestamp = item.get("timestamp", 0)
                device_id = item.get("deviceId", "unknown_device")
                source = item.get("source", "unknown_source")

                if not sender and not message and not timestamp:
                    logger.warning(f"Skipping empty or malformed signal entry: {item}")
                    continue

                message_hash = compute_message_hash(sender, message, timestamp)

                processed_signals.append({
                    "device_id": device_id,
                    "source": source,
                    "sender": sender,
                    "message": message,
                    "timestamp": timestamp,
                    "message_hash": message_hash
                })

            logger.info(f"Successfully parsed {len(processed_signals)} signals from JSON content.")
            return processed_signals

        except Exception as e:
            logger.error(f"Failed to parse JSON signal dump: {e}")
            return []
