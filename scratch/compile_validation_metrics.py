# scratch/compile_validation_metrics.py

import json
import datetime
from collections import Counter
import re

def main():
    with open("scratch/validation_run_raw.json", "r") as f:
        data = json.load(f)

    dataset = data["dataset"]
    v1 = data["v1"]
    v2 = data["v2"]

    # 1. Overall Statistics
    total_signals = len(dataset)
    
    v1_stats = Counter(v["status"] for v in v1.values())
    v2_stats = Counter(v["status"] for v in v2.values())

    print("=" * 60)
    print("1. OVERALL STATISTICS")
    print("=" * 60)
    print(f"Total Signals Processed: {total_signals}")
    print("\n--- Version 2A.1 (Before) ---")
    for status, count in v1_stats.items():
        pct = (count / total_signals) * 100
        print(f"  {status}: {count} ({pct:.2f}%)")
    print("\n--- Version 2A.2 (After) ---")
    for status, count in v2_stats.items():
        pct = (count / total_signals) * 100
        print(f"  {status}: {count} ({pct:.2f}%)")

    # 2. Movement Analysis
    movements = {
        "REVIEW -> QUALIFIED": 0,
        "REJECTED -> REVIEW": 0,
        "REJECTED -> QUALIFIED": 0,
        "QUALIFIED -> REVIEW": 0,
        "QUALIFIED -> REJECTED": 0,
        "NO CHANGE": 0
    }
    movement_examples = {k: [] for k in movements.keys()}

    for s in dataset:
        sid = str(s["id"])
        s1 = v1[sid]["status"]
        s2 = v2[sid]["status"]
        
        m_key = f"{s1} -> {s2}"
        if s1 == s2:
            movements["NO CHANGE"] += 1
        elif m_key in movements:
            movements[m_key] += 1
            movement_examples[m_key].append(s)
        else:
            # e.g., REVIEW -> REJECTED
            pass

    print("\n" + "=" * 60)
    print("2. MOVEMENT ANALYSIS")
    print("=" * 60)
    for m_type, count in movements.items():
        print(f"  {m_type}: {count}")

    # 3. Family Context Impact
    # Family terms: Pradeep, Shobana, Charan, Chinicka, Chainicka, etc.
    family_names = ["pradeep", "shobana", "charan", "chinicka", "chainicka"]
    family_keywords = ["family", "parent", "parenting", "spouse", "wife", "kids", "child", "son", "daughter"]
    all_family_terms = family_names + family_keywords
    
    family_impacted_signals = []
    for s in dataset:
        sid = str(s["id"])
        msg_l = s["message"].lower()
        snd_l = s["sender"].lower()
        
        # Word boundary or simple match (to match agent logic: any substring matching)
        # Note: the agent logic is: any(term in msg_lower or term in sender_lower)
        if any(term in msg_l or term in snd_l for term in all_family_terms):
            family_impacted_signals.append(s)

    print("\n" + "=" * 60)
    print("3. FAMILY CONTEXT IMPACT")
    print("=" * 60)
    print(f"Total signals matching family context: {len(family_impacted_signals)}")
    print("Examples promoted due to family context:")
    promo_count = 0
    for s in family_impacted_signals:
        sid = str(s["id"])
        s1 = v1[sid]["status"]
        s2 = v2[sid]["status"]
        if s1 != s2 and s2 == "QUALIFIED":
            promo_count += 1
            print(f"  - [{s['source']}] {s['sender']}: '{s['message']}' ({s1} -> {s2})")
            if promo_count >= 10:
                break

    # 4. High Value Domains
    # Load high value domains from config
    with open("config/high_value_domains.json", "r") as hf:
        domains_cfg = json.load(hf)
    
    # Add other domains from user request: Government, Subscriptions, Appointments
    # Ensure they are represented
    domains_extended = {
        "education": domains_cfg.get("education", []),
        "medical": domains_cfg.get("medical", []),
        "insurance": domains_cfg.get("insurance", []),
        "finance": domains_cfg.get("finance", []),
        "travel": domains_cfg.get("travel", []),
        "utilities": domains_cfg.get("utilities", []),
        "employment": domains_cfg.get("employment", []),
        "government": ["govt", "aadhaar", "passport", "tax", "income tax", "pf ", "epfo", "pan card", "digilocker"],
        "subscriptions": ["netflix", "spotify", "prime video", "subscription", "autopay", "youtube premium", "renew subscription"],
        "appointments": ["appointment", "booking confirmed", "scheduled", "slot", "visit"]
    }

    domain_counts = {}
    for dom, keywords in domains_extended.items():
        found = []
        qualified = 0
        reviewed = 0
        rejected = 0
        
        for s in dataset:
            sid = str(s["id"])
            msg_l = s["message"].lower()
            snd_l = s["sender"].lower()
            if any(kw in msg_l or kw in snd_l for kw in keywords):
                found.append(s)
                status = v2[sid]["status"]
                if status == "QUALIFIED":
                    qualified += 1
                elif status == "REVIEW":
                    reviewed += 1
                elif status == "REJECTED":
                    rejected += 1
                    
        domain_counts[dom] = {
            "found": len(found),
            "qualified": qualified,
            "reviewed": reviewed,
            "rejected": rejected
        }

    print("\n" + "=" * 60)
    print("4. HIGH VALUE DOMAIN IMPACT")
    print("=" * 60)
    for dom, counts in domain_counts.items():
        print(f"Domain: {dom.upper():<15} | Found: {counts['found']:<3} | Qualified: {counts['qualified']:<3} | Reviewed: {counts['reviewed']:<3} | Rejected: {counts['rejected']:<3}")

    # 5. Financial Preservation Validation
    # Keywords: debit, credit, upi, spent, card, bill, statement, emi, payment
    fin_keywords = ["debit", "credit", "spent", "received", "card ending", "upi", "emi", "payment of", "bill", "invoice", "statement", "autopay"]
    fin_signals = []
    for s in dataset:
        msg_l = s["message"].lower()
        if any(kw in msg_l for kw in fin_keywords):
            fin_signals.append(s)

    fin_stats = Counter()
    rejected_fin = []
    for s in fin_signals:
        sid = str(s["id"])
        status = v2[sid]["status"]
        fin_stats[status] += 1
        if status == "REJECTED":
            rejected_fin.append(s)

    print("\n" + "=" * 60)
    print("5. FINANCIAL PRESERVATION VALIDATION")
    print("=" * 60)
    print(f"Total Financial Signals Found: {len(fin_signals)}")
    for status, count in fin_stats.items():
        print(f"  {status}: {count}")
    print(f"Rejected Financial Signals ({len(rejected_fin)}):")
    for s in rejected_fin[:20]:
        sid = str(s["id"])
        print(f"  - [{s['source']}] {s['sender']}: '{s['message']}' (Reason: {v2[sid]['reason']})")

    # 6. Review Queue Analysis
    review_signals = [s for s in dataset if v2[str(s["id"])]["status"] == "REVIEW"]
    review_senders = Counter(s["sender"] for s in review_signals)
    
    # Extract keywords
    words = []
    for s in review_signals:
        # Simple tokenization
        w_list = re.findall(r"\b\w{3,15}\b", s["message"].lower())
        # Filter out common stop words
        stops = {"the", "and", "for", "you", "your", "with", "this", "that", "from", "are", "have", "has", "was", "will"}
        words.extend([w for w in w_list if w not in stops])
    review_words = Counter(words)

    # Group classification (Badminton, Apartment, Community, etc.)
    group_counts = Counter()
    for s in review_signals:
        msg_l = s["message"].lower()
        if "badminton" in msg_l:
            group_counts["Badminton Group"] += 1
        elif any(kw in msg_l for kw in ["apartment", "association", "gate entry", "visitor alert"]):
            group_counts["Apartment/Community Group"] += 1
        elif "class" in msg_l or "school" in msg_l:
            group_counts["School Group/Circular"] += 1
        else:
            group_counts["Other Review"] += 1

    print("\n" + "=" * 60)
    print("6. REVIEW QUEUE ANALYSIS")
    print("=" * 60)
    print("Top 10 Senders in REVIEW:")
    for sender, count in review_senders.most_common(10):
        print(f"  {sender}: {count}")
    print("\nTop 15 Keywords in REVIEW:")
    for word, count in review_words.most_common(15):
        print(f"  {word}: {count}")
    print("\nGroup Breakdown in REVIEW:")
    for grp, count in group_counts.items():
        print(f"  {grp}: {count}")

    # 7. False Positive & False Negative Analysis (we will sample and categorize)
    qualified_signals = [s for s in dataset if v2[str(s["id"])]["status"] == "QUALIFIED"]
    rejected_signals = [s for s in dataset if v2[str(s["id"])]["status"] == "REJECTED"]

    print("\n" + "=" * 60)
    print("7. QUALIFIED SIGNALS PREVIEW (First 20 for manual categorization)")
    print("=" * 60)
    for i, s in enumerate(qualified_signals[:20]):
        sid = str(s["id"])
        print(f"[{i+1}] Sender: {s['sender']} | Msg: {s['message'][:80]} | Score: {v2[sid]['score']}")

    print("\n" + "=" * 60)
    print("8. REJECTED SIGNALS PREVIEW (First 20 for manual categorization)")
    print("=" * 60)
    for i, s in enumerate(rejected_signals[:20]):
        sid = str(s["id"])
        print(f"[{i+1}] Sender: {s['sender']} | Msg: {s['message'][:80]} | Reason: {v2[sid]['reason']}")

    # 9. Top Qualification Reasons
    reasons = Counter()
    for s in qualified_signals:
        sid = str(s["id"])
        # Determine why it got qualified
        msg_l = s["message"].lower()
        snd_l = s["sender"].lower()
        
        # Match checks
        is_fam = any(term in msg_l or term in snd_l for term in all_family_terms)
        is_dom = False
        matched_dom = []
        for dom, keywords in domains_extended.items():
            if any(kw in msg_l or kw in snd_l for kw in keywords):
                is_dom = True
                matched_dom.append(dom)
        
        if is_fam and is_dom:
            reasons["Family + Domain Boost"] += 1
        elif is_fam:
            reasons["Family Context Boost"] += 1
        elif is_dom:
            reasons[f"Domain Boost: {', '.join(matched_dom[:2])}"] += 1
        else:
            reasons["Base Score (No Boosts applied)"] += 1
            
    print("\n" + "=" * 60)
    print("9. TOP QUALIFICATION REASONS")
    print("=" * 60)
    for reason, count in reasons.most_common(20):
        print(f"  {reason}: {count}")

    # 10. Before vs After Examples (20 examples)
    print("\n" + "=" * 60)
    print("10. BEFORE VS AFTER EXAMPLES")
    print("=" * 60)
    count = 0
    for s in dataset:
        sid = str(s["id"])
        s1 = v1[sid]["status"]
        sc1 = v1[sid]["score"]
        s2 = v2[sid]["status"]
        sc2 = v2[sid]["score"]
        
        if s1 != s2:
            count += 1
            print(f"Example {count}:")
            print(f"  Signal:  [{s['source']}] {s['sender']}: '{s['message']}'")
            print(f"  2A.1:    Score {sc1} ({s1})")
            print(f"  2A.2:    Score {sc2} ({s2})")
            print(f"  Reason:  {'Family Context' if any(f in s['message'].lower() or f in s['sender'].lower() for f in all_family_terms) else 'Domain Boost / Financial Preservation'}")
            if count >= 20:
                break

if __name__ == "__main__":
    main()
