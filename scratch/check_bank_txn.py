import json

def check_bank_txn():
    with open("scratch/dump_preview.json", "r") as f:
        data = json.load(f)
        
    signals = data.get("signals", [])
    sms_signals = [s for s in signals if s.get("source") == "sms"]
    
    bank_keywords = ["debited", "credited", "spent on", "card ending", "a/c ending", "vpa", "transacted"]
    
    bank_txns = []
    for s in sms_signals:
        msg = s.get("message", "").lower()
        if any(kw in msg for kw in bank_keywords) and "otp" not in msg:
            bank_txns.append(s)
            
    print(f"Total SMS signals: {len(sms_signals)}")
    print(f"SMS signals matching bank transaction keywords: {len(bank_txns)}")
    print("\n--- Example Bank Transaction SMS (first 10) ---")
    for i, s in enumerate(bank_txns[:10]):
        print(f"{i+1}. Sender: {s.get('sender')} | Message: {s.get('message')}")

if __name__ == "__main__":
    check_bank_txn()
