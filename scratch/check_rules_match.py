# scratch/check_rules_match.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import SessionLocal, initialize_database
from storage.models.mobile_signal import MobileSignal
from skills.mobile.mobile_intent_extractor import MobileIntentExtractor
from skills.mobile.mobile_noise_filter import MobileNoiseFilter

initialize_database()
session = SessionLocal()

unprocessed = session.query(MobileSignal).filter(MobileSignal.processed == False).all()
print("Total unprocessed in DB:", len(unprocessed))

noise_count = 0
pre_classified_count = 0
telecom_count = 0
system_count = 0
otp_count = 0
promo_count = 0
llm_required_count = 0

extractor = MobileIntentExtractor()

for msg in unprocessed:
    signal_dict = {
        "source": msg.source,
        "sender": msg.sender,
        "message": msg.message
    }
    
    if MobileNoiseFilter.is_noise(signal_dict):
        noise_count += 1
        continue
        
    pre = extractor._rule_based_pre_classify(signal_dict)
    if pre:
        pre_classified_count += 1
        intent = pre["intent"]
        summary = pre["summary"]
        if "Telecom" in summary:
            telecom_count += 1
        elif "System" in summary:
            system_count += 1
        elif intent == "otp":
            otp_count += 1
        elif "Promotional" in summary:
            promo_count += 1
    else:
        llm_required_count += 1

print("\nAnalysis of unprocessed signals:")
print(f"  Dropped as Noise (Filter): {noise_count}")
print(f"  Pre-Classified (Bypass LLM): {pre_classified_count}")
print(f"    - Telecom/Data Balance Alerts: {telecom_count}")
print(f"    - System Notifications: {system_count}")
print(f"    - OTPs: {otp_count}")
print(f"    - Promotional Spam: {promo_count}")
print(f"  Requires LLM: {llm_required_count}")

session.close()
