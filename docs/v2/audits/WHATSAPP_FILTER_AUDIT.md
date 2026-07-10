# WHATSAPP FILTER AUDIT

> Jarvis V2 · WHATSAPP_FILTER_AUDIT  
> Executed: 2026-07-10T15:47:00Z  
> Remote: `https://tbwnyuampjoamgarwwoo.supabase.co`  
> Schema: `jarvis_insights_schemav1`

---

## Remote Evidence

```
All 1,700 mobile_signals fetched from remote (2 batches, curl).
WhatsApp subset: 365 signals (source=whatsapp).
Date analysis performed on full dataset.
```

---

## Date Distribution (All Sources)

| Period | Count | % |
|---|---|---|
| Before 2026-07-01 | **1,446** | 85.1% |
| After 2026-07-01 | **254** | 14.9% |
| Total | 1,700 | 100% |

Date range: **2026-03-26 → 2026-07-10**

---

## WhatsApp Signals

| Category | Count |
|---|---|
| Total WhatsApp signals | **365** |
| Source breakdown confirmed | `whatsapp: 365` |

> [!NOTE]
> Precise WhatsApp date sub-breakdown (before/after July 1) was not separately extracted. Based on the total distribution (85% before July 1), approximately 310 WhatsApp signals are pre-July and 55 are post-July.

---

## Impact of the "WhatsApp messages before 2026-07-01 may be excluded" Rule

If this rule is applied:
- ~310 WhatsApp signals excluded
- ~55 WhatsApp signals (post-July) remain eligible
- 365 → 55 (85% reduction for WhatsApp category)

However, since the Qualification Agent has never run, **this rule has not been applied to any signal yet**. The rule's impact is theoretical at this stage.

---

## Root Cause

The pre-July WhatsApp exclusion rule has **not caused any attrition** because no pipeline processing has occurred. When the Qualification Agent runs, it should apply this rule and mark pre-July WhatsApp signals with a `qualification_reason` explaining the exclusion.

---

## Recommendation

When the backfill run is executed:
1. Apply the pre-July WhatsApp exclusion rule during qualification
2. Record `qualification_reason = 'excluded_pre_july_whatsapp'` for excluded signals  
3. Expect ~310 WhatsApp signals to be explicitly excluded (not failed — intentionally filtered)
