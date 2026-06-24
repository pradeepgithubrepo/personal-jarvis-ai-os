# scratch/run_qualification_validation.py

import os
import sys
import json
import datetime
from collections import Counter
from unittest.mock import MagicMock, patch

# Ensure python path includes project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.signal_qualification_agent import SignalQualificationAgent
from storage.models.qualified_signal import QualifiedSignal

def run_validation():
    # Load dump file
    dump_path = "scratch/dump_preview.json"
    if not os.path.exists(dump_path):
        print(f"Error: dump file not found at {dump_path}")
        return

    with open(dump_path, "r") as f:
        data = json.load(f)

    raw_signals = data.get("signals", [])
    
    # Validation dataset filters:
    # 1. All WhatsApp signals
    # 2. Last 90 days SMS signals
    # Cutoff reference: June 23, 2026 (local time)
    ref_now = datetime.datetime(2026, 6, 23, 14, 39, 21)
    cutoff_sms = ref_now - datetime.timedelta(days=90)

    dataset = []
    for s in raw_signals:
        src = s.get("source", "").lower()
        ts = datetime.datetime.fromtimestamp(s.get("timestamp", 0) / 1000.0)
        
        if src == "whatsapp":
            dataset.append(s)
        elif src == "sms":
            if ts >= cutoff_sms:
                dataset.append(s)

    print(f"Total validation dataset size: {len(dataset)} (WhatsApp: {sum(1 for s in dataset if s['source'] == 'whatsapp')}, SMS: {sum(1 for s in dataset if s['source'] == 'sms')})")

    # Mock DB session and Supabase Repo to prevent write side-effects
    mock_db = MagicMock()
    
    # We will run 2A.1 baseline and 2A.2
    # In 2A.1:
    # - family_context is empty
    # - high_value_domains is empty
    # - qualification_rules has default thresholds but no boosts/preservation
    
    v1_results = {}
    v2_results = {}

    # Run V1
    SignalQualificationAgent._family_context = {}
    SignalQualificationAgent._high_value_domains = {}
    SignalQualificationAgent._qualification_rules = {
        "thresholds": {"rejected": 20, "review": 60, "qualified": 100},
        "boosts": {"family_context": 0, "high_value_domain": 0},
        "preservation": {"financial_topics": []}
    }

    # Helper for in-memory deduplication during dry-runs
    processed_messages_v1 = set()
    processed_messages_v2 = set()

    def mock_duplicate_v1(db, source, sender, message, timestamp):
        msg_clean = message.strip().lower()
        if msg_clean in processed_messages_v1:
            return True
        processed_messages_v1.add(msg_clean)
        return False

    def mock_duplicate_v2(db, source, sender, message, timestamp):
        msg_clean = message.strip().lower()
        if msg_clean in processed_messages_v2:
            return True
        processed_messages_v2.add(msg_clean)
        return False

    # Qualify for V1
    with patch("services.signal_qualification_agent.SupabaseRepo") as mock_supabase, \
         patch.object(SignalQualificationAgent, "check_is_duplicate", side_effect=mock_duplicate_v1):
        for s in dataset:
            res = SignalQualificationAgent.qualify_signal(
                db_session=mock_db,
                signal_id=str(s["id"]),
                source=s["source"],
                sender=s["sender"],
                message=s["message"],
                raw_ts_str=str(s["timestamp"])
            )
            v1_results[s["id"]] = {
                "status": res.qualification_status,
                "score": res.qualification_score,
                "reason": res.qualification_reason
            }

    # Run V2 (Load actual config files)
    SignalQualificationAgent._family_context = None
    SignalQualificationAgent._high_value_domains = None
    SignalQualificationAgent._qualification_rules = None
    SignalQualificationAgent.load_configs()

    # Qualify for V2
    with patch("services.signal_qualification_agent.SupabaseRepo") as mock_supabase, \
         patch.object(SignalQualificationAgent, "check_is_duplicate", side_effect=mock_duplicate_v2):
        for s in dataset:
            res = SignalQualificationAgent.qualify_signal(
                db_session=mock_db,
                signal_id=str(s["id"]),
                source=s["source"],
                sender=s["sender"],
                message=s["message"],
                raw_ts_str=str(s["timestamp"])
            )
            v2_results[s["id"]] = {
                "status": res.qualification_status,
                "score": res.qualification_score,
                "reason": res.qualification_reason
            }

    # Save validation results JSON for easy reporting
    analysis_data = {
        "dataset": dataset,
        "v1": v1_results,
        "v2": v2_results
    }
    with open("scratch/validation_run_raw.json", "w") as out:
        json.dump(analysis_data, out, indent=2)
    print("Saved raw analysis data to scratch/validation_run_raw.json")

if __name__ == "__main__":
    run_validation()
