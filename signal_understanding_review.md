# Signal Understanding Review

This document reviews the current metadata extraction, prompting strategies, classification rules, confidence scores, entities, and data loss patterns inside `MobileIntentExtractor`, `RulesEngine`, and `SignalProcessor` to specify the design of the future **Signal Understanding Agent**.

---

## 1. Information Extracted Today

* **Rule-Based Pre-Classification**: Inspects message strings for keywords to fast-track telecom data limits, app notifications, OTP messages, and promotional spam.
* **LLM Intent Classification**: Routes messages to local LLMs to extract:
  * `intent`: High-level operational type (`financial_transaction`, `otp`, `delivery_update`, `shopping_order`, `school_update`, `personal_chat`, `work_chat`, `important`, `ignore`).
  * `category`: Broad domain categorizations (`finance`, `security`, `shopping`, `education`, `personal`, `work`, `general`).
  * `priority`: Criticality tags (`high`, `medium`, `low`, `ignore`).
  * `action_required`: Action indicator flag.
  * `due_date`: Normalizes calendar dates and relative dates (e.g. `"tomorrow"`).
  * `summary`: Synthetic summary of the raw message text.
  * `details`: Key-value dictionaries customized for each intent type (e.g. transaction amount, currency, merchant name, message sender name, order status).

---

## 2. Prompts Used Today

The system utilizes a structured instruction prompt in `MobileIntentExtractor.extract_intent()` specifying:
* **Constraint Guidelines**: Return ONLY valid JSON without markdown block wrappers or conversational notes.
* **Enumerated Valid Types**: Explicit validation lists for `intent`, `category`, and `priority`.
* **Field Explanations**: Precise schema specifications for `action_required`, `due_date`, and `summary`.
* **Sub-Schema Details**: Key-value specifications for:
  * `financial_transaction` (amount, currency, paid_to, paid_from, receiver_vpa, transaction_id, transaction_type, payment_channel, transaction_status).
  * `school_update` / `personal_chat` (classification, sender_name, message_content, action_items).
  * `shopping_order` / `delivery_update` (merchant, product, order_status, delivery_date).
  * `otp` (otp_code, service).
* **Backup Rules**: programmatically hardcodes priority overrides (e.g. forcing WhatsApp school updates and personal chats to `"high"` priority, forcing OTPs to `"ignore"` priority).

---

## 3. Structured Outputs Generated

The output schema is represented as a structured JSON object:

```json
{
  "intent": "school_update",
  "category": "education",
  "priority": "high",
  "summary": "WhatsApp update regarding child science homework due by Wednesday",
  "action_required": true,
  "due_date": "2026-06-25",
  "details": {
    "classification": "task",
    "sender_name": "Class Group",
    "message_content": "Submit science project model by Wednesday.",
    "action_items": ["Submit science project model"]
  }
}
```

---

## 4. Confidence & Fallback Mechanics

* **Classification Confidence**:
  * For rule-based matches in `SignalProcessor.classify_signal` (like OTPs or known transaction keywords), confidence is set to `1.0`.
  * For default fallback classifications, confidence is set to `0.8`.
  * LLM-based outputs do not currently return a confidence score; they are assumed to be high-confidence unless a parsing error occurs.
* **Cache Check**: Caches output via SHA256 hashes of `source + sender + message` in `ClassificationCacheRepository` to avoid duplicate LLM invocations.
* **Fallback Extraction**: If the LLM call fails or outputs invalid JSON, a local regex-based heuristic extractor matches keywords for school tasks, OTPs, transaction amounts, and deliveries.

---

## 5. Entities Extracted

* **Financial Events**: Transactions, debit/credit labels, amounts, currencies, merchants, and VPAs.
* **Tasks/Todos**: Actionable items, due dates, source associations, and priority scores.
* **Info circulars/FYIs**: Informational updates (school instructions, delivery tracking events, travel dates).

---

## 6. Discarded Metadata & Data Loss Risks

1. **VPA/Bank Details**: While `MobileIntentExtractor` attempts to fetch bank names and VPA handles, these are often omitted in simplified SMS alerts, losing merchant category matching keys.
2. **Contact Names**: Device contacts matching telephone numbers are not integrated; the system relies strictly on strings sent by the Android service, which can cause naming variations.
3. **LLM Probability/Logprobs**: No logprobs or model confidence scores are captured from the Ollama generation, making it difficult to automatically flag doubtful classifications for user correction.

---

## 7. Future Signal Understanding Agent Design

The future **Signal Understanding Agent** should encapsulate the following design enhancements:
* **Confidence Scoring**: Require the LLM prompt to include a `"confidence"` score (between `0.0` and `1.0`) inside the JSON schema.
* **Rule-LLM Hybrid Pipeline**: Integrate the `RulesEngine` and `MobileIntentExtractor` directly into the agent. First run deterministic rule lookups, and fall back to LLM calls only when rules do not resolve with confidence.
* **Feedback Loop Learning**: Expose low-confidence classifications (e.g. < 0.8) to the Streamlit UI for active correction, feeding verified overrides back to the `user_overrides.json` file.
