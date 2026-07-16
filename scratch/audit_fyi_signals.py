import os
import sys
import re
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions

def main():
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        print("Error: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set.")
        sys.exit(1)
        
    options = ClientOptions(schema="jarvis_insights_schemav1")
    client: Client = create_client(url, key, options=options)
    
    print("Fetching all FYI signals from understood_signals...")
    # Fetch signal_type = 'FYI'
    # We select fields: id, signal_type, confidence, summary, qualified_signals(message, sender, source, timestamp)
    res = client.table("understood_signals").select(
        "id, signal_type, confidence, summary, qualified_signals:qualified_signal_id(message, sender, source, timestamp)"
    ).eq("signal_type", "FYI").execute()
    
    fyi_records = res.data
    total_fyi = len(fyi_records)
    print(f"Found {total_fyi} FYI signals.")
    
    # Categorization keywords
    school_keywords = [
        "school", "parent", "student", "fee", "homework", "project", 
        "exam", "class", "teacher", "rehearsal", "annual day", "sports day", 
        "assignment", "circular", "children", "attendance", "admission"
    ]
    medical_keywords = [
        "medical", "hospital", "doctor", "claim", "tpa", "health", 
        "pharmacy", "apollo", "medicine", "lab test", "report", "prescription",
        "phlebotomist", "treatment", "clinic"
    ]
    insurance_keywords = [
        "insurance", "policy", "premium", "lic", "hdfc ergo", "renewal", "coverfox",
        "insurer", "settlement"
    ]
    travel_keywords = [
        "travel", "flight", "train", "booking", "ticket", "pnr", "cab", 
        "uber", "ola", "irctc", "boarding", "hotel", "indigo", "air india"
    ]
    
    # Action indicators to help analyze which ones should be ACTION
    action_keywords = [
        "submit", "pay", "bring", "attend", "join", "register", "upload", 
        "complete", "renew", "update", "sign", "verify", "provide", "carry", "wear",
        "deadline", "due date", "last date", "tomorrow", "before", "on or before"
    ]
    
    categories = {
        "School/Education": [],
        "Medical": [],
        "Insurance": [],
        "Travel": [],
        "Other": []
    }
    
    for r in fyi_records:
        qs = r.get("qualified_signals") or {}
        message = qs.get("message") or ""
        sender = qs.get("sender") or ""
        msg_lower = message.lower()
        sender_lower = sender.lower()
        
        # Determine category
        is_school = any(kw in msg_lower or kw in sender_lower for kw in school_keywords)
        is_medical = any(kw in msg_lower or kw in sender_lower for kw in medical_keywords)
        is_insurance = any(kw in msg_lower or kw in sender_lower for kw in insurance_keywords)
        is_travel = any(kw in msg_lower or kw in sender_lower for kw in travel_keywords)
        
        # We classify mutually exclusively for counting purposes (prioritizing School -> Medical -> Insurance -> Travel)
        record_info = {
            "id": r["id"],
            "message": message,
            "sender": sender,
            "source": qs.get("source"),
            "timestamp": qs.get("timestamp"),
            "summary": r.get("summary"),
            "confidence": r.get("confidence"),
            "has_action_indicators": [kw for kw in action_keywords if re.search(r"\b" + re.escape(kw) + r"\b", msg_lower)]
        }
        
        if is_school:
            categories["School/Education"].append(record_info)
        elif is_medical:
            categories["Medical"].append(record_info)
        elif is_insurance:
            categories["Insurance"].append(record_info)
        elif is_travel:
            categories["Travel"].append(record_info)
        else:
            categories["Other"].append(record_info)
            
    # Write markdown report
    report_path = "/home/prad/.gemini/antigravity-ide/brain/69052cde-91ec-4243-874c-9ad54bd264f2/fyi_audit_results.md"
    print(f"Generating audit report at {report_path}...")
    
    with open(report_path, "w") as f:
        f.write("# FYI Signals Audit Results\n\n")
        f.write(f"Analyzed **{total_fyi}** signals currently classified as `FYI` in the `understood_signals` table.\n\n")
        
        # Summary Table
        f.write("## 1. Category Distribution\n\n")
        f.write("| Category | Count | Action-Candidate Count* | Description |\n")
        f.write("| :--- | :--- | :--- | :--- |\n")
        
        for cat_name, records in categories.items():
            action_candidates = sum(1 for r in records if len(r["has_action_indicators"]) > 0)
            pct = (len(records) / total_fyi * 100) if total_fyi > 0 else 0
            f.write(f"| **{cat_name}** | {len(records)} ({pct:.1f}%) | {action_candidates} | Signals matching {cat_name.lower()} keywords. |\n")
        f.write("\n*\*Action-Candidate Count represents signals containing one or more action-related keywords (e.g. submit, pay, bring, tomorrow, deadline).* \n\n")
        
        # School/Education Dump
        f.write("## 2. Dump of School/Education FYI Signals\n\n")
        f.write(f"Total found: **{len(categories['School/Education'])}** signals.\n\n")
        if not categories["School/Education"]:
            f.write("No School/Education FYI signals found.\n")
        else:
            for idx, r in enumerate(categories["School/Education"]):
                action_str = f"Yes (matched: {', '.join(r['has_action_indicators'])})" if r["has_action_indicators"] else "No"
                f.write(f"### {idx+1}. Sender: `{r['sender']}` | Action Candidate: **{action_str}**\n")
                f.write(f"- **Message**: {r['message'].strip()}\n")
                f.write(f"- **Summary**: *{r['summary']}*\n\n")
                f.write("---\n\n")
                
        # Medical, Insurance, Travel Examples
        for cat_name in ["Medical", "Insurance", "Travel"]:
            f.write(f"## 3. Examples of {cat_name} FYI Signals\n\n")
            cat_records = categories[cat_name]
            f.write(f"Total found: **{len(cat_records)}** signals. Showing up to 10 examples:\n\n")
            if not cat_records:
                f.write("No signals found in this category.\n\n")
            else:
                for idx, r in enumerate(cat_records[:10]):
                    action_str = f"Yes (matched: {', '.join(r['has_action_indicators'])})" if r["has_action_indicators"] else "No"
                    f.write(f"### {idx+1}. Sender: `{r['sender']}` | Action Candidate: **{action_str}**\n")
                    f.write(f"- **Message**: {r['message'].strip()}\n")
                    f.write(f"- **Summary**: *{r['summary']}*\n\n")
                    f.write("---\n\n")
                    
    print("Report generated successfully.")

if __name__ == "__main__":
    main()
