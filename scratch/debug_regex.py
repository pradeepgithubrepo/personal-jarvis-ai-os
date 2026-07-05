import sys
import os
import re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from storage.db.database import SessionLocal
from storage.models.mobile_signal import MobileSignal

db = SessionLocal()
signals = db.query(MobileSignal).all()

regex = r"(?:rs\.?|inr|\$)\s?([\d,]+(?:\.\d+)?)"

for s in signals:
    msg_clean = s.message.strip().lower()
    amount_match = re.search(regex, msg_clean)
    if amount_match:
        val = amount_match.group(1)
        try:
            amt = float(val.replace(",", ""))
        except Exception as e:
            print(f"FAILED on ID={s.id}: message={s.message!r}")
            print(f"Match group 1: {val!r}")
            print(f"Error: {e}")
db.close()
