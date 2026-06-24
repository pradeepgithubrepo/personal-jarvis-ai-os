# scratch/count_records.py

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.system_initializer import initialize_system
from storage.db.database import SessionLocal
from storage.models.mobile_signal import MobileSignal
from storage.models.signal import Signal
from storage.models.processed_file import ProcessedFile
from services.supabase_repo import SupabaseRepo, supabase

def check():
    initialize_system()
    db = SessionLocal()
    
    print("\n" + "=" * 50)
    print("         SQLITE LOCAL COUNTS")
    print("=" * 50)
    print(f"processed_files : {db.query(ProcessedFile).count()}")
    print(f"mobile_signals  : {db.query(MobileSignal).count()}")
    print(f"signals         : {db.query(Signal).count()}")
    
    print("\n" + "=" * 50)
    print("         SUPABASE REMOTE COUNTS")
    print("=" * 50)
    try:
        r_files = supabase.table("processed_files").select("*", count="exact").execute()
        print(f"processed_files : {r_files.count}")
    except Exception as e:
        print(f"Failed to fetch processed_files: {e}")
        
    try:
        r_signals = supabase.table("signals").select("*", count="exact").execute()
        print(f"signals         : {r_signals.count}")
    except Exception as e:
        print(f"Failed to fetch signals: {e}")

    db.close()

if __name__ == "__main__":
    check()
