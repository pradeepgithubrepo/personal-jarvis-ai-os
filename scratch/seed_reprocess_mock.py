# scratch/seed_reprocess_mock.py

import os
import sys
import json
import time
from loguru import logger

# Add root folder to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from consumer.supabase_client import SupabaseClient

def main():
    logger.info("Reading local dump_preview.json...")
    preview_path = "scratch/dump_preview.json"
    if not os.path.exists(preview_path):
        logger.error(f"Dump preview file not found at {preview_path}. Cannot seed mock data.")
        return

    with open(preview_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    signals = data.get("signals", [])
    logger.info(f"Loaded {len(signals)} signals from preview.")

    # Select 3 whatsapp signals and 3 sms bank txn signals (containing debit/credit)
    whatsapp_sigs = [s for s in signals if s.get("source") == "whatsapp"]
    sms_sigs = [s for s in signals if s.get("source") == "sms"]

    # Filter SMS signals to find bank transaction-like notifications
    sms_bank_sigs = []
    bank_keywords = ["debited", "credited", "spent", "card ending", "upi"]
    for s in sms_sigs:
        msg = s.get("message", "").lower()
        if any(kw in msg for kw in bank_keywords) and "otp" not in msg:
            sms_bank_sigs.append(s)

    selected_whatsapp = whatsapp_sigs[:3]
    selected_sms = sms_bank_sigs[:3]

    selected_signals = selected_whatsapp + selected_sms
    logger.info(f"Selected {len(selected_whatsapp)} WhatsApp signals and {len(selected_sms)} SMS bank signals.")

    mock_payload = {
        "generatedAt": int(time.time() * 1000),
        "signals": selected_signals
    }

    client = SupabaseClient()
    mock_filename = f"pradeep/historical_mock_{int(time.time())}.json"
    logger.info(f"Uploading mock signals JSON to bucket at path: {mock_filename}")
    
    content = json.dumps(mock_payload, indent=2)
    success = client.upload_file(mock_filename, content)
    if success:
        logger.success(f"Mock file seeded successfully at {mock_filename}")
    else:
        logger.error("Failed to upload mock file to Supabase Storage.")

if __name__ == "__main__":
    main()
