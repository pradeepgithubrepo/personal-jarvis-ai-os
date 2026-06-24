# Signal Qualification Agent Design Review

This document decomposes and reviews all current filtering, age exclusion, and duplicate checking mechanisms in Jarvis to design the future **Signal Qualification Agent**. This agent serves as the gating barrier between raw ingestion feeds and downstream LLM intelligence layers, preventing noise from diluting the pipeline.

---

## 1. Existing Filter Inventory

Below is an inventory of all rule-based filters currently executing in the pipeline:

| Rule Name | Current Location | Current Logic | Example Signal | Current Action |
| :--- | :--- | :--- | :--- | :--- |
| **OTP Detection** | `MobileNoiseFilter` | Checks for keywords: `"otp"`, `"verification code"`, `"one-time password"`, `"securesubmit"`. | *"Your HDFC Bank OTP is 887755"* | **DROP** |
| **WhatsApp System Noise** | `MobileNoiseFilter` | Drops system status strings: `"checking for new messages"`, `"whatsapp is running"`. | *"Checking for new messages..."* | **DROP** |
| **Deleted Messages** | `MobileNoiseFilter` | Drops delete notifications: `"this message was deleted"`, `"you deleted this message"`. | *"This message was deleted"* | **DROP** |
| **WhatsApp Media Logs** | `MobileNoiseFilter` | Drops media alerts containing only: `"photo"`, `"video"`, `"audio"`, `"sticker"`, `"gif"`. | *"sticker"* | **DROP** |
| **SMS Noise Keywords** | `MobileNoiseFilter` | Drops spam overlay keyword markers: `"tap to view"`, `"click here to view"`, `"truecaller"`. | *"Tap to view notification"* | **DROP** |
| **Telecom Data Alerts** | `MobileIntentExtractor` | Ignores keywords like: `"daily high speed data limit"`, `"90% data alert"`, `"recharge successful"`. | *"90% data limit exceeded"* | **DROP** |
| **System Diagnostics** | `MobileIntentExtractor` | Ignores phone health alerts: `"truecaller is running"`, `"whatsapp backup"`, `"syncing completed"`. | *"Truecaller is running in background"*| **DROP** |
| **Promotional Ads** | `MobileIntentExtractor` | Ignores marketing terms (if no payment verbs like `spent` exist): `"pre-approved loan"`, `"click to apply"`. | *"Pre-approved personal loan of Rs 5L"*| **DROP** |
| **Topic Ignorance** | `RulesEngine` | Compares text against dynamic list in `jarvis_rules.json` (`ignore_topics`, `financial_ignore`). | Matches custom spam keywords | **DROP** |

---

## 2. Existing Age Rules

* **SMS & WhatsApp Cutoff**: Implemented in [mobile_signal_pipeline.py](file:///home/prad/petprojects/ai/jarvis/services/mobile_signal_pipeline.py#L72-L77). Checks the parsed mobile timestamp. If it is older than **90 days** from the current system time, the LLM pipeline is bypassed, and the record is marked processed.
* **Email Cutoff**: Currently, no age filters exist in [email_pipeline.py](file:///home/prad/petprojects/ai/jarvis/services/email_pipeline.py). The Gmail client only queries the first `40` unread email results. Stale unread emails could theoretically enter the system if they are marked unread, indicating a potential vulnerability.

---

## 3. Duplicate Rules & Deduplication

* **Message Hash Logic**: Implemented during Consumer Ingestion. Computes SHA256 hashes of download strings to reject identical file imports.
* **Signal Deduplication**: Evaluates message IDs (e.g. Gmail ID) via `SignalRepository.exists_message_id()` to skip already imported items.
* **Cross-Channel Deduplication**: Implemented in `SignalRepository.is_duplicate_signal()`:
  * *Finance*: Scans signals in the last **48 hours**. If amounts match and the payment sources (e.g. card suffix) are identical, it is rejected as a duplicate.
  * *Shopping*: If order IDs or merchant names match in the last **48 hours**, it is flagged as a duplicate.
  * *Text match*: If summaries match exactly (case-insensitive), it is rejected.
* **Future Agent Ownership**: All deduplication logic will be consolidated inside the **Signal Qualification Agent** before signals are saved or routed, preventing downstream processing of redundant signals.

---

## 4. Qualification Categories

The Signal Qualification Agent will categorize every raw input into one of three statuses:

1. **QUALIFIED**: Valuable signals forwarded to the Signal Understanding Agent.
   * *Examples*: Family conversations, parenting updates, school homework announcements, utility bills, financial credit/debit logs, travel/flight details, doctor/health appointments, e-commerce shipping milestones.
2. **REJECTED**: Confirmed junk, spam, or diagnostic noise to be bypassed immediately.
   * *Examples*: OTPs, SMS advertisements, telecom recharge proposals, device battery/backup state logs, truecaller overlay notifications, deleted messages, media placeholders.
3. **REVIEW**: Edge cases or group message channels where high-value signals might occasionally be mixed with noise.
   * *Examples*: Badminton group scheduling chats, apartment association maintenance notices, community groups, unknown numbers sending bulk notifications.

---

## 5. Qualification Reason Codes

To facilitate auditing, every non-QUALIFIED status will receive a reason code:

* `OTP`: One-time password or verification code.
* `PROMOTION`: Marketing advertisement or spam campaign.
* `SYSTEM_NOTIFICATION`: Phone diagnostic log, backup sync alert, or status overlay.
* `STALE_SIGNAL`: Exceeds age limitations (> 90 days).
* `DUPLICATE_SIGNAL`: Matched hash, message ID, or cross-channel transaction parameters in the 48-hour window.
* `LOW_VALUE_GROUP_MESSAGE`: Dropped after community filter evaluation (e.g., non-relevant chatter).
* `UNKNOWN`: Uncategorized noise.

---

## 6. Qualified Signal Contract

This JSON contract is emitted by the Signal Qualification Agent, representing the schema of the future `qualified_signals` table/payload:

```json
{
  "qualified_signal_id": "unique_qualification_uuid",
  "signal_id": "raw_source_record_uuid",
  "qualification_status": "QUALIFIED | REJECTED | REVIEW",
  "qualification_reason": "OTP | PROMOTION | STALE_SIGNAL | DUPLICATE_SIGNAL | null",
  "source": "whatsapp | sms | email",
  "sender": "HDFCBank | Shobana | Class Group",
  "message": "Original raw message body",
  "timestamp": "2026-06-23T14:20:00Z",
  "created_at": "2026-06-23T14:20:00Z"
}
```

---

## 7. Rejected Signal Strategy

Rather than deleting `REJECTED` or `REVIEW` signals (which prevents tuning filters or recovering erroneously blocked messages):
1. **Suppression Log**: Store rejected signals in a dedicated, low-indexing audit log table: `rejected_signals_audit`.
2. **Review Queue**: Flags categorized as `REVIEW` are displayed in a hidden "Diagnostics" tab on the Streamlit dashboard. Users can promote a sender or override rules (e.g., converting a group message to a task).
3. **Age Out Policy**: Run an automated cleaning cron job that deletes entries in `rejected_signals_audit` only after **30 days** of retention.

---

## 8. Ownership Matrix

| Function / Rule | Monolithic Module | Future Agent Owner |
| :--- | :--- | :--- |
| OTP keyword checks | `MobileNoiseFilter` | **Signal Qualification Agent** |
| WhatsApp system / media filters | `MobileNoiseFilter` | **Signal Qualification Agent** |
| Age filter checks (90 days) | `MobileSignalPipeline` | **Signal Qualification Agent** |
| Cross-channel duplicate scans | `SignalRepository` | **Signal Qualification Agent** |
| Group channel filter rules | `RulesEngine` | **Signal Qualification Agent** |
| Ignore topic lists | `RulesEngine` | **Signal Qualification Agent** |
