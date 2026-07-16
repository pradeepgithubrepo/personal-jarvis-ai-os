import os
import json
import re
import uuid
from dotenv import load_dotenv
from supabase import create_client, ClientOptions

def extract_entities(message: str) -> list[str]:
    candidates = re.findall(r"\b[A-Z][a-zA-Z0-9]+\b", message)
    exclude = {"Alert", "Your", "Dear", "Customer", "Bank", "Info", "Txn", "Use", "This", "The", "And", "With", "For", "Rs", "Inr", "Good", "Morning", "Have", "A", "Is", "Note"}
    return list(set([c for c in candidates if c not in exclude]))

def main():
    load_dotenv('/home/prad/petprojects/ai/jarvis/.env')
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not supabase_key:
        print("Error: Supabase credentials missing.")
        return
        
    options = ClientOptions(schema="jarvis_insights_schemav1")
    client = create_client(supabase_url, supabase_key, options=options)
    
    print("Fetching raw signals from mobile_signals table...")
    res = client.table("mobile_signals").select("*").limit(400).execute()
    raw_signals = res.data
    print(f"Fetched {len(raw_signals)} raw signals.")
    
    gold_signals = []
    
    for sig in raw_signals:
        msg = sig.get("message", "")
        if not msg or len(msg.strip()) < 5:
            continue
            
        msg_lower = msg.lower()
        sender = sig.get("sender", "")
        sender_lower = sender.lower()
        
        # Rule-based ground truth categorization
        sig_type = "NOISE"
        importance = 0.1
        contract = {}
        
        # Heuristic keywords
        noise_keywords = ["otp", "verification code", "one-time password", "verification pin", "one time password", "trans.no", "your otp", "verification", "g-code"]
        greeting_keywords = ["good morning", "good night", "happy birthday", "have a wonderful day", "have a great day"]
        promo_keywords = ["vi.in", "recharge your prepaid", "gb/day", "promo code", "discount", "click to buy", "airtel", "recharge your", "recharge rs"]
        badminton_keywords = ["badminton", "court booking", "update:"]
        
        financial_keywords = ["debited", "credited", "spent", "spent on", "card ending", "upi", "txn of", "txn at", "received", "credited with", "payment of", "emi", "paid to", "received from", "transferred", "payment of", "txn"]
        action_keywords = ["remind", "todo", "todo:", "task:", "action:", "buy", "call ", "please call", "need to", "don't forget", "please", "can you", "could you", "share", "send", "give"]
        fyi_keywords = ["flight", "booking", "scheduled for", "ticket", "boarding", "departure", "pnr", "seat"]
        fact_keywords = ["passport", "weight", "height", "birthday", "birth", "blood group", "address is", "license"]
        
        # Check NOISE first to avoid classifying OTPs or promo balance alerts as financial transactions
        is_noise = (
            any(kw in msg_lower for kw in noise_keywords) or
            any(kw in msg_lower for kw in greeting_keywords) or
            any(kw in msg_lower for kw in promo_keywords) or
            any(kw in msg_lower for kw in badminton_keywords) or
            "badminton" in sender_lower or
            "airtel" in sender_lower
        )
        
        if is_noise:
            sig_type = "NOISE"
            importance = 0.1
            contract = {}
        elif any(kw in msg_lower for kw in financial_keywords):
            sig_type = "FINANCIAL"
            importance = 0.85
            # Extract amount if possible
            amt_match = re.search(r"(?:rs\.?|inr)\s*([\d,]+(?:\.\d{2})?)", msg_lower)
            amount = float(amt_match.group(1).replace(",", "")) if amt_match else None
            tx_type = "UNKNOWN"
            if "credited" in msg_lower or "received" in msg_lower:
                tx_type = "CREDIT"
            elif "debited" in msg_lower or "spent" in msg_lower or "paid" in msg_lower or "transferred" in msg_lower:
                tx_type = "DEBIT"
            contract = {
                "amount": amount,
                "currency": "INR" if amount else None,
                "transaction_type": tx_type,
                "payment_channel": "UPI" if "upi" in msg_lower else "UNKNOWN",
                "merchant": None
            }
        elif any(kw in msg_lower for kw in action_keywords):
            sig_type = "ACTION"
            importance = 0.75
            contract = {
                "task_name": msg,
                "assignee": "unknown",
                "due_date": None
            }
        elif any(kw in msg_lower for kw in fyi_keywords):
            sig_type = "FYI"
            importance = 0.5
            contract = {
                "event_name": "Booking / Event Alert",
                "event_time": None,
                "description": msg
            }
        elif any(kw in msg_lower for kw in fact_keywords):
            sig_type = "FACT"
            importance = 0.6
            contract = {
                "entity": "user",
                "attribute": "fact",
                "value": msg
            }
        else:
            # Default to NOISE for general chit chat or low-importance notifications
            sig_type = "NOISE"
            importance = 0.1
            contract = {}
            
        # Append canonical extended contract fields
        contract["entities"] = extract_entities(msg)
        contract["financial_candidate"] = (sig_type == "FINANCIAL")
        contract["fact_candidate"] = (sig_type == "FACT")
        contract["fyi_candidate"] = (sig_type == "FYI")
        contract["noise_candidate"] = (sig_type == "NOISE")
        contract["requires_action"] = (sig_type == "ACTION")
        contract["memory_candidate"] = (sig_type in ["FACT", "ACTION", "FYI"])
        
        gold_signals.append({
            "id": str(uuid.uuid4()),
            "signal_id": sig.get("id"),
            "source": sig.get("source", "unknown"),
            "sender": sender,
            "message": msg,
            "timestamp": sig.get("mobile_timestamp") or sig.get("created_at"),
            "expected": {
                "signal_type": sig_type,
                "importance": importance,
                "contract": contract
            }
        })
        
        # Stop at 210 signals
        if len(gold_signals) >= 210:
            break
            
    # Write to tests/sua_gold_set.json
    with open("tests/sua_gold_set.json", "w") as f:
        json.dump(gold_signals, f, indent=2)
        
    print(f"Successfully generated tests/sua_gold_set.json with {len(gold_signals)} signals!")

if __name__ == "__main__":
    main()
