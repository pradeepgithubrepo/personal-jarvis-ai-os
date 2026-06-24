# scratch/check_duplicates.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import SessionLocal, initialize_database
from storage.models.mobile_signal import MobileSignal
from collections import Counter

initialize_database()
session = SessionLocal()

# Fetch all signals
signals = session.query(MobileSignal).all()
print("Total signals in DB:", len(signals))

# Count duplicates by (source, sender, message)
keys = [(s.source, s.sender, s.message) for s in signals]
counter = Counter(keys)

duplicates = {k: v for k, v in counter.items() if v > 1}
print("Unique (source, sender, message) combinations that have duplicates:", len(duplicates))
total_duplicate_messages = sum(duplicates.values())
print("Total messages that are duplicates of some other message:", total_duplicate_messages)

# Let's print the top 10 duplicates
print("\nTop 10 duplicates:")
sorted_duplicates = sorted(duplicates.items(), key=lambda x: x[1], reverse=True)
for k, v in sorted_duplicates[:10]:
    print(f"Count: {v} | Source: {k[0]} | Sender: {k[1]} | Message: {k[2][:100]}")

session.close()
