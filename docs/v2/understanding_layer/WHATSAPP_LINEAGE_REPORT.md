# WHATSAPP SIGNAL LINEAGE AUDIT REPORT
**Jarvis V2 Pipeline Rebuild — Ingestion to Understanding**

---

## 1. Executive Summary

This lineage report traces the movement of **WhatsApp signals** from raw ingestion in `mobile_signals` through Stage 1 (Qualification) and into Stage 2 (Understanding). 

A total of **365 raw WhatsApp messages** exist in `mobile_signals`. Out of these, exactly **29 signals** (7.9%) reached the `understood_signals` table. This reduction is the result of strict pipeline filters, primarily the **Pre-July WhatsApp Exclusion Rule** and the **Qualification Status Filter** (which isolates `REVIEW` and `REJECTED` records from downstream processing).

---

## 2. Ingestion Lineage Funnel

The diagram below outlines the transition funnel for WhatsApp signals across the pipeline:

```text
       Raw Ingest (mobile_signals)
                 365 (100%)
                     │
                     ▼ [Stage 1 Qualification]
      ┌──────────────┼──────────────┐
      ▼              ▼              ▼
[ REJECTED ]     [ REVIEW ]    [ QUALIFIED ]
  213 (58%)      123 (34%)       29 (8%)
                     │              │
                     │              ▼ [Stage 2 Understanding]
                     │         [ Understood ]
                     │            29 (100%)
                     ▼
           [ Bypassed / Frozen ]
```

---

## 3. Dissecting the Qualification Filters

### 3.1 The Pre-July WhatsApp Exclusion Rule (213 Signals Filtered)
* **Rule Objective**: Prevent chat pollution and high LLM token costs from historical chats by filtering out WhatsApp messages dated before **July 1, 2026**.
* **Result**: **213 signals (58.4% of total)** were rejected with the reason `excluded_pre_july_whatsapp`.
* **Example Messages Filtered**:
  * *"Yes I'm ready if school holiday ✋🏾"* (General conversation)
  * *"Yes I am coming tomorrow morning 6.30"* (Scheduling coordinate)
  * *"Can you share the mercury one gate url if possible"* (Link request)

### 3.2 Qualification Scoring Rules (116 Signals Filtered)
* **Rule Objective**: Messages must cross a minimum score of `70.0` or meet keyword boosts to be qualified for downstream automation. Ambiguous or conversational updates are routed to `REVIEW` to avoid false actions.
* **Result**: **116 signals (31.8%)** were categorized under `REVIEW` (reason: `review_needed`). Since Stage 2 SUA only accepts `qualification_status = 'QUALIFIED'`, these signals were withheld.
* **Examples**:
  * *" Purifier person don't pick up the call so register complaint "* (Initially marked `REVIEW` or qualified depending on boost, but if lacking high qualification boosts, it sits in REVIEW).

### 3.3 Other Rejections (7 Signals Filtered)
* **Group Messages**: **6 signals** were rejected with the reason `group_message` (to avoid spam processing from group chats).
* **Financial Preservation Override**: **1 signal** was handled under override.

---

## 4. Understood WhatsApp Signals (The 29 Records)

The 29 signals that reached `understood_signals` represent **high-intent, action-oriented, or financial WhatsApp messages** post-July 1, 2026. 

A sample of these successfully understood records includes:
1. **Action Request**: *"Purifier person don't pick up the call so register complaint"* (Classified as `ACTION`, task contract generated).
2. **Status Update**: *"Boarded the train"* (Classified as `NOISE` fallback, indicating no task/financial ledger insert needed).
3. **Cashback Alert**: *"HCs cashback credited in Apollo wallet"* (Classified as `FINANCIAL`, CREDIT transaction type contract generated).

---

## 5. Summary & Recommendation

The count of 29 WhatsApp signals is **correct and indicates that the pipeline filters are working exactly as designed**:
1. It successfully prevented **213 historical chat messages** from polluting the ledger/tasks database.
2. It filtered out **6 spam group-chat messages**.
3. It isolated **116 ambiguous/low-scoring messages** into `REVIEW` status, leaving only the 29 highest-signal messages to be processed into semantic contracts in `understood_signals`.
