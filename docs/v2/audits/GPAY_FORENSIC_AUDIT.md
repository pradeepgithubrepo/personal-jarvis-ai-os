# GPAY FORENSIC AUDIT

> Jarvis V2 · GPAY_FORENSIC_AUDIT  
> Executed: 2026-07-10T15:47:00Z  
> Remote: `https://tbwnyuampjoamgarwwoo.supabase.co`  
> Schema: `jarvis_insights_schemav1`

---

## Remote Evidence

```
curl -si "https://tbwnyuampjoamgarwwoo.supabase.co/rest/v1/mobile_signals?select=source&source=eq.gpay&limit=0"
  -H "Accept-Profile: jarvis_insights_schemav1" -H "Prefer: count=exact"
Response: content-range: */277
```

---

## GPay Signal Counts

| Stage | Count | Notes |
|---|---|---|
| `mobile_signals` (source=gpay) | **277** | Raw GPay notifications |
| `qualified_signals` (GPay) | **0** | Pipeline never ran |
| `understood_signals` (GPay) | **0** | Pipeline never ran |
| Rejected | **0** | Not rejected — unprocessed |
| Missing | **0** | All 277 are intact in `mobile_signals` |

---

## Expected vs Actual

Expected behavior:
> Most GPay transactions should qualify.  
> Most GPay transactions should be understood.

Actual behavior: **0% qualified, 0% understood** — not because GPay signals are invalid, but because the Qualification Agent has never run.

---

## Sample GPay Senders (from Top 20 Sender Analysis)

- `pprad` (308 total across all sources — likely GPay UPI notifications from WhatsApp/SMS)
- `JM-HDFCBK-S` (36) — HDFC Bank UPI/GPay notifications
- `VM-HDFCBK-T` (35) — HDFC Bank transaction alerts
- `VM-HDFCBK-S` (29) — HDFC Bank service messages
- `VK-SBICRD-T` (21) — SBI credit card transaction alerts

---

## Root Cause

277 GPay signals are in `mobile_signals` with `processed=False`. They have never been touched by any pipeline stage. They are ready for processing.

**Once the Qualification Agent runs, most GPay signals are expected to qualify as FINANCIAL signals (DEBIT/CREDIT/TRANSFER patterns).**

---

## Recommended Action

Run backfill Qualification → SUA → Router against all `source=gpay` signals. Expected outcome: ~200–260 of 277 should become `FINANCIAL` type `understood_signals`.
