import json

def check_financial():
    with open("scratch/dump_preview.json", "r") as f:
        data = json.load(f)
        
    signals = data.get("signals", [])
    sms_signals = [s for s in signals if s.get("source") == "sms"]
    
    finance_keywords = ["spent", "debited", "credited", "rs", "inr", "transaction", "otp", "upi", "card"]
    
    finance_count = 0
    finance_examples = []
    
    for s in sms_signals:
        msg = s.get("message", "").lower()
        if any(kw in msg for kw in finance_keywords):
            finance_count += 1
            if len(finance_examples) < 10:
                finance_examples.append(s)
                
    print(f"Total SMS signals: {len(sms_signals)}")
    print(f"SMS signals matching financial keywords: {finance_count}")
    print("\n--- Example Financial SMS ---")
    for i, s in enumerate(finance_examples):
        print(f"{i+1}. Sender: {s.get('sender')} | Message: {s.get('message')}")

if __name__ == "__main__":
    check_financial()
