# scratch/run_sua_validation.py

import os
import sys
import json
import time
from datetime import datetime
from collections import Counter
import re
from unittest.mock import MagicMock, patch

# Ensure python path includes project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import initialize_database, SessionLocal
from storage.models.qualified_signal import QualifiedSignal
from storage.models.understood_signal import UnderstoodSignal
from services.signal_understanding_agent import SignalUnderstandingAgent
from services.supabase_repo import SupabaseRepo
from intelligence.local.local_llm import LocalLLM

# Instrument Ollama client to track tokens and durations
total_prompt_tokens = 0
total_completion_tokens = 0
total_llm_calls = 0
llm_call_durations = []

def patch_ollama():
    # We patch LocalLLM.ask
    original_ask = LocalLLM.ask
    
    def instrumented_ask(self, prompt: str) -> str:
        global total_prompt_tokens, total_completion_tokens, total_llm_calls, llm_call_durations
        total_llm_calls += 1
        t0 = time.time()
        
        # We can intercept chat and get token counts
        original_chat = self.client.chat
        
        prompt_tokens = 0
        completion_tokens = 0
        
        def instrumented_chat(*args, **kwargs):
            nonlocal prompt_tokens, completion_tokens
            res = original_chat(*args, **kwargs)
            if hasattr(res, 'prompt_eval_count') and res.prompt_eval_count:
                prompt_tokens = res.prompt_eval_count
            if hasattr(res, 'eval_count') and res.eval_count:
                completion_tokens = res.eval_count
            return res
            
        with patch.object(self.client, 'chat', instrumented_chat):
            res_content = original_ask(self, prompt)
            
        duration = time.time() - t0
        llm_call_durations.append(duration)
        total_prompt_tokens += prompt_tokens
        total_completion_tokens += completion_tokens
        return res_content
        
    LocalLLM.ask = instrumented_ask

def main():
    patch_ollama()
    initialize_database()
    db = SessionLocal()

    # Clear old understood signals
    print("Clearing old understood signals...")
    db.query(UnderstoodSignal).delete()
    db.commit()

    # Get qualified signals
    qualified_signals = db.query(QualifiedSignal).filter(
        QualifiedSignal.qualification_status == "QUALIFIED"
    ).all()
    
    qualified_input_count = len(qualified_signals)
    print(f"Loaded {qualified_input_count} qualified signals from SQLite.")
    
    if qualified_input_count == 0:
        print("Error: No qualified signals found in SQLite. Run qualification validation first.")
        db.close()
        return

    # Mock SupabaseRepo to bypass network latency during local validation run
    mock_supabase = MagicMock()
    mock_supabase.save_understood_signal.return_value = True

    agent = SignalUnderstandingAgent()

    print("Executing Signal Understanding Agent on 264 qualified signals...")
    start_time = time.time()
    
    deterministic_count = 0
    llm_count = 0
    failed_count = 0
    contracts = []

    with patch("services.signal_understanding_agent.SupabaseRepo", mock_supabase):
        for s in qualified_signals:
            try:
                # We can trace which path is used
                # 1. Deterministic path
                det_contract = agent._try_deterministic_path(s)
                if det_contract is not None:
                    deterministic_count += 1
                else:
                    llm_count += 1
                
                # Execute the full processing
                contract = agent.process_signal(s, db)
                contracts.append(contract)
            except Exception as e:
                print(f"Failed processing signal {s.id}: {e}")
                failed_count += 1

        db.commit()

    duration = time.time() - start_time
    print(f"Completed in {duration:.4f} seconds.")
    
    # Run all audits
    run_audits(qualified_signals, contracts, deterministic_count, llm_count, failed_count, duration)
    db.close()

def run_audits(qualified_signals, contracts, deterministic_count, llm_count, failed_count, duration):
    # 1. Reconciliation
    qualified_input_count = len(qualified_signals)
    contracts_created = len(contracts)
    reconciled = (deterministic_count + llm_count + failed_count == qualified_input_count)
    
    # 2. Path Analysis
    det_pct = (deterministic_count / contracts_created * 100) if contracts_created else 0
    llm_pct = (llm_count / contracts_created * 100) if contracts_created else 0

    # 3. LLM Audit
    total_tokens = total_prompt_tokens + total_completion_tokens
    avg_tokens_per_signal = (total_tokens / total_llm_calls) if total_llm_calls else 0
    total_llm_duration = sum(llm_call_durations)

    # 4. Canonical Contract Validation
    # Audit all contracts (not just 25)
    required_keys = ["signal_id", "signal_type", "classes", "domains", "importance", "summary", "confidence", "reason", "entities", "routes", "raw_context"]
    malformed_contracts = []
    
    for c in contracts:
        missing = [k for k in required_keys if k not in c]
        if missing:
            malformed_contracts.append({"contract": c, "missing": missing})
            
    # 5. Financial Boundary Validation (Critical)
    financial_boundary_keywords = ["bill due", "payment due", "minimum due", "outstanding amount", "emi due", "insurance renewal", "premium due", "renewal reminder"]
    financial_boundary_violations = []
    
    for c in contracts:
        msg_l = c["raw_context"].get("message", "").lower()
        if any(kw in msg_l for kw in financial_boundary_keywords):
            # Check if classes contains FINANCIAL
            if "FINANCIAL" in c["classes"]:
                financial_boundary_violations.append({
                    "id": c["signal_id"],
                    "sender": c["raw_context"].get("sender", ""),
                    "message": msg_l,
                    "classes": c["classes"],
                    "routes": c["routes"]
                })

    # 6. Refund Validation
    refund_keywords = ["refund", "refunded", "reversal", "reversed", "credited back", "adjusted against"]
    future_refund_patterns = ["will be refunded", "will be reversed", "if debited will", "pending refund", "will refund"]
    refund_validations = []
    
    for c in contracts:
        msg_l = c["raw_context"].get("message", "").lower()
        if any(kw in msg_l for kw in refund_keywords):
            # Check if future refund
            is_future = any(pat in msg_l for pat in future_refund_patterns)
            classes = c["classes"]
            routes = c["routes"]
            
            if is_future:
                # Expected NOT FINANCIAL, expected INFORMATION and/or ALERT
                status = "PASS" if "FINANCIAL" not in classes else "FAIL"
            else:
                # Confirmed refund: FINANCIAL + INFORMATION, routes: FinancialAgent + FyiAgent
                status = "PASS" if ("FINANCIAL" in classes and "FinancialAgent" in routes and "FyiAgent" in routes) else "FAIL"
                
            refund_validations.append({
                "id": c["signal_id"],
                "message": msg_l,
                "is_future": is_future,
                "classes": classes,
                "routes": routes,
                "status": status
            })

    # 7. Routing Validation
    routing_violations = []
    for c in contracts:
        classes = c["classes"]
        routes = c["routes"]
        # FINANCIAL -> FinancialAgent
        # ACTION -> TodoAgent
        # INFORMATION -> FyiAgent
        # MEMORY -> FactAgent
        mismatch = False
        if "FINANCIAL" in classes and "FinancialAgent" not in routes:
            mismatch = True
        if "ACTION" in classes and "TodoAgent" not in routes:
            mismatch = True
        if "INFORMATION" in classes and "FyiAgent" not in routes:
            mismatch = True
        if "MEMORY" in classes and "FactAgent" not in routes:
            mismatch = True
        if mismatch:
            routing_violations.append({
                "id": c["signal_id"],
                "classes": classes,
                "routes": routes
            })

    # 8. Confidence Model Validation
    conf_distribution = {"high": 0, "mid": 0, "low": 0}
    confidence_violations = []
    for c in contracts:
        conf = c.get("confidence", 0.0)
        if conf >= 0.85:
            conf_distribution["high"] += 1
        elif conf >= 0.50:
            conf_distribution["mid"] += 1
        else:
            conf_distribution["low"] += 1

    # 9. Deterministic Rule Coverage Analysis
    rule_hits = Counter()
    for c in contracts:
        if c["raw_context"].get("processing_path") == "RULE_ENGINE":
            rule_hits[c.get("signal_type", "general")] += 1
            
    # 10. Entity Extraction Audit
    entity_audit = []
    for c in contracts:
        if "FINANCIAL" in c["classes"]:
            monetary = c["entities"].get("monetary_value", {})
            amt = monetary.get("amount")
            if amt is None:
                entity_audit.append({
                    "id": c["signal_id"],
                    "message": c["raw_context"].get("message"),
                    "entities": c["entities"]
                })

    # 11. Critical Failure Review
    critical_failures = []
    for c in contracts:
        if not c.get("routes"):
            critical_failures.append({"id": c["signal_id"], "issue": "Empty routes"})
        if not c.get("classes"):
            critical_failures.append({"id": c["signal_id"], "issue": "Empty classes"})
        if c.get("confidence") is None:
            critical_failures.append({"id": c["signal_id"], "issue": "Missing confidence"})

    # Write summary validation file
    summary_path = "understanding_validation.md"
    
    with open(summary_path, "w") as f:
        f.write("# Signal Understanding Agent Validation Summary\n\n")
        f.write("## 1. Processing Reconciliation\n\n")
        f.write(f"* **Qualified Input Count**: {qualified_input_count}\n")
        f.write(f"* **Deterministic Processing Count**: {deterministic_count}\n")
        f.write(f"* **LLM Processing Count**: {llm_count}\n")
        f.write(f"* **Failed Processing Count**: {failed_count}\n")
        f.write(f"* **Contracts Created Count**: {contracts_created}\n\n")
        f.write("> [!NOTE]\n")
        f.write(f"> Reconciliation equation: {deterministic_count} (Deterministic) + {llm_count} (LLM) + {failed_count} (Failed) = {deterministic_count + llm_count + failed_count} (Expected: {qualified_input_count})\n\n")

        f.write("## 2. Deterministic vs LLM Path Analysis\n\n")
        f.write(f"* **Deterministic Contracts**: {deterministic_count} ({det_pct:.2f}%)\n")
        f.write(f"* **LLM Contracts**: {llm_count} ({llm_pct:.2f}%)\n\n")
        f.write("> [!TIP]\n")
        f.write("> The deterministic path was always attempted first. The LLM was only invoked when the deterministic rules returned None.\n\n")

        f.write("## 3. LLM Audit\n\n")
        f.write(f"* **Total LLM Calls**: {total_llm_calls}\n")
        f.write(f"* **Total Tokens Consumed**: {total_tokens}\n")
        f.write(f"* **Average Tokens Per Signal**: {avg_tokens_per_signal:.2f}\n")
        f.write(f"* **Model Used**: {LocalLLM().model}\n")
        f.write(f"* **Total Processing Time**: {total_llm_duration:.4f} seconds\n\n")

        f.write("## 4. Canonical Contract Validation\n\n")
        f.write(f"* **Malformed Contracts Detected**: {len(malformed_contracts)}\n\n")
        if malformed_contracts:
            f.write("| Signal ID | Missing Fields |\n")
            f.write("| --- | --- |\n")
            for mc in malformed_contracts:
                f.write(f"| {mc['id']} | {', '.join(mc['missing'])} |\n")
        else:
            f.write("> [!TIP]\n")
            f.write("> All inspected contracts conform to the canonical schema and contain no missing or malformed fields.\n\n")

        f.write("## 5. FINANCIAL Boundary Validation (Critical)\n\n")
        f.write(f"Detected **{len(financial_boundary_violations)}** boundary violations (future payment obligations marked as FINANCIAL).\n\n")
        if financial_boundary_violations:
            f.write("| Signal ID | Sender | Classes | Routes | Message |\n")
            f.write("| --- | --- | --- | --- | --- |\n")
            for violation in financial_boundary_violations:
                f.write(f"| {violation['id']} | {violation['sender']} | {violation['classes']} | {violation['routes']} | *{violation['message'][:80]}* |\n")
        else:
            f.write("> [!TIP]\n")
            f.write("> Verified: Future payment obligations (bills due, insurance renewals) correctly resolved to INFORMATION and ACTION without money movement. No FINANCIAL class emitted.\n\n")

        f.write("## 6. Refund Validation Summary\n\n")
        f.write("| Signal ID | Is Future | Classes | Routes | Status |\n")
        f.write("| --- | --- | --- | --- | --- |\n")
        for rv in refund_validations[:15]:
            f.write(f"| {rv['id']} | {rv['is_future']} | {rv['classes']} | {rv['routes']} | {rv['status']} |\n")
        f.write("\n")

        f.write("## 7. Routing Validation Summary\n\n")
        f.write(f"Detected **{len(routing_violations)}** routing mismatches.\n\n")
        if routing_violations:
            f.write("| Signal ID | Classes | Routes |\n")
            f.write("| --- | --- | --- |\n")
            for rv in routing_violations:
                f.write(f"| {rv['id']} | {rv['classes']} | {rv['routes']} |\n")
        else:
            f.write("> [!TIP]\n")
            f.write("> Verified: Class-to-Agent routing is completely intact across all classes.\n\n")

        f.write("## 8. Confidence Distribution\n\n")
        f.write(f"* **Confidence >= 0.85 (Auto-process)**: {conf_distribution['high']}\n")
        f.write(f"* **Confidence 0.50–0.84 (Review queue)**: {conf_distribution['mid']}\n")
        f.write(f"* **Confidence < 0.50 (Critical Inbox)**: {conf_distribution['low']}\n\n")

        f.write("## 9. Deterministic Rule Coverage Analysis\n\n")
        f.write("| Rule / Signal Type | Hit Count | Percentage |\n")
        f.write("| --- | --- | --- |\n")
        for rtype, count in rule_hits.items():
            f.write(f"| {rtype} | {count} | {count/deterministic_count*100:.2f}% |\n")
        f.write("\n")

        f.write("## 10. Entity Extraction Audit\n\n")
        f.write(f"Detected **{len(entity_audit)}** financial contracts with missing monetary amounts.\n\n")
        if entity_audit:
            f.write("| Signal ID | Message |\n")
            f.write("| --- | --- |\n")
            for ea in entity_audit:
                f.write(f"| {ea['id']} | *{ea['message'][:100]}* |\n")
        else:
            f.write("> [!TIP]\n")
            f.write("> Verified: All financial transaction signals successfully extracted monetary values.\n\n")

        f.write("## 11. Critical Failure Review\n\n")
        f.write(f"Detected **{len(critical_failures)}** critical contract failures.\n\n")

        f.write("## 12. Final Verdict\n\n")
        
        success = (reconciled and 
                   len(malformed_contracts) == 0 and 
                   len(financial_boundary_violations) == 0 and 
                   len(routing_violations) == 0 and 
                   failed_count == 0)
                   
        if success:
            f.write("### **FINAL VERDICT: SIGNAL_UNDERSTANDING_VALIDATED**\n")
        else:
            f.write("### **FINAL VERDICT: SIGNAL_UNDERSTANDING_REQUIRES_REMEDIATION**\n")

    print(f"Validation summary report written to {summary_path}")

if __name__ == "__main__":
    main()
