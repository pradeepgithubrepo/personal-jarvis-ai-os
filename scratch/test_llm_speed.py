import os
import sys
import json
import time
import requests
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions

load_dotenv()

supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

options = ClientOptions(schema="jarvis_insights_schemav1")
client: Client = create_client(supabase_url, supabase_key, options=options)

# Get 15 WhatsApp signals from qualified_signals
res = client.table("qualified_signals").select("*").eq("source", "whatsapp").limit(15).execute()
signals = res.data

print(f"Retrieved {len(signals)} WhatsApp signals for test.")

def build_prompt(message: str, sender: str, source: str, timestamp: str) -> str:
    return f"""Analyze the message and classify it into exactly one of these types:
- FINANCIAL: Active transactions, credit/debit alerts, bank spent/received notifications, payment receipts. (Only if money is actively transferred or spent)
- ACTION: Reminders, todos, tasks, chores, or direct requests to do something (e.g. 'call plumber', 'buy milk').
- FYI: Schedules, bookings, flight/train/movie status, appointments, non-actionable info. (e.g. 'flight AI-101 scheduled')
- FACT: User context, credentials, passport, birthday, height/weight info.
- NOISE: Greetings, spam, chit-chat, OTPs, promotional codes, or generic messages.

Message to analyze:
Sender: {sender}
Source: {source}
Content: {message}
Timestamp: {timestamp}

Respond ONLY with a single JSON object. Do not wrap in markdown or code blocks.
JSON format keys:
"signal_type" (one of the 5 uppercase types above),
"importance" (float 0.0 to 1.0),
"confidence" (float 0.0 to 1.0),
"summary" (1-sentence description),
"reason" (short classification justification),
"contract" (object of details, e.g. for NOISE it is {{}}).

Contract fields per type:
- FINANCIAL: amount, currency, transaction_type (DEBIT/CREDIT), payment_channel (UPI/CARD/CASH/UNKNOWN), merchant
- ACTION: task_name, assignee, due_date
- FYI: event_name, event_time, description
- FACT: entity, attribute, value
- NOISE: {{}}
"""

ollama_url = "http://127.0.0.1:11434"
model_name = "qwen2.5:1.5b"

report_items = []

for idx, sig in enumerate(signals):
    message = sig.get("message", "")
    sender = sig.get("sender", "")
    source = sig.get("source", "")
    timestamp = sig.get("timestamp", "")
    
    prompt = build_prompt(message, sender, source, timestamp)
    
    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.0,
            "num_predict": 256
        }
    }
    
    print(f"Running signal {idx+1}/{len(signals)}: {message[:50]}...")
    start_time = time.time()
    
    try:
        # Using a very generous 90-second timeout to allow completion
        r = requests.post(f"{ollama_url}/api/generate", json=payload, timeout=90.0)
        duration = time.time() - start_time
        
        if r.status_code == 200:
            raw_response = r.json().get("response", "").strip()
            
            # Try parsing the json
            cleaned = raw_response
            if cleaned.startswith("```"):
                import re
                cleaned = re.sub(r"^```(?:json)?\n", "", cleaned)
                cleaned = re.sub(r"\n```$", "", cleaned)
                cleaned = cleaned.strip()
            
            try:
                parsed = json.loads(cleaned)
                parse_success = "SUCCESS"
            except Exception as pe:
                parsed = {"error": f"JSON parsing error: {pe}"}
                parse_success = "PARSE_FAILED"
        else:
            raw_response = f"Error: Ollama returned status {r.status_code}"
            parsed = {}
            parse_success = "HTTP_ERROR"
            duration = time.time() - start_time
            
    except Exception as e:
        duration = time.time() - start_time
        raw_response = f"Error calling Ollama: {e}"
        parsed = {}
        parse_success = "TIMEOUT/NETWORK_ERROR"
        
    report_items.append({
        "index": idx + 1,
        "signal_id": sig.get("signal_id"),
        "sender": sender,
        "message": message,
        "timestamp": timestamp,
        "duration": duration,
        "parse_success": parse_success,
        "prompt": prompt,
        "raw_response": raw_response,
        "parsed": parsed
    })

# Write the report
report_markdown = f"""# LOCAL QWEN 1.5B WHATSAPP SIGNAL BENCHMARK REPORT
**Date/Time**: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}  
**Model**: `qwen2.5:1.5b` (Local Ollama on CPU)  
**Total Signals Tested**: {len(report_items)}

---

## 1. Volumetric Speed Summary

| Signal Index | Signal ID | Message (Truncated) | Duration (sec) | Parse Status | Predicted Type |
|---|---|---|---|---|---|
"""

for item in report_items:
    pred_type = item["parsed"].get("signal_type", "N/A")
    msg_trunc = item["message"][:40] + "..." if len(item["message"]) > 40 else item["message"]
    report_markdown += f"| {item['index']} | {item['signal_id']} | `{msg_trunc}` | {item['duration']:.2f}s | `{item['parse_success']}` | `{pred_type}` |\n"

total_duration = sum(item["duration"] for item in report_items)
avg_duration = total_duration / len(report_items) if report_items else 0
success_count = sum(1 for item in report_items if item["parse_success"] == "SUCCESS")

report_markdown += f"""
### Key Metrics
* **Total Time**: {total_duration:.2f} seconds
* **Average Time per Signal**: {avg_duration:.2f} seconds
* **JSON Parse Success Rate**: {success_count}/{len(report_items)} ({success_count/len(report_items)*100:.1f}%)

---

## 2. Detailed Request & Response Trace
"""

for item in report_items:
    report_markdown += f"""
### Signal {item['index']} (ID: {item['signal_id']})
* **Sender**: `{item['sender']}`
* **Timestamp**: `{item['timestamp']}`
* **Message**: *"{item['message']}"*
* **Response Time**: `{item['duration']:.2f} seconds`
* **Parse Status**: `{item['parse_success']}`

#### Exact Prompt Passed:
```text
{item['prompt']}
```

#### Raw Model Response:
```json
{item['raw_response']}
```

#### Parsed Contract JSON:
```json
{json.dumps(item['parsed'], indent=2)}
```

---
"""

# Save report
os.makedirs("docs/v2/understanding_layer", exist_ok=True)
with open("docs/v2/understanding_layer/LLM_BENCHMARK_REPORT.md", "w") as f:
    f.write(report_markdown)

print("Benchmark report written to docs/v2/understanding_layer/LLM_BENCHMARK_REPORT.md")
