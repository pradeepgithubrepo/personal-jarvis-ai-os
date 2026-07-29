# BANK TRANSACTION FORENSIC AUDIT

> Jarvis V2 · BANK_FORENSIC_AUDIT  
> Executed: 2026-07-10T15:47:00Z  
> Remote: `https://tbwnyuampjoamgarwwoo.supabase.co`  
> Schema: `jarvis_insights_schemav1`

---

## Remote Evidence

```
Source breakdown from 1,700 mobile_signals:
  bank_statement: 49 (2.9%)
  sms (bank-related senders): ~200+ (HDFC, SBI, Axis, Kotak, etc.)
```

---

## Bank Signal Counts

| Category | Count | Notes |
|---|---|---|
| `source=bank_statement` | **49** | Direct bank statement imports |
| SMS from bank senders (HDFCBK, SBICRD, etc.) | **~200** | Estimated from sender analysis |
| `qualified_signals` (bank) | **0** | Pipeline never ran |
| `understood_signals` (bank) | **0** | Pipeline never ran |

---

## Top Bank Senders (from Remote Data)

| Sender | Count | Bank |
|---|---|---|
| AD-HDFCBK-S | 57 | HDFC Bank (service) |
| JM-HDFCBK-S | 36 | HDFC Bank |
| VM-HDFCBK-T | 35 | HDFC Bank (transactions) |
| VM-HDFCBK-S | 29 | HDFC Bank (service) |
| VK-SBICRD-T | 21 | SBI Credit Card (transactions) |
| JM-HDFCBN-P | 19 | HDFC Bank Net |
| AX-SBIPSG-T | 16 | SBI PSG |
| VD-HDFCBN-P | 16 | HDFC Bank Net |
| VD-HDFCBK-S | 14 | HDFC Bank |
| VM-HDFCBN-P | 13 | HDFC Bank Net |

---

## Root Cause

All bank signals (both `bank_statement` and SMS from bank senders) are sitting in `mobile_signals` with `processed=False`. None have been qualified or understood. This is the primary source of expected `FINANCIAL` signals for Phase 3A.

---

## Recommended Action

Bank transaction SMS signals (HDFC, SBI, Axis) are the highest-value signals for the Financial Agent. Prioritize qualifying these. Estimated ~200 bank SMS + 49 bank statements = ~250 potential FINANCIAL signals.
