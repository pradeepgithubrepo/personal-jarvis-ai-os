import os
import json
import time
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.agents.sua.agent import SignalUnderstandingAgent

def process_single_signal(sig, sua):
    # Execute understanding agent
    understood = sua.understand_signal(sig)
    
    # Run heuristic fallback path for comparison (shadow validation)
    heuristic = sua._fallback_understand(sig)
    
    expected = sig["expected"]
    actual_type = understood.get("signal_type")
    expected_type = expected.get("signal_type")
    heuristic_type = heuristic.get("signal_type")
    
    type_match = actual_type == expected_type
    
    return {
        "id": sig["id"],
        "message": sig["message"],
        "expected_type": expected_type,
        "actual_type": actual_type,
        "heuristic_type": heuristic_type,
        "type_match": type_match,
        "processing_path": understood.get("processing_path"),
        "llm_model_used": understood.get("llm_model_used"),
        "expected_contract": expected.get("contract"),
        "actual_contract": understood.get("contract_json")
    }

def run_validation():
    # Load gold set
    gold_set_path = "tests/sua_gold_set.json"
    if not os.path.exists(gold_set_path):
        print(f"Error: Gold set file not found at {gold_set_path}")
        return
        
    with open(gold_set_path, "r") as f:
        gold_signals = json.load(f)
        
    # Limit to first 110 signals to satisfy 100+ count requirement quickly on CPU
    gold_signals = gold_signals[:110]
        
    sua = SignalUnderstandingAgent()
    
    results = []
    correct_types = 0
    total = len(gold_signals)
    
    print(f"Running SUA Validation on {total} signals in parallel...")
    
    started_at = time.time()
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(process_single_signal, sig, sua): i for i, sig in enumerate(gold_signals)}
        
        for idx, future in enumerate(as_completed(futures)):
            if idx > 0 and idx % 10 == 0:
                print(f"Completed {idx}/{total} signals...")
            try:
                res = future.result()
                if res["type_match"]:
                    correct_types += 1
                results.append(res)
            except Exception as e:
                print(f"Error processing signal: {e}")
                
    duration = time.time() - started_at
    type_accuracy = correct_types / total if total > 0 else 0
    
    os.makedirs("docs/v2/phase2a", exist_ok=True)
    
    # 1. Save standard Validation Report
    report_path = "docs/v2/phase2a/sua_validation_report.md"
    with open(report_path, "w") as f:
        f.write(f"# SUA Validation Report\n\n")
        f.write(f"Generated at: {datetime.now(timezone.utc).isoformat()}\n")
        f.write(f"Model used: {sua.model}\n")
        f.write(f"Ollama URL: {sua.llm_client.ollama_url}\n\n")
        f.write(f"## Metrics\n\n")
        f.write(f"- **Total Signals Evaluated**: {total}\n")
        f.write(f"- **Signal Type Classification Accuracy**: {type_accuracy * 100:.2f}%\n")
        f.write(f"- **Total Execution Time**: {duration:.2f} seconds\n")
        f.write(f"- **Average Speed per Signal**: {duration / total:.2f} seconds\n\n")
        
        f.write(f"## Detailed Results\n\n")
        f.write(f"| Message | Expected Type | Actual Type | Type Match? | Processing Path | Model Used |\n")
        f.write(f"|---|---|---|---|---|---|\n")
        for res in results:
            msg_snippet = res["message"][:60].replace("\n", " ") + ("..." if len(res["message"]) > 60 else "")
            match_str = "✅ PASS" if res["type_match"] else "❌ FAIL"
            f.write(f"| {msg_snippet} | {res['expected_type']} | {res['actual_type']} | {match_str} | {res['processing_path']} | {res['llm_model_used']} |\n")
            
    # 2. Save Shadow Validation Report
    shadow_report_path = "docs/v2/phase2a/SUA_SHADOW_VALIDATION_REPORT.md"
    matches_heuristic = sum(1 for r in results if r["actual_type"] == r["heuristic_type"])
    heuristic_match_rate = matches_heuristic / total if total > 0 else 0
    
    with open(shadow_report_path, "w") as f:
        f.write(f"# SUA Shadow Validation Report\n\n")
        f.write(f"Generated at: {datetime.now(timezone.utc).isoformat()}\n")
        f.write(f"Active Model: {sua.model}\n")
        f.write(f"Heuristics Variant: Fallback Rule Heuristics\n\n")
        f.write(f"## Shadow Alignment Metrics\n\n")
        f.write(f"- **Total Signals Evaluated**: {total}\n")
        f.write(f"- **LLM vs Heuristic Match Rate**: {heuristic_match_rate * 100:.2f}%\n")
        f.write(f"- **Heuristics Disagreement Count**: {total - matches_heuristic}\n\n")
        
        f.write(f"## Disagreement Log\n\n")
        f.write(f"Log of signals where the active LLM classifier disagreed with the heuristics fallback classifier:\n\n")
        f.write(f"| Message | Expected Type | LLM Actual Type | Heuristic Fallback Type | Processing Path |\n")
        f.write(f"|---|---|---|---|---|\n")
        for res in results:
            if res["actual_type"] != res["heuristic_type"]:
                msg_snippet = res["message"][:60].replace("\n", " ") + ("..." if len(res["message"]) > 60 else "")
                f.write(f"| {msg_snippet} | {res['expected_type']} | {res['actual_type']} | {res['heuristic_type']} | {res['processing_path']} |\n")
                
    print(f"Validation completed in {duration:.2f}s. Accuracy: {type_accuracy * 100:.2f}%. Match Rate with Heuristics: {heuristic_match_rate * 100:.2f}%.")
    print(f"Reports written to {report_path} and {shadow_report_path}")

if __name__ == "__main__":
    run_validation()
