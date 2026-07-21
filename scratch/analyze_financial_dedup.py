import os
import json
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions

def main():
    load_dotenv()
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    opts = ClientOptions(schema="jarvis_insights_schemav1")
    client = create_client(url, key, options=opts)

    print("Fetching data...")
    txs = client.table("financial_transactions").select("*").execute().data or []
    evidence = client.table("transaction_evidence").select("*").execute().data or []
    routes = client.table("signal_routes").select("*").eq("agent_name", "financial_agent").execute().data or []
    understood = client.table("understood_signals").select("id, summary, contract_json").execute().data or []

    print(f"Loaded:")
    print(f"  - {len(txs)} transactions in financial_transactions")
    print(f"  - {len(evidence)} evidence records in transaction_evidence")
    print(f"  - {len(routes)} financial agent routes")

    # Mappings
    tx_map = {t["transaction_id"]: t for t in txs}
    us_map = {u["id"]: u for u in understood}

    # Count transaction sources
    tx_sources = {}
    for t in txs:
        src = t["source"]
        tx_sources[src] = tx_sources.get(src, 0) + 1
    
    print("\n--- financial_transactions Source Distribution ---")
    for src, cnt in tx_sources.items():
        print(f"  - {src}: {cnt}")

    # Count evidence sources
    ev_sources = {}
    for ev in evidence:
        src = ev["source"]
        ev_sources[src] = ev_sources.get(src, 0) + 1
    
    print("\n--- transaction_evidence Source Distribution ---")
    for src, cnt in ev_sources.items():
        print(f"  - {src}: {cnt}")

    # Deduplication Details:
    # Let's inspect the evidence records. Every record in transaction_evidence represents a signal 
    # that was deduplicated (matched to an existing transaction).
    # Let's map evidence by transaction_id to see which transactions have which evidence.
    ev_by_tx = {}
    for ev in evidence:
        tx_id = ev["transaction_id"]
        ev_by_tx.setdefault(tx_id, []).append(ev)

    print("\n--- Deduplication Analysis ---")
    # Let's look at the sources of the matched pairs (Existing Source vs. Evidence Source)
    pairs = {}
    for tx_id, ev_list in ev_by_tx.items():
        tx = tx_map.get(tx_id)
        if not tx:
            continue
        tx_src = tx["source"]
        for ev in ev_list:
            ev_src = ev["source"]
            key = (tx_src, ev_src)
            pairs[key] = pairs.get(key, 0) + 1

    print("Precedence Matches (Existing Transaction Source vs. Duplicate Signal Source):")
    for (tx_src, ev_src), count in sorted(pairs.items()):
        print(f"  - Existing: {tx_src:<20} | Duplicate Signal: {ev_src:<20} | Count: {count}")

    # Let's check for any anomalies, e.g. where the duplicate signal was GPAY_PDF or BANK_STATEMENT_PDF
    # but the existing transaction was SMS. That would mean promotion didn't happen!
    anomalies = []
    for tx_id, ev_list in ev_by_tx.items():
        tx = tx_map.get(tx_id)
        if not tx:
            continue
        tx_src = tx["source"]
        for ev in ev_list:
            ev_src = ev["source"]
            # Precedence: SMS = 1, GPAY_PDF = 2, BANK_STATEMENT_PDF = 3
            prec = {"SMS": 1, "GPAY_PDF": 2, "BANK_STATEMENT_PDF": 3}
            if prec.get(ev_src, 1) > prec.get(tx_src, 1):
                anomalies.append({
                    "tx_id": tx_id,
                    "existing_source": tx_src,
                    "duplicate_source": ev_src,
                    "amount": tx["amount"],
                    "date": tx["event_date"],
                    "ref": tx["reference_number"],
                    "ev_ref": ev["reference_number"]
                })

    print(f"\nAnomalies where a higher precedence signal was deduplicated under a lower precedence transaction: {len(anomalies)}")
    for an in anomalies[:10]:
        print(f"  - Tx ID: {an['tx_id']} | Existing: {an['existing_source']} | Duplicate: {an['duplicate_source']}")
        print(f"    Amount: {an['amount']} | Date: {an['date']} | Existing Ref: {an['ref']} | Duplicate Ref: {an['ev_ref']}")

    # Let's check for hash collisions. 
    # Do we have multiple different evidence records for the same transaction that have different details (like different reference numbers or different narrations)?
    print("\n--- Hash Collision Check ---")
    collision_count = 0
    for tx_id, ev_list in ev_by_tx.items():
        tx = tx_map.get(tx_id)
        if not tx:
            continue
        
        # Check if the reference numbers or amounts are different
        distinct_refs = set(ev["reference_number"] for ev in ev_list if ev["reference_number"])
        if tx["reference_number"]:
            distinct_refs.add(tx["reference_number"])
        
        # If we have multiple distinct reference numbers for the same hash, that could be a collision
        if len(distinct_refs) > 1:
            collision_count += 1
            if collision_count <= 5:
                print(f"Transaction ID: {tx_id} | Amount: {tx['amount']} | Date: {tx['event_date']}")
                print(f"  Existing Source: {tx['source']} | Ref: {tx['reference_number']}")
                for ev in ev_list:
                    print(f"  Evidence Source: {ev['source']} | Ref: {ev['reference_number']} | Narration: {ev['raw_narration'][:60]}")
                print("-" * 50)
    print(f"Total transactions with multiple distinct reference numbers (potential collisions): {collision_count}")

    # Write detail to JSON for full audit
    breakdown = {
        "sources": tx_sources,
        "evidence_sources": ev_sources,
        "pairs": {f"{k[0]}->{k[1]}": v for k, v in pairs.items()},
        "anomalies": anomalies
    }
    with open("scratch/dedup_gap_analysis.json", "w") as f:
        json.dump(breakdown, f, indent=2)

if __name__ == "__main__":
    main()
