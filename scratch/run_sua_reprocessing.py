# scratch/run_sua_reprocessing.py

import os
import sys
import json
import re
from collections import Counter
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import SessionLocal, initialize_database
from storage.models.qualified_signal import QualifiedSignal
from storage.models.understood_signal import UnderstoodSignal
from services.signal_understanding_agent import SignalUnderstandingAgent

def main():
    initialize_database()
    db = SessionLocal()
    
    # 1. Load existing understood contracts for mock LLM responses
    print("Loading original understood contracts for LLM path replay...")
    original_contracts = {}
    for u in db.query(UnderstoodSignal).all():
        try:
            original_contracts[u.raw_signal_id] = json.loads(u.contract_json)
        except Exception:
            pass
            
    # 2. Clear old understood signals
    print("Clearing understood_signals table...")
    db.query(UnderstoodSignal).delete()
    db.commit()

    # 3. Load qualified signals
    qualified_signals = db.query(QualifiedSignal).filter(
        QualifiedSignal.qualification_status == "QUALIFIED"
    ).all()
    
    print(f"Loaded {len(qualified_signals)} qualified signals.")

    # 4. Patch _run_llm_path to return original contracts exactly as they were returned by the LLM
    agent = SignalUnderstandingAgent()
    
    def mock_run_llm_path(signal):
        raw_id = signal.signal_id
        if raw_id in original_contracts:
            return json.loads(json.dumps(original_contracts[raw_id]))
        else:
            return {
                "signal_id": signal.signal_id,
                "signal_type": "general",
                "classes": ["INFORMATION"],
                "domains": ["GENERAL"],
                "importance": "MEDIUM",
                "summary": signal.message[:100],
                "confidence": 0.5,
                "reason": "Default fallback",
                "entities": {},
                "routes": ["FyiAgent"],
                "raw_context": {
                    "source": signal.source,
                    "sender": signal.sender,
                    "timestamp": signal.timestamp.isoformat(),
                    "processing_path": "LLM",
                    "llm_model_used": "qwen2.5:1.5b"
                }
            }

    # Mock SupabaseRepo
    mock_supabase = MagicMock()
    mock_supabase.save_understood_signal.return_value = True

    print("Reprocessing all signals using patched LLM path and updated rules...")
    reprocessed_contracts = []
    
    with patch.object(agent, "_run_llm_path", mock_run_llm_path), \
         patch("services.signal_understanding_agent.SupabaseRepo", mock_supabase):
        for s in qualified_signals:
            try:
                contract = agent.process_signal(s, db)
                reprocessed_contracts.append((s, contract))
            except Exception as e:
                print(f"Failed to process signal {s.signal_id}: {e}")
                
        db.commit()

    print("Reprocessing complete. Starting Regression & Merchant Quality Validation...")
    run_regression_validation(qualified_signals, reprocessed_contracts, original_contracts)
    db.close()

def run_regression_validation(qualified_signals, reprocessed_contracts, original_contracts):
    total_reprocessed = len(reprocessed_contracts)
    financial_fp_after = 0
    
    amt_present_after = 0
    merc_present_after = 0
    financial_total = 0
    
    # Merchant Quality Metrics
    false_merchant_count = 0
    sender_id_count = 0
    numeric_artifact_count = 0
    currency_artifact_count = 0
    
    top_50_merchants = []
    
    # Checker functions for false merchants
    def is_sender_id(cand: str) -> bool:
        return bool(re.match(r"^[A-Za-z]{2}-[A-Za-z0-9]+-[A-Za-z]$", cand.strip()))

    def is_numeric_artifact(cand: str) -> bool:
        clean = cand.strip()
        if clean.isdigit():
            return True
        digit_count = sum(1 for c in clean if c.isdigit())
        if len(clean) > 0 and (digit_count / len(clean) > 0.4):
            return True
        if re.search(r"\b\d{4,}\b", clean):
            return True
        if re.search(r"x{2,}\d+", clean, re.IGNORECASE):
            return True
        if re.search(r"\*\d{3,}", clean):
            return True
        return False

    def is_stop_word_artifact(cand: str) -> bool:
        stop_words = {
            "rs", "inr", "credit alert", "debit alert", "balance", "upi", "transaction",
            "account", "reference", "alert", "bank", "payment", "vpa", "mobile", "ref",
            "dear customer", "yono", "avl bal", "credit", "debit", "statement", "amount",
            "successful", "yono by sbi", "rs.", "inr.", "your", "the", "a", "an", "to", "from", "at"
        }
        clean = cand.strip().lower()
        if clean in stop_words:
            return True
        for sw in stop_words:
            if clean == sw or clean.startswith(sw + " ") or clean.endswith(" " + sw):
                return True
        return False

    for q, c in reprocessed_contracts:
        if "FINANCIAL" in c.get("classes", []):
            financial_total += 1
            
            # Amount coverage
            amt_after = c.get("entities", {}).get("monetary_value", {}).get("amount")
            if amt_after is not None:
                amt_present_after += 1
                
            # Merchant check
            merchants = c.get("entities", {}).get("merchants", [])
            has_merchant = False
            if merchants and len(merchants) > 0 and merchants[0]:
                has_merchant = True
                merc_name = merchants[0]
                merc_present_after += 1
                
                # Check for false merchants
                is_false = False
                if is_sender_id(merc_name):
                    sender_id_count += 1
                    is_false = True
                elif is_numeric_artifact(merc_name):
                    numeric_artifact_count += 1
                    is_false = True
                elif is_stop_word_artifact(merc_name):
                    currency_artifact_count += 1
                    is_false = True
                    
                if is_false:
                    false_merchant_count += 1
                    
                # Collect top 50 merchants
                if len(top_50_merchants) < 50:
                    top_50_merchants.append({
                        "id": q.signal_id,
                        "raw_message": q.message.replace("\n", " "),
                        "merchant_name": merc_name,
                        "merchant_type": "Institution" if merc_name in ["AMAZON", "SWIGGY", "HDFC_ERGO", "SBI_CARDS", "FLIPKART", "PHONEPE", "GOOGLE_PLAY", "PAYTM"] else "Other",
                        "merchant_confidence": c.get("entities", {}).get("merchant_confidence", 0.0),
                        "status": "INCORRECT" if is_false else "CORRECT"
                    })

    # Calculations
    amt_cov_after = (amt_present_after / financial_total * 100) if financial_total else 0
    merc_presence_pct = (merc_present_after / financial_total * 100) if financial_total else 0
    
    # Accuracy definition
    correct_merchants = merc_present_after - false_merchant_count
    merc_accuracy_pct = (correct_merchants / merc_present_after * 100) if merc_present_after else 0

    # Write report
    report_path = "signal_understanding_remediation_v2.md"
    with open(report_path, "w") as f:
        f.write("# Signal Understanding Agent: Merchant Quality & Sprint Validation Report\n\n")
        
        f.write("## 1. Executive Summary\n\n")
        f.write("| Metric | Value | Target | Status |\n")
        f.write("| :--- | :--- | :--- | :--- |\n")
        f.write(f"| **Merchant Presence %** | {merc_presence_pct:.2f}% | Informational | - |\n")
        f.write(f"| **Merchant Accuracy %** | {merc_accuracy_pct:.2f}% | >= 90% | {'PASS' if merc_accuracy_pct >= 90.0 else 'FAIL'} |\n")
        f.write(f"| **Amount Extraction Coverage** | {amt_cov_after:.2f}% | >= 99% | {'PASS' if amt_cov_after >= 99.0 else 'FAIL'} |\n")
        f.write(f"| **False Merchant Count** | {false_merchant_count} | 0 | {'PASS' if false_merchant_count == 0 else 'FAIL'} |\n")
        f.write(f"| **Sender ID Merchants** | {sender_id_count} | 0 | {'PASS' if sender_id_count == 0 else 'FAIL'} |\n")
        f.write(f"| **Numeric Artifact Merchants** | {numeric_artifact_count} | 0 | {'PASS' if numeric_artifact_count == 0 else 'FAIL'} |\n")
        f.write(f"| **Currency Artifact Merchants** | {currency_artifact_count} | 0 | {'PASS' if currency_artifact_count == 0 else 'FAIL'} |\n\n")

        f.write("## 2. Top 50 Merchant Extractions\n\n")
        f.write("| Signal ID | Raw Message Snippet | Extracted Merchant | Merchant Type | Confidence | Status |\n")
        f.write("| --- | --- | --- | --- | --- | --- |\n")
        for m in top_50_merchants:
            f.write(f"| {m['id']} | *{m['raw_message'][:80]}* | {m['merchant_name']} | {m['merchant_type']} | {m['merchant_confidence']:.2f} | {m['status']} |\n")
        f.write("\n")

        f.write("## 3. Exit Criteria Verdict\n\n")
        
        success = (merc_accuracy_pct >= 90.0 and 
                   false_merchant_count == 0 and 
                   sender_id_count == 0 and 
                   numeric_artifact_count == 0 and 
                   currency_artifact_count == 0 and 
                   amt_cov_after >= 99.0)
                   
        if success:
            f.write("### **FINAL VERDICT: SIGNAL_UNDERSTANDING_FULLY_LOCKED**\n")
        else:
            f.write("### **FINAL VERDICT: MERCHANT_REMEDIATION_REQUIRED**\n")

    print(f"Validation summary report written to {report_path}")

if __name__ == "__main__":
    main()
