import os
import sys
import sqlite3
import json

def check_sqlite():
    print("=== READING FROM SQLITE (READ-ONLY MODE) ===")
    db_path = "storage/db/sqlite/jarvis.db"
    if not os.path.exists(db_path):
        print(f"SQLite DB not found at {db_path}")
        return
        
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cursor = conn.cursor()
        
        # Query WhatsApp signals from signals table
        cursor.execute("SELECT id, category, importance, summary, raw_json, created_at FROM signals WHERE source='whatsapp';")
        signals = cursor.fetchall()
        print(f"Found {len(signals)} WhatsApp signals in signals table.\n")
        
        for row in signals:
            sig_id, category, importance, summary, raw_json, created_at = row
            print(f"Signal ID: {sig_id}")
            print(f"  Category: {category}")
            print(f"  Importance: {importance}")
            print(f"  Summary: {summary}")
            print(f"  Created At: {created_at}")
            print(f"  Raw JSON: {raw_json}")
            print("-" * 50)
            
    except Exception as e:
        print(f"SQLite Error: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            pass

if __name__ == "__main__":
    check_sqlite()
