# scratch/analyze_llm_messages.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import SessionLocal, initialize_database
from storage.models.mobile_signal import MobileSignal
from skills.mobile.mobile_intent_extractor import MobileIntentExtractor
from skills.mobile.mobile_noise_filter import MobileNoiseFilter
from collections import Counter

initialize_database()
session = SessionLocal()

unprocessed = session.query(MobileSignal).filter(MobileSignal.processed == False).all()

extractor = MobileIntentExtractor()

senders_requiring_llm = []
messages_requiring_llm = []

for msg in unprocessed:
    signal_dict = {
        "source": msg.source,
        "sender": msg.sender,
        "message": msg.message
    }
    
    if MobileNoiseFilter.is_noise(signal_dict):
        continue
        
    pre = extractor._rule_based_pre_classify(signal_dict)
    if not pre:
        senders_requiring_llm.append(msg.sender)
        messages_requiring_llm.append((msg.sender, msg.message))

print(f"Total messages requiring LLM: {len(messages_requiring_llm)}")

# Count most common senders requiring LLM
sender_counts = Counter(senders_requiring_llm)
print("\nTop 20 senders requiring LLM:")
for sender, count in sender_counts.most_common(20):
    print(f"  {sender}: {count}")

# Print sample messages for the top senders
print("\nSample messages for top senders:")
for sender, count in sender_counts.most_common(10):
    print(f"\n--- SENDER: {sender} ({count} messages) ---")
    samples = [msg for s, msg in messages_requiring_llm if s == sender][:5]
    for sample in samples:
        print(f"  - {sample[:150]}")

session.close()
