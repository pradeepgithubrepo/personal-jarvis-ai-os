# TODO AGENT ALIGNMENT REVIEW
**Transitioning from Route-to-Task Transformer to Local LLM Reasoning Agent**

---

## 1. Gaps Between Current Blueprint & True Agent Behavior

The V1 blueprint treated the To-Do Agent as a **passive route transformer** that automatically converted any signal routed with type `ACTION` into a corresponding task record. This approach introduces significant problems:

| Dimension | Current Blueprint (Transformer) | Required Target (True Agent) |
|:---|:---|:---|
| **Responsibility** | Maps raw signal summaries directly into task fields. | Reasons over the message content, current user context, and existing task state. |
| **Data Quality** | Propagates messy raw messages (e.g., *"Dear Parents. Homework Book 1 page 9."*) straight to the task list. | Translates messy signals into clean, actionable, human-friendly tasks (e.g., *"Complete Homework - Book 1 Page 9"*). |
| **Deduplication** | Inserts a new task for every single routed signal, creating duplicate clutter if an alert arrives via SMS and WhatsApp. | Analyzes semantic overlap with open tasks and decides whether to merge or ignore. |
| **Filtering** | Automatically creates a task for every `ACTION` signal, including non-actionable noise (e.g., *"Reached home"*). | Determines whether a task *should* actually be created, classifying messages into `CREATE_TASK`, `IGNORE`, or `MERGE`. |

---

## 2. Where Local LLM Should Be Introduced

The local LLM (`qwen2.5:1.5b` or equivalent) is invoked during the laptop backend's wake cycle. It runs inside the pull worker's main process loop when executing the To-Do Agent.

```
Laptop Wake
    ↓
Query signal_routes (PENDING + todo_agent)
    ↓
For each route:
    1. Fetch parent understood_signal contract & raw message
    2. Fetch all current OPEN tasks from Supabase
    3. Pass context (Raw Message + Open Tasks) to LLM
    4. LLM parses and returns Structured Task Decision JSON
    5. Perform action (Create, Ignore, or Merge)
    6. Update signal_routes status to COMPLETED
```

### Prompt Construction
The prompt fed to the LLM provides:
1. The **Raw Signal Message** and its parsed metadata (sender, source).
2. The list of **Current Open Tasks** to check for semantic duplication.
3. Strict instructions to return a JSON contract outlining the creation decision.

---

## 3. Deduplication Strategy

To prevent task bloat, the To-Do Agent uses a **semantic deduplication loop**:

1. **Context Loading**: The agent queries Supabase for all `tasks` where `status = 'OPEN'` or `status = 'IN_PROGRESS'` assigned to the user.
2. **LLM Context Injection**: The list of open task titles and descriptions is formatted as a JSON block inside the LLM prompt.
3. **Similarity Assessment**: The LLM evaluates whether the incoming signal represents the same operational event as an existing task.
   - *Example*: Incoming SMS: *"Your bike insurance policy #1234 expires tomorrow."*
   - *Existing Open Task*: *"Renew bike insurance"* (created from an email signal 2 hours earlier).
   - *LLM Decision*: Classifies as `MERGE_WITH_EXISTING`, references the existing task's ID, and appends the new signal reference to the task's lineage audit log or description.

---

## 4. Rationalization Strategy

The core architectural principle is: **"Signals are messy. Tasks must be clean."**
The local LLM is instructed to rewrite tasks into a professional, brief, imperative form (starting with a strong action verb).

```
"Electricity charges of Rs.2527 are due on 27-May."
      ↳ [LLM Reasoning] ↳ "Pay TNEB Electricity Bill"

"Dear Parents. Homework Book 1 page 9."
      ↳ [LLM Reasoning] ↳ "Complete Homework - Book 1 Page 9"

"Your insurance policy expires tomorrow."
      ↳ [LLM Reasoning] ↳ "Renew Bike Insurance"
```

---

## 5. Task Generation Contract

The local LLM must return a structured JSON response matching the following schema. If the LLM response fails validation, the agent falls back to a deterministic mapping of the raw signal summary to prevent system failure.

```json
{
  "decision": "CREATE_TASK", 
  "rationale": "Signal indicates an electricity bill payment due by May 27th.",
  "title": "Pay TNEB Electricity Bill",
  "description": "Electricity charges of Rs.2527 are due on 27-May.",
  "priority": "HIGH",
  "due_datetime": "2026-05-27T23:59:59Z",
  "notification_profile": "IMPORTANT",
  "confidence": 0.95
}
```

### Allowed Values
* **`decision`**: `CREATE_TASK` | `IGNORE` | `MERGE_WITH_EXISTING`
* **`priority`**: `LOW` | `MEDIUM` | `HIGH` | `URGENT`
* **`notification_profile`**: `NONE` | `STANDARD` | `IMPORTANT` | `CRITICAL`

---

## 6. Lineage Preservation Strategy

We preserve complete audit traceability from the final task all the way back to the raw source data. This allows the mobile app UI to show a "View Source" button for any task.

```
tasks.route_id (links to)
    ↳ signal_routes.id
        ↳ signal_routes.understood_signal_id (links to)
            ↳ understood_signals.id
                ↳ understood_signals.qualified_signal_id (links to)
                    ↳ qualified_signals.id
                        ↳ qualified_signals.signal_id (links to)
                            ↳ mobile_signals.id (Raw Message)
```

### Database FK Chain Implementation
* The `tasks` table includes a `route_id UUID REFERENCES signal_routes(id) ON DELETE SET NULL` column.
* For `MERGE_WITH_EXISTING` decisions, we write a record in a simple task audit/history or append to the task's log description, preserving linkage to *both* original routes.

---

## 7. Recommended Implementation Changes

1. **Modify `src/agents/todo/todo_agent.py`**:
   - Integrate `LLMClient` (from `intelligence.llm_client.py`).
   - Implement the `process_pending_routes` loop to fetch open tasks and execute the LLM reasoning prompt.
   - Parse and validate the returned LLM JSON payload.
2. **Supabase Schema**:
   - Establish the `tasks` table with the foreign key `route_id REFERENCES signal_routes(id)`.
3. **Android Client Interface**:
   - Provide an endpoint or direct Supabase select query that retrieves the raw mobile signal text via the foreign key chain, enabling the "View Source" card on the mobile task details screen.
