# Signal Intake Agent Review

This document decomposes the first stage of the **MobileSignalPipeline** and **EmailPipeline** into an agentic sub-module: the **Signal Intake Agent**. The sole responsibility of this agent is to validate, inspect, and select whether an incoming raw signal should proceed to downstream intelligence stages or be discarded as noise.

---

## 1. Input Analysis (WhatsApp, SMS, Email)

The intake agent processes three distinct channels. Below is the current metadata, timestamping, sender, and contextual structure for each source:

| Channel | Metadata Fields | Timestamps | Sender Info | Contextual Attributes |
| :--- | :--- | :--- | :--- | :--- |
| **WhatsApp** | `deviceId`, `message_hash`, `processed` (flag) | `mobile_timestamp` (Epoch ms string / ISO format) | Chat contact name (e.g. `'Shobana'`, `'WhatsApp System'`) | Conversation context, chat sender identity |
| **SMS** | `deviceId`, `message_hash`, `processed` (flag) | `mobile_timestamp` (Epoch ms string / ISO format) | SMS shortcode/sender (e.g. `'HDFCBank'`, `'998877'`) | Bank transactions, OTPs, promotional codes |
| **Email** | `id` (Gmail msg ID), `threadId`, `snippet` | Gmail API `internalDate` header | From email header, sender displayName | Full headers, subject line, body text |

---

## 2. Selection Logic (Rule-Based Noise Filtering)

The intake logic operates on a fail-fast, rule-based approach to filter noise before invoking any local LLM.

### Discard Criteria (Dropped Signals)
1. **OTPs & Verification Codes**: If the message contains terms like `"otp"`, `"verification code"`, `"one-time password"`, or `"securesubmit"`.
2. **WhatsApp System/Media Activity**:
   * System events: `"checking for new messages"`, `"whatsapp is running"`, `"incoming voice call"`, `"missed video call"`.
   * Message status logs: `"this message was deleted"`, `"you deleted this message"`.
   * Media-only notifications with no accompanying text: `"photo"`, `"video"`, `"audio"`, `"sticker"`, `"gif"`.
3. **SMS Spam Indicators**: Keywords like `"tap to view"`, `"click here to view"`, `"truecaller"`, `"overlay notification"`.
4. **Temporal Cutoff**: Any raw mobile signal whose parsed timestamp is older than **90 days**.

### Accept Criteria (Candidate Signals)
1. **Financial/Banking Transactions**: Shortcodes or text indicating banking, debit, credit, or UPI statements (e.g. `"UPI transaction of INR 1500"`).
2. **Personal Chats & Action Requests**: Messages from known contacts (e.g., family members like Shobana asking questions, school circular updates).
3. **Important Information / FYIs**: General updates that are not classified as system notifications or promotional spam.

---

## 3. WhatsApp Processing & Information Integrity

### Key Value Source
WhatsApp contains high-value context about family operations, school updates, travel plans, and home tasks. 

### Potential Metadata & Timestamp Loss Risks
1. **Timestamp Conversion**: The original `mobile_timestamp` is often stored in the source database as an Epoch millisecond string (e.g., `"1782021845000"`). If parsing fails, it defaults to `datetime.utcnow()`, destroying historical sequence integrity.
2. **Message Hash Deduplication**: The unique hash (`message_hash`) prevents duplicate ingestion at the DB layer, but if the device uploads the same message with slightly different whitespace or metadata, it might bypass the initial hash check and require cross-channel deduplication.
3. **Group vs. Direct Context**: Currently, the sender field is loaded, but group conversation context (group name vs. individual sender within the group) is not fully separated.

---

## 4. Proposed Intake Output: `candidate_signals`

To enforce a clean boundary, the **Signal Intake Agent** will output a list of structured `candidate_signals`. Downstream agents (for classification, todo extraction, and financials) will process only these candidate signals:

```json
{
  "raw_signal_id": "db_record_id_or_hash",
  "source": "whatsapp | sms | email",
  "sender": "Sender Name / Number",
  "message": "Original raw message text or body",
  "timestamp": "2026-06-23T13:45:00Z",
  "meta": {
    "device_id": "mobile_device_identifier",
    "email_message_id": "gmail_msg_id_if_email",
    "is_personal_contact": true
  }
}
```
Using this clean boundary, the downstream LLM classifications are shielded from system noise, OTPs, deleted messages, and stale historic logs.
