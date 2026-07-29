# LOCAL QWEN 1.5B WHATSAPP SIGNAL BENCHMARK REPORT
**Date/Time**: 2026-07-11T15:12:34Z  
**Model**: `qwen2.5:1.5b` (Local Ollama on CPU)  
**Total Signals Tested**: 15

---

## 1. Volumetric Speed Summary

| Signal Index | Signal ID | Message (Truncated) | Duration (sec) | Parse Status | Predicted Type |
|---|---|---|---|---|---|
| 1 | 8668 | `Yes I'm ready if school holiday ✋🏾` | 8.74s | `SUCCESS` | `ACTION` |
| 2 | 8669 | `Ok anna` | 4.69s | `SUCCESS` | `ACTION` |
| 3 | 8670 | `Yes I am coming tomorrow morning 6.30` | 6.42s | `SUCCESS` | `ACTION` |
| 4 | 8671 | `Super anna` | 4.46s | `SUCCESS` | `ACTION` |
| 5 | 8684 | `Can you share the mercury one gate url i...` | 2.93s | `SUCCESS` | `ACTION` |
| 6 | 8685 | `Got the link` | 5.38s | `SUCCESS` | `ACTION` |
| 7 | 8686 | `Done , User!` | 6.02s | `SUCCESS` | `ACTION` |
| 8 | 8888 | `📷 Photo` | 5.24s | `SUCCESS` | `ACTION` |
| 9 | 8687 | `Done , User!` | 6.62s | `SUCCESS` | `ACTION` |
| 10 | 8688 | `Guys pls come around 6:30am` | 3.51s | `SUCCESS` | `ACTION` |
| 11 | 8889 | `from Contact_1` | 5.05s | `SUCCESS` | `ACTION` |
| 12 | 8689 | `Sure` | 5.20s | `SUCCESS` | `ACTION` |
| 13 | 8719 | `Same as @⁨~Ganesh Pandian 🫰🏾⁩ said` | 5.28s | `SUCCESS` | `ACTION` |
| 14 | 8720 | `Tap for more info` | 5.69s | `SUCCESS` | `NOISE` |
| 15 | 8721 | `Tap for more info` | 4.44s | `SUCCESS` | `NOISE` |

### Key Metrics
* **Total Time**: 79.66 seconds
* **Average Time per Signal**: 5.31 seconds
* **JSON Parse Success Rate**: 15/15 (100.0%)

---

## 2. Detailed Request & Response Trace

### Signal 1 (ID: 8668)
* **Sender**: `[REDACTED_SPORTS_GROUP]: ~ Ganesh Pandian 🫰🏾`
* **Timestamp**: `2026-06-25T03:47:19.177+00:00`
* **Message**: *"Yes I'm ready if school holiday ✋🏾"*
* **Response Time**: `8.74 seconds`
* **Parse Status**: `SUCCESS`

#### Exact Prompt Passed:
```text
Analyze the message and classify it into exactly one of these types:
- FINANCIAL: Active transactions, credit/debit alerts, bank spent/received notifications, payment receipts. (Only if money is actively transferred or spent)
- ACTION: Reminders, todos, tasks, chores, or direct requests to do something (e.g. 'call plumber', 'buy milk').
- FYI: Schedules, bookings, flight/train/movie status, appointments, non-actionable info. (e.g. 'flight AI-101 scheduled')
- FACT: User context, credentials, passport, birthday, height/weight info.
- NOISE: Greetings, spam, chit-chat, OTPs, promotional codes, or generic messages.

Message to analyze:
Sender: [REDACTED_SPORTS_GROUP]: ~ Ganesh Pandian 🫰🏾
Source: whatsapp
Content: Yes I'm ready if school holiday ✋🏾
Timestamp: 2026-06-25T03:47:19.177+00:00

Respond ONLY with a single JSON object. Do not wrap in markdown or code blocks.
JSON format keys:
"signal_type" (one of the 5 uppercase types above),
"importance" (float 0.0 to 1.0),
"confidence" (float 0.0 to 1.0),
"summary" (1-sentence description),
"reason" (short classification justification),
"contract" (object of details, e.g. for NOISE it is {}).

Contract fields per type:
- FINANCIAL: amount, currency, transaction_type (DEBIT/CREDIT), payment_channel (UPI/CARD/CASH/UNKNOWN), merchant
- ACTION: task_name, assignee, due_date
- FYI: event_name, event_time, description
- FACT: entity, attribute, value
- NOISE: {}

```

#### Raw Model Response:
```json
```json
{
  "signal_type": "ACTION",
  "importance": 0.8,
  "confidence": 0.95,
  "summary": "A message indicating that the sender is ready for school holiday activities.",
  "reason": "The message contains a direct request to do something (school holiday activities) and does not involve any financial transactions, schedules, or personal information.",
  "contract": {}
}
```
```

#### Parsed Contract JSON:
```json
{
  "signal_type": "ACTION",
  "importance": 0.8,
  "confidence": 0.95,
  "summary": "A message indicating that the sender is ready for school holiday activities.",
  "reason": "The message contains a direct request to do something (school holiday activities) and does not involve any financial transactions, schedules, or personal information.",
  "contract": {}
}
```

---

### Signal 2 (ID: 8669)
* **Sender**: `[REDACTED_SPORTS_GROUP] (2 messages): ~ Arun Kumar`
* **Timestamp**: `2026-06-25T03:48:19.167+00:00`
* **Message**: *"Ok anna"*
* **Response Time**: `4.69 seconds`
* **Parse Status**: `SUCCESS`

#### Exact Prompt Passed:
```text
Analyze the message and classify it into exactly one of these types:
- FINANCIAL: Active transactions, credit/debit alerts, bank spent/received notifications, payment receipts. (Only if money is actively transferred or spent)
- ACTION: Reminders, todos, tasks, chores, or direct requests to do something (e.g. 'call plumber', 'buy milk').
- FYI: Schedules, bookings, flight/train/movie status, appointments, non-actionable info. (e.g. 'flight AI-101 scheduled')
- FACT: User context, credentials, passport, birthday, height/weight info.
- NOISE: Greetings, spam, chit-chat, OTPs, promotional codes, or generic messages.

Message to analyze:
Sender: [REDACTED_SPORTS_GROUP] (2 messages): ~ Arun Kumar
Source: whatsapp
Content: Ok anna
Timestamp: 2026-06-25T03:48:19.167+00:00

Respond ONLY with a single JSON object. Do not wrap in markdown or code blocks.
JSON format keys:
"signal_type" (one of the 5 uppercase types above),
"importance" (float 0.0 to 1.0),
"confidence" (float 0.0 to 1.0),
"summary" (1-sentence description),
"reason" (short classification justification),
"contract" (object of details, e.g. for NOISE it is {}).

Contract fields per type:
- FINANCIAL: amount, currency, transaction_type (DEBIT/CREDIT), payment_channel (UPI/CARD/CASH/UNKNOWN), merchant
- ACTION: task_name, assignee, due_date
- FYI: event_name, event_time, description
- FACT: entity, attribute, value
- NOISE: {}

```

#### Raw Model Response:
```json
```json
{
  "signal_type": "ACTION",
  "importance": 0.5,
  "confidence": 1.0,
  "summary": "A message from a daily badminton update sender.",
  "reason": "The content is a greeting and does not contain any financial, action-related, fact-based, or noise elements typical of the other signal types.",
  "contract": {}
}
```
```

#### Parsed Contract JSON:
```json
{
  "signal_type": "ACTION",
  "importance": 0.5,
  "confidence": 1.0,
  "summary": "A message from a daily badminton update sender.",
  "reason": "The content is a greeting and does not contain any financial, action-related, fact-based, or noise elements typical of the other signal types.",
  "contract": {}
}
```

---

### Signal 3 (ID: 8670)
* **Sender**: `[REDACTED_SPORTS_GROUP]: ~ santhosh rao`
* **Timestamp**: `2026-06-25T04:26:48.27+00:00`
* **Message**: *"Yes I am coming tomorrow morning 6.30"*
* **Response Time**: `6.42 seconds`
* **Parse Status**: `SUCCESS`

#### Exact Prompt Passed:
```text
Analyze the message and classify it into exactly one of these types:
- FINANCIAL: Active transactions, credit/debit alerts, bank spent/received notifications, payment receipts. (Only if money is actively transferred or spent)
- ACTION: Reminders, todos, tasks, chores, or direct requests to do something (e.g. 'call plumber', 'buy milk').
- FYI: Schedules, bookings, flight/train/movie status, appointments, non-actionable info. (e.g. 'flight AI-101 scheduled')
- FACT: User context, credentials, passport, birthday, height/weight info.
- NOISE: Greetings, spam, chit-chat, OTPs, promotional codes, or generic messages.

Message to analyze:
Sender: [REDACTED_SPORTS_GROUP]: ~ santhosh rao
Source: whatsapp
Content: Yes I am coming tomorrow morning 6.30
Timestamp: 2026-06-25T04:26:48.27+00:00

Respond ONLY with a single JSON object. Do not wrap in markdown or code blocks.
JSON format keys:
"signal_type" (one of the 5 uppercase types above),
"importance" (float 0.0 to 1.0),
"confidence" (float 0.0 to 1.0),
"summary" (1-sentence description),
"reason" (short classification justification),
"contract" (object of details, e.g. for NOISE it is {}).

Contract fields per type:
- FINANCIAL: amount, currency, transaction_type (DEBIT/CREDIT), payment_channel (UPI/CARD/CASH/UNKNOWN), merchant
- ACTION: task_name, assignee, due_date
- FYI: event_name, event_time, description
- FACT: entity, attribute, value
- NOISE: {}

```

#### Raw Model Response:
```json
```json
{
  "signal_type": "ACTION",
  "importance": 0.8,
  "confidence": 0.95,
  "summary": "The sender is confirming their arrival at a specific time for an event.",
  "reason": "The message contains a clear task (coming to the event) with a specific time and details, indicating it's a direct request to do something.",
  "contract": {
    "task_name": "Arrive at Badminton Event",
    "assignee": "santhosh rao",
    "due_date": "2026-06-25T06:30:00"
  }
}
```
```

#### Parsed Contract JSON:
```json
{
  "signal_type": "ACTION",
  "importance": 0.8,
  "confidence": 0.95,
  "summary": "The sender is confirming their arrival at a specific time for an event.",
  "reason": "The message contains a clear task (coming to the event) with a specific time and details, indicating it's a direct request to do something.",
  "contract": {
    "task_name": "Arrive at Badminton Event",
    "assignee": "santhosh rao",
    "due_date": "2026-06-25T06:30:00"
  }
}
```

---

### Signal 4 (ID: 8671)
* **Sender**: `[REDACTED_SPORTS_GROUP] (2 messages): ~ Arun Kumar`
* **Timestamp**: `2026-06-25T04:46:30.382+00:00`
* **Message**: *"Super anna"*
* **Response Time**: `4.46 seconds`
* **Parse Status**: `SUCCESS`

#### Exact Prompt Passed:
```text
Analyze the message and classify it into exactly one of these types:
- FINANCIAL: Active transactions, credit/debit alerts, bank spent/received notifications, payment receipts. (Only if money is actively transferred or spent)
- ACTION: Reminders, todos, tasks, chores, or direct requests to do something (e.g. 'call plumber', 'buy milk').
- FYI: Schedules, bookings, flight/train/movie status, appointments, non-actionable info. (e.g. 'flight AI-101 scheduled')
- FACT: User context, credentials, passport, birthday, height/weight info.
- NOISE: Greetings, spam, chit-chat, OTPs, promotional codes, or generic messages.

Message to analyze:
Sender: [REDACTED_SPORTS_GROUP] (2 messages): ~ Arun Kumar
Source: whatsapp
Content: Super anna
Timestamp: 2026-06-25T04:46:30.382+00:00

Respond ONLY with a single JSON object. Do not wrap in markdown or code blocks.
JSON format keys:
"signal_type" (one of the 5 uppercase types above),
"importance" (float 0.0 to 1.0),
"confidence" (float 0.0 to 1.0),
"summary" (1-sentence description),
"reason" (short classification justification),
"contract" (object of details, e.g. for NOISE it is {}).

Contract fields per type:
- FINANCIAL: amount, currency, transaction_type (DEBIT/CREDIT), payment_channel (UPI/CARD/CASH/UNKNOWN), merchant
- ACTION: task_name, assignee, due_date
- FYI: event_name, event_time, description
- FACT: entity, attribute, value
- NOISE: {}

```

#### Raw Model Response:
```json
```json
{
  "signal_type": "ACTION",
  "importance": 0.8,
  "confidence": 0.95,
  "summary": "Arun Kumar is reminding the recipient to call a plumber.",
  "reason": "The message contains a direct request ('call plumber') that requires an action, which aligns with the 'ACTION' type classification.",
  "contract": {}
}
```
```

#### Parsed Contract JSON:
```json
{
  "signal_type": "ACTION",
  "importance": 0.8,
  "confidence": 0.95,
  "summary": "Arun Kumar is reminding the recipient to call a plumber.",
  "reason": "The message contains a direct request ('call plumber') that requires an action, which aligns with the 'ACTION' type classification.",
  "contract": {}
}
```

---

### Signal 5 (ID: 8684)
* **Sender**: `Senthil RFC`
* **Timestamp**: `2026-06-25T16:38:55.135+00:00`
* **Message**: *"Can you share the mercury one gate url if possible"*
* **Response Time**: `2.93 seconds`
* **Parse Status**: `SUCCESS`

#### Exact Prompt Passed:
```text
Analyze the message and classify it into exactly one of these types:
- FINANCIAL: Active transactions, credit/debit alerts, bank spent/received notifications, payment receipts. (Only if money is actively transferred or spent)
- ACTION: Reminders, todos, tasks, chores, or direct requests to do something (e.g. 'call plumber', 'buy milk').
- FYI: Schedules, bookings, flight/train/movie status, appointments, non-actionable info. (e.g. 'flight AI-101 scheduled')
- FACT: User context, credentials, passport, birthday, height/weight info.
- NOISE: Greetings, spam, chit-chat, OTPs, promotional codes, or generic messages.

Message to analyze:
Sender: Senthil RFC
Source: whatsapp
Content: Can you share the mercury one gate url if possible
Timestamp: 2026-06-25T16:38:55.135+00:00

Respond ONLY with a single JSON object. Do not wrap in markdown or code blocks.
JSON format keys:
"signal_type" (one of the 5 uppercase types above),
"importance" (float 0.0 to 1.0),
"confidence" (float 0.0 to 1.0),
"summary" (1-sentence description),
"reason" (short classification justification),
"contract" (object of details, e.g. for NOISE it is {}).

Contract fields per type:
- FINANCIAL: amount, currency, transaction_type (DEBIT/CREDIT), payment_channel (UPI/CARD/CASH/UNKNOWN), merchant
- ACTION: task_name, assignee, due_date
- FYI: event_name, event_time, description
- FACT: entity, attribute, value
- NOISE: {}

```

#### Raw Model Response:
```json
```json
{
  "signal_type": "ACTION",
  "importance": 0.2,
  "confidence": 0.85,
  "summary": "A request for information about a URL related to mercury one gate.",
  "reason": "The message is asking for specific information (a URL) that requires an action, which falls under the 'ACTION' category.",
  "contract": {}
}
```
```

#### Parsed Contract JSON:
```json
{
  "signal_type": "ACTION",
  "importance": 0.2,
  "confidence": 0.85,
  "summary": "A request for information about a URL related to mercury one gate.",
  "reason": "The message is asking for specific information (a URL) that requires an action, which falls under the 'ACTION' category.",
  "contract": {}
}
```

---

### Signal 6 (ID: 8685)
* **Sender**: `WhatsApp: Senthil RFC`
* **Timestamp**: `2026-06-25T16:41:16.265+00:00`
* **Message**: *"Got the link"*
* **Response Time**: `5.38 seconds`
* **Parse Status**: `SUCCESS`

#### Exact Prompt Passed:
```text
Analyze the message and classify it into exactly one of these types:
- FINANCIAL: Active transactions, credit/debit alerts, bank spent/received notifications, payment receipts. (Only if money is actively transferred or spent)
- ACTION: Reminders, todos, tasks, chores, or direct requests to do something (e.g. 'call plumber', 'buy milk').
- FYI: Schedules, bookings, flight/train/movie status, appointments, non-actionable info. (e.g. 'flight AI-101 scheduled')
- FACT: User context, credentials, passport, birthday, height/weight info.
- NOISE: Greetings, spam, chit-chat, OTPs, promotional codes, or generic messages.

Message to analyze:
Sender: WhatsApp: Senthil RFC
Source: whatsapp
Content: Got the link
Timestamp: 2026-06-25T16:41:16.265+00:00

Respond ONLY with a single JSON object. Do not wrap in markdown or code blocks.
JSON format keys:
"signal_type" (one of the 5 uppercase types above),
"importance" (float 0.0 to 1.0),
"confidence" (float 0.0 to 1.0),
"summary" (1-sentence description),
"reason" (short classification justification),
"contract" (object of details, e.g. for NOISE it is {}).

Contract fields per type:
- FINANCIAL: amount, currency, transaction_type (DEBIT/CREDIT), payment_channel (UPI/CARD/CASH/UNKNOWN), merchant
- ACTION: task_name, assignee, due_date
- FYI: event_name, event_time, description
- FACT: entity, attribute, value
- NOISE: {}

```

#### Raw Model Response:
```json
```json
{
  "signal_type": "ACTION",
  "importance": 0.8,
  "confidence": 0.95,
  "summary": "A reminder to call a plumber.",
  "reason": "The message contains the phrase 'call plumber', which is typically associated with action requests.",
  "contract": {}
}
```
```

#### Parsed Contract JSON:
```json
{
  "signal_type": "ACTION",
  "importance": 0.8,
  "confidence": 0.95,
  "summary": "A reminder to call a plumber.",
  "reason": "The message contains the phrase 'call plumber', which is typically associated with action requests.",
  "contract": {}
}
```

---

### Signal 7 (ID: 8686)
* **Sender**: `WhatsApp: Shraddha Jaiswal`
* **Timestamp**: `2026-06-25T17:05:46.826+00:00`
* **Message**: *"Done , User!"*
* **Response Time**: `6.02 seconds`
* **Parse Status**: `SUCCESS`

#### Exact Prompt Passed:
```text
Analyze the message and classify it into exactly one of these types:
- FINANCIAL: Active transactions, credit/debit alerts, bank spent/received notifications, payment receipts. (Only if money is actively transferred or spent)
- ACTION: Reminders, todos, tasks, chores, or direct requests to do something (e.g. 'call plumber', 'buy milk').
- FYI: Schedules, bookings, flight/train/movie status, appointments, non-actionable info. (e.g. 'flight AI-101 scheduled')
- FACT: User context, credentials, passport, birthday, height/weight info.
- NOISE: Greetings, spam, chit-chat, OTPs, promotional codes, or generic messages.

Message to analyze:
Sender: WhatsApp: Shraddha Jaiswal
Source: whatsapp
Content: Done , User!
Timestamp: 2026-06-25T17:05:46.826+00:00

Respond ONLY with a single JSON object. Do not wrap in markdown or code blocks.
JSON format keys:
"signal_type" (one of the 5 uppercase types above),
"importance" (float 0.0 to 1.0),
"confidence" (float 0.0 to 1.0),
"summary" (1-sentence description),
"reason" (short classification justification),
"contract" (object of details, e.g. for NOISE it is {}).

Contract fields per type:
- FINANCIAL: amount, currency, transaction_type (DEBIT/CREDIT), payment_channel (UPI/CARD/CASH/UNKNOWN), merchant
- ACTION: task_name, assignee, due_date
- FYI: event_name, event_time, description
- FACT: entity, attribute, value
- NOISE: {}

```

#### Raw Model Response:
```json
```json
{
  "signal_type": "ACTION",
  "importance": 0.8,
  "confidence": 0.95,
  "summary": "A message indicating that User has been completed by Shraddha Jaiswal.",
  "reason": "The content 'Done, User!' is a direct request to do something (task) and does not involve any financial transactions or scheduling information.",
  "contract": {}
}
```
```

#### Parsed Contract JSON:
```json
{
  "signal_type": "ACTION",
  "importance": 0.8,
  "confidence": 0.95,
  "summary": "A message indicating that User has been completed by Shraddha Jaiswal.",
  "reason": "The content 'Done, User!' is a direct request to do something (task) and does not involve any financial transactions or scheduling information.",
  "contract": {}
}
```

---

### Signal 8 (ID: 8888)
* **Sender**: `Contact_1`
* **Timestamp**: `2026-07-02T03:25:22.768+00:00`
* **Message**: *"📷 Photo"*
* **Response Time**: `5.24 seconds`
* **Parse Status**: `SUCCESS`

#### Exact Prompt Passed:
```text
Analyze the message and classify it into exactly one of these types:
- FINANCIAL: Active transactions, credit/debit alerts, bank spent/received notifications, payment receipts. (Only if money is actively transferred or spent)
- ACTION: Reminders, todos, tasks, chores, or direct requests to do something (e.g. 'call plumber', 'buy milk').
- FYI: Schedules, bookings, flight/train/movie status, appointments, non-actionable info. (e.g. 'flight AI-101 scheduled')
- FACT: User context, credentials, passport, birthday, height/weight info.
- NOISE: Greetings, spam, chit-chat, OTPs, promotional codes, or generic messages.

Message to analyze:
Sender: Contact_1
Source: whatsapp
Content: 📷 Photo
Timestamp: 2026-07-02T03:25:22.768+00:00

Respond ONLY with a single JSON object. Do not wrap in markdown or code blocks.
JSON format keys:
"signal_type" (one of the 5 uppercase types above),
"importance" (float 0.0 to 1.0),
"confidence" (float 0.0 to 1.0),
"summary" (1-sentence description),
"reason" (short classification justification),
"contract" (object of details, e.g. for NOISE it is {}).

Contract fields per type:
- FINANCIAL: amount, currency, transaction_type (DEBIT/CREDIT), payment_channel (UPI/CARD/CASH/UNKNOWN), merchant
- ACTION: task_name, assignee, due_date
- FYI: event_name, event_time, description
- FACT: entity, attribute, value
- NOISE: {}

```

#### Raw Model Response:
```json
{
  "signal_type": "ACTION",
  "importance": 0.8,
  "confidence": 0.95,
  "summary": "A photo message from Contact_1.",
  "reason": "The content is a photo sent via WhatsApp, which falls under the ACTION category as it involves an action (taking a photo).",
  "contract": {}
}
```

#### Parsed Contract JSON:
```json
{
  "signal_type": "ACTION",
  "importance": 0.8,
  "confidence": 0.95,
  "summary": "A photo message from Contact_1.",
  "reason": "The content is a photo sent via WhatsApp, which falls under the ACTION category as it involves an action (taking a photo).",
  "contract": {}
}
```

---

### Signal 9 (ID: 8687)
* **Sender**: `Shraddha Jaiswal`
* **Timestamp**: `2026-06-25T17:05:46.835+00:00`
* **Message**: *"Done , User!"*
* **Response Time**: `6.62 seconds`
* **Parse Status**: `SUCCESS`

#### Exact Prompt Passed:
```text
Analyze the message and classify it into exactly one of these types:
- FINANCIAL: Active transactions, credit/debit alerts, bank spent/received notifications, payment receipts. (Only if money is actively transferred or spent)
- ACTION: Reminders, todos, tasks, chores, or direct requests to do something (e.g. 'call plumber', 'buy milk').
- FYI: Schedules, bookings, flight/train/movie status, appointments, non-actionable info. (e.g. 'flight AI-101 scheduled')
- FACT: User context, credentials, passport, birthday, height/weight info.
- NOISE: Greetings, spam, chit-chat, OTPs, promotional codes, or generic messages.

Message to analyze:
Sender: Shraddha Jaiswal
Source: whatsapp
Content: Done , User!
Timestamp: 2026-06-25T17:05:46.835+00:00

Respond ONLY with a single JSON object. Do not wrap in markdown or code blocks.
JSON format keys:
"signal_type" (one of the 5 uppercase types above),
"importance" (float 0.0 to 1.0),
"confidence" (float 0.0 to 1.0),
"summary" (1-sentence description),
"reason" (short classification justification),
"contract" (object of details, e.g. for NOISE it is {}).

Contract fields per type:
- FINANCIAL: amount, currency, transaction_type (DEBIT/CREDIT), payment_channel (UPI/CARD/CASH/UNKNOWN), merchant
- ACTION: task_name, assignee, due_date
- FYI: event_name, event_time, description
- FACT: entity, attribute, value
- NOISE: {}

```

#### Raw Model Response:
```json
```json
{
  "signal_type": "ACTION",
  "importance": 0.8,
  "confidence": 0.95,
  "summary": "A message indicating that User's task has been completed.",
  "reason": "The content 'Done, User!' is a direct request to do something (task completion) and does not involve money transactions or any other context-specific information.",
  "contract": {}
}
```
```

#### Parsed Contract JSON:
```json
{
  "signal_type": "ACTION",
  "importance": 0.8,
  "confidence": 0.95,
  "summary": "A message indicating that User's task has been completed.",
  "reason": "The content 'Done, User!' is a direct request to do something (task completion) and does not involve money transactions or any other context-specific information.",
  "contract": {}
}
```

---

### Signal 10 (ID: 8688)
* **Sender**: `[REDACTED_SPORTS_GROUP]: ~ Ganesh Pandian 🫰🏾`
* **Timestamp**: `2026-06-26T00:16:33.948+00:00`
* **Message**: *"Guys pls come around 6:30am"*
* **Response Time**: `3.51 seconds`
* **Parse Status**: `SUCCESS`

#### Exact Prompt Passed:
```text
Analyze the message and classify it into exactly one of these types:
- FINANCIAL: Active transactions, credit/debit alerts, bank spent/received notifications, payment receipts. (Only if money is actively transferred or spent)
- ACTION: Reminders, todos, tasks, chores, or direct requests to do something (e.g. 'call plumber', 'buy milk').
- FYI: Schedules, bookings, flight/train/movie status, appointments, non-actionable info. (e.g. 'flight AI-101 scheduled')
- FACT: User context, credentials, passport, birthday, height/weight info.
- NOISE: Greetings, spam, chit-chat, OTPs, promotional codes, or generic messages.

Message to analyze:
Sender: [REDACTED_SPORTS_GROUP]: ~ Ganesh Pandian 🫰🏾
Source: whatsapp
Content: Guys pls come around 6:30am
Timestamp: 2026-06-26T00:16:33.948+00:00

Respond ONLY with a single JSON object. Do not wrap in markdown or code blocks.
JSON format keys:
"signal_type" (one of the 5 uppercase types above),
"importance" (float 0.0 to 1.0),
"confidence" (float 0.0 to 1.0),
"summary" (1-sentence description),
"reason" (short classification justification),
"contract" (object of details, e.g. for NOISE it is {}).

Contract fields per type:
- FINANCIAL: amount, currency, transaction_type (DEBIT/CREDIT), payment_channel (UPI/CARD/CASH/UNKNOWN), merchant
- ACTION: task_name, assignee, due_date
- FYI: event_name, event_time, description
- FACT: entity, attribute, value
- NOISE: {}

```

#### Raw Model Response:
```json
```json
{
  "signal_type": "ACTION",
  "importance": 0.8,
  "confidence": 0.95,
  "summary": "A group call request for a morning meeting.",
  "reason": "The message contains a direct request to do something (call), which is typical of an ACTION type signal.",
  "contract": {}
}
```
```

#### Parsed Contract JSON:
```json
{
  "signal_type": "ACTION",
  "importance": 0.8,
  "confidence": 0.95,
  "summary": "A group call request for a morning meeting.",
  "reason": "The message contains a direct request to do something (call), which is typical of an ACTION type signal.",
  "contract": {}
}
```

---

### Signal 11 (ID: 8889)
* **Sender**: `Downloading video`
* **Timestamp**: `2026-07-02T03:25:28.029+00:00`
* **Message**: *"from Contact_1"*
* **Response Time**: `5.05 seconds`
* **Parse Status**: `SUCCESS`

#### Exact Prompt Passed:
```text
Analyze the message and classify it into exactly one of these types:
- FINANCIAL: Active transactions, credit/debit alerts, bank spent/received notifications, payment receipts. (Only if money is actively transferred or spent)
- ACTION: Reminders, todos, tasks, chores, or direct requests to do something (e.g. 'call plumber', 'buy milk').
- FYI: Schedules, bookings, flight/train/movie status, appointments, non-actionable info. (e.g. 'flight AI-101 scheduled')
- FACT: User context, credentials, passport, birthday, height/weight info.
- NOISE: Greetings, spam, chit-chat, OTPs, promotional codes, or generic messages.

Message to analyze:
Sender: Downloading video
Source: whatsapp
Content: from Contact_1
Timestamp: 2026-07-02T03:25:28.029+00:00

Respond ONLY with a single JSON object. Do not wrap in markdown or code blocks.
JSON format keys:
"signal_type" (one of the 5 uppercase types above),
"importance" (float 0.0 to 1.0),
"confidence" (float 0.0 to 1.0),
"summary" (1-sentence description),
"reason" (short classification justification),
"contract" (object of details, e.g. for NOISE it is {}).

Contract fields per type:
- FINANCIAL: amount, currency, transaction_type (DEBIT/CREDIT), payment_channel (UPI/CARD/CASH/UNKNOWN), merchant
- ACTION: task_name, assignee, due_date
- FYI: event_name, event_time, description
- FACT: entity, attribute, value
- NOISE: {}

```

#### Raw Model Response:
```json
{
  "signal_type": "ACTION",
  "importance": 0.8,
  "confidence": 0.95,
  "summary": "User is downloading a video.",
  "reason": "The message indicates an action (downloading a video) without any financial or informational context.",
  "contract": {}
}
```

#### Parsed Contract JSON:
```json
{
  "signal_type": "ACTION",
  "importance": 0.8,
  "confidence": 0.95,
  "summary": "User is downloading a video.",
  "reason": "The message indicates an action (downloading a video) without any financial or informational context.",
  "contract": {}
}
```

---

### Signal 12 (ID: 8689)
* **Sender**: `[REDACTED_SPORTS_GROUP] (2 messages): ~ Arun Kumar`
* **Timestamp**: `2026-06-26T00:25:37.256+00:00`
* **Message**: *"Sure"*
* **Response Time**: `5.20 seconds`
* **Parse Status**: `SUCCESS`

#### Exact Prompt Passed:
```text
Analyze the message and classify it into exactly one of these types:
- FINANCIAL: Active transactions, credit/debit alerts, bank spent/received notifications, payment receipts. (Only if money is actively transferred or spent)
- ACTION: Reminders, todos, tasks, chores, or direct requests to do something (e.g. 'call plumber', 'buy milk').
- FYI: Schedules, bookings, flight/train/movie status, appointments, non-actionable info. (e.g. 'flight AI-101 scheduled')
- FACT: User context, credentials, passport, birthday, height/weight info.
- NOISE: Greetings, spam, chit-chat, OTPs, promotional codes, or generic messages.

Message to analyze:
Sender: [REDACTED_SPORTS_GROUP] (2 messages): ~ Arun Kumar
Source: whatsapp
Content: Sure
Timestamp: 2026-06-26T00:25:37.256+00:00

Respond ONLY with a single JSON object. Do not wrap in markdown or code blocks.
JSON format keys:
"signal_type" (one of the 5 uppercase types above),
"importance" (float 0.0 to 1.0),
"confidence" (float 0.0 to 1.0),
"summary" (1-sentence description),
"reason" (short classification justification),
"contract" (object of details, e.g. for NOISE it is {}).

Contract fields per type:
- FINANCIAL: amount, currency, transaction_type (DEBIT/CREDIT), payment_channel (UPI/CARD/CASH/UNKNOWN), merchant
- ACTION: task_name, assignee, due_date
- FYI: event_name, event_time, description
- FACT: entity, attribute, value
- NOISE: {}

```

#### Raw Model Response:
```json
```json
{
  "signal_type": "ACTION",
  "importance": 0.8,
  "confidence": 0.95,
  "summary": "Arun Kumar is responding to a daily badminton update message.",
  "reason": "The sender's name 'Arun Kumar' and the context of receiving a daily update indicate this is an action request.",
  "contract": {}
}
```
```

#### Parsed Contract JSON:
```json
{
  "signal_type": "ACTION",
  "importance": 0.8,
  "confidence": 0.95,
  "summary": "Arun Kumar is responding to a daily badminton update message.",
  "reason": "The sender's name 'Arun Kumar' and the context of receiving a daily update indicate this is an action request.",
  "contract": {}
}
```

---

### Signal 13 (ID: 8719)
* **Sender**: `[REDACTED_SPORTS_GROUP] (2 messages): ~ Contact_3`
* **Timestamp**: `2026-06-27T03:22:49.969+00:00`
* **Message**: *"Same as @⁨~Ganesh Pandian 🫰🏾⁩ said"*
* **Response Time**: `5.28 seconds`
* **Parse Status**: `SUCCESS`

#### Exact Prompt Passed:
```text
Analyze the message and classify it into exactly one of these types:
- FINANCIAL: Active transactions, credit/debit alerts, bank spent/received notifications, payment receipts. (Only if money is actively transferred or spent)
- ACTION: Reminders, todos, tasks, chores, or direct requests to do something (e.g. 'call plumber', 'buy milk').
- FYI: Schedules, bookings, flight/train/movie status, appointments, non-actionable info. (e.g. 'flight AI-101 scheduled')
- FACT: User context, credentials, passport, birthday, height/weight info.
- NOISE: Greetings, spam, chit-chat, OTPs, promotional codes, or generic messages.

Message to analyze:
Sender: [REDACTED_SPORTS_GROUP] (2 messages): ~ Contact_3
Source: whatsapp
Content: Same as @⁨~Ganesh Pandian 🫰🏾⁩ said
Timestamp: 2026-06-27T03:22:49.969+00:00

Respond ONLY with a single JSON object. Do not wrap in markdown or code blocks.
JSON format keys:
"signal_type" (one of the 5 uppercase types above),
"importance" (float 0.0 to 1.0),
"confidence" (float 0.0 to 1.0),
"summary" (1-sentence description),
"reason" (short classification justification),
"contract" (object of details, e.g. for NOISE it is {}).

Contract fields per type:
- FINANCIAL: amount, currency, transaction_type (DEBIT/CREDIT), payment_channel (UPI/CARD/CASH/UNKNOWN), merchant
- ACTION: task_name, assignee, due_date
- FYI: event_name, event_time, description
- FACT: entity, attribute, value
- NOISE: {}

```

#### Raw Model Response:
```json
```json
{
  "signal_type": "ACTION",
  "importance": 0.8,
  "confidence": 0.95,
  "summary": "[REDACTED_SPORTS_GROUP] from Contact_3.",
  "reason": "The message contains a recurring update on daily activities, which is typically categorized as an action request.",
  "contract": {}
}
```
```

#### Parsed Contract JSON:
```json
{
  "signal_type": "ACTION",
  "importance": 0.8,
  "confidence": 0.95,
  "summary": "[REDACTED_SPORTS_GROUP] from Contact_3.",
  "reason": "The message contains a recurring update on daily activities, which is typically categorized as an action request.",
  "contract": {}
}
```

---

### Signal 14 (ID: 8720)
* **Sender**: `Couldn't complete backup`
* **Timestamp**: `2026-06-27T03:27:40.789+00:00`
* **Message**: *"Tap for more info"*
* **Response Time**: `5.69 seconds`
* **Parse Status**: `SUCCESS`

#### Exact Prompt Passed:
```text
Analyze the message and classify it into exactly one of these types:
- FINANCIAL: Active transactions, credit/debit alerts, bank spent/received notifications, payment receipts. (Only if money is actively transferred or spent)
- ACTION: Reminders, todos, tasks, chores, or direct requests to do something (e.g. 'call plumber', 'buy milk').
- FYI: Schedules, bookings, flight/train/movie status, appointments, non-actionable info. (e.g. 'flight AI-101 scheduled')
- FACT: User context, credentials, passport, birthday, height/weight info.
- NOISE: Greetings, spam, chit-chat, OTPs, promotional codes, or generic messages.

Message to analyze:
Sender: Couldn't complete backup
Source: whatsapp
Content: Tap for more info
Timestamp: 2026-06-27T03:27:40.789+00:00

Respond ONLY with a single JSON object. Do not wrap in markdown or code blocks.
JSON format keys:
"signal_type" (one of the 5 uppercase types above),
"importance" (float 0.0 to 1.0),
"confidence" (float 0.0 to 1.0),
"summary" (1-sentence description),
"reason" (short classification justification),
"contract" (object of details, e.g. for NOISE it is {}).

Contract fields per type:
- FINANCIAL: amount, currency, transaction_type (DEBIT/CREDIT), payment_channel (UPI/CARD/CASH/UNKNOWN), merchant
- ACTION: task_name, assignee, due_date
- FYI: event_name, event_time, description
- FACT: entity, attribute, value
- NOISE: {}

```

#### Raw Model Response:
```json
{
  "signal_type": "NOISE",
  "importance": 0.1,
  "confidence": 0.5,
  "summary": "A generic message with no clear context or action.",
  "reason": "The message contains a generic request for more information without any specific details or urgency, which is not related to financial transactions, tasks, schedules, credentials, height/weight, active payments, reminders, or non-actionable info.",
  "contract": {}
}
```

#### Parsed Contract JSON:
```json
{
  "signal_type": "NOISE",
  "importance": 0.1,
  "confidence": 0.5,
  "summary": "A generic message with no clear context or action.",
  "reason": "The message contains a generic request for more information without any specific details or urgency, which is not related to financial transactions, tasks, schedules, credentials, height/weight, active payments, reminders, or non-actionable info.",
  "contract": {}
}
```

---

### Signal 15 (ID: 8721)
* **Sender**: `Couldn't complete backup`
* **Timestamp**: `2026-06-27T03:37:46.593+00:00`
* **Message**: *"Tap for more info"*
* **Response Time**: `4.44 seconds`
* **Parse Status**: `SUCCESS`

#### Exact Prompt Passed:
```text
Analyze the message and classify it into exactly one of these types:
- FINANCIAL: Active transactions, credit/debit alerts, bank spent/received notifications, payment receipts. (Only if money is actively transferred or spent)
- ACTION: Reminders, todos, tasks, chores, or direct requests to do something (e.g. 'call plumber', 'buy milk').
- FYI: Schedules, bookings, flight/train/movie status, appointments, non-actionable info. (e.g. 'flight AI-101 scheduled')
- FACT: User context, credentials, passport, birthday, height/weight info.
- NOISE: Greetings, spam, chit-chat, OTPs, promotional codes, or generic messages.

Message to analyze:
Sender: Couldn't complete backup
Source: whatsapp
Content: Tap for more info
Timestamp: 2026-06-27T03:37:46.593+00:00

Respond ONLY with a single JSON object. Do not wrap in markdown or code blocks.
JSON format keys:
"signal_type" (one of the 5 uppercase types above),
"importance" (float 0.0 to 1.0),
"confidence" (float 0.0 to 1.0),
"summary" (1-sentence description),
"reason" (short classification justification),
"contract" (object of details, e.g. for NOISE it is {}).

Contract fields per type:
- FINANCIAL: amount, currency, transaction_type (DEBIT/CREDIT), payment_channel (UPI/CARD/CASH/UNKNOWN), merchant
- ACTION: task_name, assignee, due_date
- FYI: event_name, event_time, description
- FACT: entity, attribute, value
- NOISE: {}

```

#### Raw Model Response:
```json
{
  "signal_type": "NOISE",
  "importance": 0.1,
  "confidence": 0.2,
  "summary": "A generic message with no clear context or action.",
  "reason": "The message contains a generic request for more information without any specific details or urgency.",
  "contract": {}
}
```

#### Parsed Contract JSON:
```json
{
  "signal_type": "NOISE",
  "importance": 0.1,
  "confidence": 0.2,
  "summary": "A generic message with no clear context or action.",
  "reason": "The message contains a generic request for more information without any specific details or urgency.",
  "contract": {}
}
```

---
