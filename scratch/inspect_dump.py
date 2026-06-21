import json

def inspect():
    with open("scratch/dump_preview.json", "r") as f:
        data = json.load(f)
        
    signals = data.get("signals", [])
    print(f"Total signals in dump: {len(signals)}")
    
    whatsapp_signals = [s for s in signals if s.get("source") == "whatsapp"]
    sms_signals = [s for s in signals if s.get("source") == "sms"]
    other_signals = [s for s in signals if s.get("source") not in ("whatsapp", "sms")]
    
    print(f"WhatsApp signals: {len(whatsapp_signals)}")
    print(f"SMS signals: {len(sms_signals)}")
    print(f"Other signals: {len(other_signals)}")
    
    print("\n--- WhatsApp Preview (first 5) ---")
    for i, s in enumerate(whatsapp_signals[:5]):
        print(f"{i+1}. Sender: {s.get('sender')} | Message: {s.get('message')}")
        
    print("\n--- SMS Preview (first 5) ---")
    for i, s in enumerate(sms_signals[:5]):
        print(f"{i+1}. Sender: {s.get('sender')} | Message: {s.get('message')}")

if __name__ == "__main__":
    inspect()
