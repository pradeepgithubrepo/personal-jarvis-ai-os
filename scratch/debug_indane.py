import sys
import os
import json
import re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from storage.db.database import SessionLocal
from storage.models.qualified_signal import QualifiedSignal
from storage.models.understood_signal import UnderstoodSignal
from services.signal_understanding_agent import SignalUnderstandingAgent

db = SessionLocal()
q = db.query(QualifiedSignal).filter(QualifiedSignal.signal_id == "319").first()
print(f"Message: {q.message!r}")

# Let's run regex manually
msg = q.message.replace("\n", " ").lower().strip()
pattern = r"(?:₹|rs\.?|inr)\s?([\d,]+(?:\.\d+)?)"
match = re.search(pattern, msg)
if match:
    print(f"Matched amount string: {match.group(1)}")
else:
    print("No regex match!")
db.close()
