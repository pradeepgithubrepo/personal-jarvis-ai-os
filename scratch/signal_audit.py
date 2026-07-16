"""
Signal Lineage Audit Script
Executes all 10 objectives against remote Supabase.
Usage: PYTHONPATH=.venv/lib/python3.12/site-packages:. /usr/bin/python3 -u scratch/signal_audit.py
"""
import os
import sys
import json
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, '.venv/lib/python3.12/site-packages')

from supabase import create_client, ClientOptions

SUPABASE_URL = os.environ['SUPABASE_URL']
SUPABASE_KEY = os.environ['SUPABASE_SERVICE_ROLE_KEY']
SCHEMA = 'jarvis_insights_schemav1'
TS = datetime.now(timezone.utc).isoformat()

opts = ClientOptions(schema=SCHEMA)
db = create_client(SUPABASE_URL, SUPABASE_KEY, options=opts)

print(f"=== SIGNAL LINEAGE AUDIT ===", flush=True)
print(f"Remote: {SUPABASE_URL}", flush=True)
print(f"Schema: {SCHEMA}", flush=True)
print(f"Timestamp: {TS}", flush=True)
print("", flush=True)

# ─── OBJ 1: FULL PIPELINE COUNTS ────────────────────────────────────────────
print("── OBJECTIVE 1: PIPELINE ACCOUNTING ──", flush=True)

ms = db.table('mobile_signals').select('count', count='exact').limit(0).execute()
qs = db.table('qualified_signals').select('count', count='exact').limit(0).execute()
us = db.table('understood_signals').select('count', count='exact').limit(0).execute()
sr = db.table('signal_routes').select('count', count='exact').limit(0).execute()

n_ms = ms.count
n_qs = qs.count
n_us = us.count
n_sr = sr.count

print(f"mobile_signals:      {n_ms}", flush=True)
print(f"qualified_signals:   {n_qs}", flush=True)
print(f"understood_signals:  {n_us}", flush=True)
print(f"signal_routes:       {n_sr}", flush=True)

qual_rate = n_qs / n_ms * 100 if n_ms else 0
us_rate = n_us / n_qs * 100 if n_qs else 0
route_rate = n_sr / n_us * 100 if n_us else 0

print(f"\nQualification Rate (qs/ms): {qual_rate:.2f}%", flush=True)
print(f"Attrition ms→qs:           {100-qual_rate:.2f}%", flush=True)
print(f"Understanding Rate (us/qs): {us_rate:.2f}%", flush=True)
print(f"Attrition qs→us:           {100-us_rate:.2f}%", flush=True)
print(f"Routing Rate (sr/us):       {route_rate:.2f}%", flush=True)
print("", flush=True)

# ─── OBJ 2: SOURCE BREAKDOWN ─────────────────────────────────────────────────
print("── OBJECTIVE 2: SOURCE BREAKDOWN ──", flush=True)

ms_all = db.table('mobile_signals').select('source').execute()
from collections import Counter
source_counts = Counter(r['source'] for r in ms_all.data)
print("mobile_signals by source:")
for src, cnt in sorted(source_counts.items(), key=lambda x: -x[1]):
    print(f"  {src}: {cnt}", flush=True)
print("", flush=True)

qs_all = db.table('qualified_signals').select('source,qualification_status').execute()
qs_by_source = Counter(r['source'] for r in qs_all.data)
print("qualified_signals by source:")
for src, cnt in sorted(qs_by_source.items(), key=lambda x: -x[1]):
    print(f"  {src}: {cnt}", flush=True)
print("", flush=True)

# ─── OBJ 3: GPAY FORENSIC ────────────────────────────────────────────────────
print("── OBJECTIVE 3: GPAY FORENSIC ──", flush=True)
gpay_ms = [r for r in ms_all.data if r.get('source','').lower() in ('gpay','google pay','googlepay','g-pay')]
gpay_qs = [r for r in qs_all.data if r.get('source','').lower() in ('gpay','google pay','googlepay','g-pay')]
print(f"GPay mobile_signals:     {len(gpay_ms)}", flush=True)
print(f"GPay qualified_signals:  {len(gpay_qs)}", flush=True)
print("", flush=True)

# ─── OBJ 4: QUALIFICATION STATUS BREAKDOWN ────────────────────────────────────
print("── OBJECTIVE 4+6: QUALIFICATION STATUS BREAKDOWN ──", flush=True)
qs_status = Counter(r.get('qualification_status', 'UNKNOWN') for r in qs_all.data)
for st, cnt in sorted(qs_status.items(), key=lambda x: -x[1]):
    print(f"  {st}: {cnt}", flush=True)
print("", flush=True)

# qualification_status from all mobile_signals (via joined query)
ms_full = db.table('mobile_signals').select('id,source,sender,processed,mobile_timestamp').order('id', desc=True).limit(500).execute()
ms_processed = Counter(r.get('processed', False) for r in ms_full.data)
print(f"mobile_signals (latest 500) - processed=True: {ms_processed.get(True,0)}, processed=False: {ms_processed.get(False,0)}", flush=True)
print("", flush=True)

# ─── OBJ 5: WHATSAPP DATE FILTER ─────────────────────────────────────────────
print("── OBJECTIVE 5: WHATSAPP DATE FILTER ──", flush=True)
wa_ms = [r for r in ms_all.data if 'whatsapp' in r.get('source','').lower()]
print(f"Total WhatsApp mobile_signals: {len(wa_ms)}", flush=True)
cutoff = '2026-07-01'
wa_before = [r for r in wa_ms if r.get('mobile_timestamp','') < cutoff]
wa_after  = [r for r in wa_ms if r.get('mobile_timestamp','') >= cutoff]
print(f"  Before {cutoff}: {len(wa_before)}", flush=True)
print(f"  After  {cutoff}: {len(wa_after)}", flush=True)
print("", flush=True)

# ─── OBJ 7: QUALIFIED WITHOUT UNDERSTOOD ─────────────────────────────────────
print("── OBJECTIVE 7: QUALIFIED WITHOUT UNDERSTOOD ──", flush=True)
us_all = db.table('understood_signals').select('qualified_signal_id').execute()
us_qs_ids = set(r['qualified_signal_id'] for r in us_all.data)
qs_ids_all = set(r['id'] for r in qs_all.data)
missing_us = qs_ids_all - us_qs_ids
print(f"qualified_signals total:                 {len(qs_ids_all)}", flush=True)
print(f"qualified_signals WITH understood:       {len(us_qs_ids & qs_ids_all)}", flush=True)
print(f"qualified_signals WITHOUT understood:    {len(missing_us)}", flush=True)
print("", flush=True)

# For missing ones, look at their statuses
missing_details = [r for r in qs_all.data if r['id'] in missing_us]
missing_status = Counter(r.get('qualification_status','UNKNOWN') for r in missing_details)
print("Missing understood — qualification_status breakdown:")
for st, cnt in sorted(missing_status.items(), key=lambda x: -x[1]):
    print(f"  {st}: {cnt}", flush=True)
print("", flush=True)

# ─── OBJ 8: DELTA PROCESSING ────────────────────────────────────────────────
print("── OBJECTIVE 8: DELTA PROCESSING ──", flush=True)
try:
    pf = db.table('processed_files').select('count', count='exact').limit(0).execute()
    print(f"processed_files: {pf.count}", flush=True)
except Exception as e:
    print(f"processed_files table: {e}", flush=True)

try:
    pr = db.table('pipeline_runs').select('count', count='exact').limit(0).execute()
    print(f"pipeline_runs: {pr.count}", flush=True)
except Exception as e:
    print(f"pipeline_runs table: {e}", flush=True)

try:
    pre = db.table('pipeline_run_events').select('count', count='exact').limit(0).execute()
    print(f"pipeline_run_events: {pre.count}", flush=True)
except Exception as e:
    print(f"pipeline_run_events table: {e}", flush=True)
print("", flush=True)

# ─── OBJ 9: RANDOM TRACE AUDIT ───────────────────────────────────────────────
print("── OBJECTIVE 9: RANDOM TRACE (20 signals) ──", flush=True)
# Get 20 random mobile signals by sampling
import random
random.seed(42)
ms_sample_pool = ms_full.data[:200]
sample_20 = random.sample(ms_sample_pool, min(20, len(ms_sample_pool)))

qs_by_signal_id = {r.get('signal_id'): r for r in qs_all.data if r.get('signal_id')}
us_by_qs_id = {r.get('qualified_signal_id'): r for r in us_all.data}

for sig in sample_20:
    sid = sig['id']
    src = sig.get('source', '?')
    processed = sig.get('processed', False)
    qs_match = qs_by_signal_id.get(sid)
    us_match = us_by_qs_id.get(qs_match['id']) if qs_match else None
    sr_match = None  # Need a separate lookup for signal_routes
    
    qualified = "YES" if qs_match else "NO"
    understood = "YES" if us_match else "NO"
    q_reason = qs_match.get('qualification_status', 'N/A') if qs_match else 'Not Qualified'
    
    print(f"  ms_id={sid} | src={src} | processed={processed} | qualified={qualified}({q_reason}) | understood={understood}", flush=True)

print("", flush=True)
print("=== AUDIT COMPLETE ===", flush=True)
print(f"Execution Timestamp: {datetime.now(timezone.utc).isoformat()}", flush=True)
