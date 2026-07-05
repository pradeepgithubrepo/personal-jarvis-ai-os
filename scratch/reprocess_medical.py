import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from storage.db.database import SessionLocal
from storage.models.qualified_signal import QualifiedSignal
from storage.models.understood_signal import UnderstoodSignal
from services.signal_understanding_agent import SignalUnderstandingAgent

db = SessionLocal()
agent = SignalUnderstandingAgent()

medical_raw_ids = ["435", "401", "377", "335", "293", "13"]

for raw_id in medical_raw_ids:
    q_sig = db.query(QualifiedSignal).filter(QualifiedSignal.signal_id == raw_id).first()
    if q_sig:
        # Delete old understood signal record
        db.query(UnderstoodSignal).filter(UnderstoodSignal.qualified_signal_id == q_sig.id).delete()
        # Reprocess
        agent.process_signal(q_sig, db)
        print(f"Reprocessed qualified signal ID {q_sig.id} (raw_id={raw_id})")

db.commit()
db.close()
