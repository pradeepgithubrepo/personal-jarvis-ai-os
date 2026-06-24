# Jarvis Signal Understanding Agent: Architecture & Design Review

This document decomposes and reviews the architecture for the **Signal Understanding Agent**, the first LLM-powered cognitive layer in the Jarvis AI OS pipeline. 

```
   Raw Signals (SMS, WhatsApp, Email)
                   │
                   ▼
       Signal Qualification Agent (Module 2A)
                   │
                   ▼ [qualified_signals]
     ┌────────────────────────────────────────┐
     │      Signal Understanding Agent        │  ◄── [Rules Engine & Overrides]
     └────────────────────────────────────────┘
                   │
                   ▼ [Canonical Signal Contract]
    ┌──────────────┼──────────────┬──────────────┐
    ▼              ▼              ▼              ▼
Todo Agent  Financial Agent   FyiAgent    Fact Agent
```

---

## 1. Existing Logic Inventory

A review of the current codebase (`MobileIntentExtractor`, `SignalProcessor`, `RulesEngine`, `FinancialClassifier`, and pipeline orchestrators) reveals a mix of heuristic rules, local LLM calls, and hardcoded overrides. Below is the inventory of what survives, moves, gets deleted, or gets simplified.

### Current Logic Mapping
| Module / Feature | Current Behavior | Future State | Rationale |
| :--- | :--- | :--- | :--- |
| **Rule-Based Pre-Classification** | Detects OTPs, system notifications, promotional spam, and data limit warnings inside `MobileIntentExtractor` & `MobileNoiseFilter`. | **Survives & Moves** to the Qualification Agent stage. | Pre-LLM filtering prevents unnecessary token usage and latency. |
| **LLM Intent Classification** | Extracts `intent`, `category`, `priority`, and dynamic `details` using local LLM in `MobileIntentExtractor`. | **Moves** to the **Signal Understanding Agent**. | Centralizes LLM semantic parsing into a single specialized contract emitter. |
| **RulesEngine Exclusions** | Evaluates ignore list (`ignore_topics`, `financial_ignore`) inside `RulesEngine.should_ignore_signal`. | **Survives** as a helper tool within the Signal Understanding Agent. | Provides a high-speed fallback and deterministic safety rail to override LLM behavior. |
| **RulesEngine Merchant / VPA Classification** | Maps transactions to categories like `GROCERY` or `FOOD` using patterns in `jarvis_rules.json` and overrides in `user_overrides.json`. | **Moves** to the downstream **Financial Agent**. | Categorization logic for ledger sheets belongs to the domain expert agent, not the understanding layer. |
| **SQLite & Supabase Direct Writes** | `SignalProcessor` directly creates SQLite rows and invokes `SupabaseRepo` to write `Todo`, `FinancialEvent`, and `FyiEvent`. | **Deleted / Replaced** with routing outputs. | The Signal Understanding Agent does *not* create domain records. It emits a payload, and downstream specialist agents handle persistence. |
| **Heuristic Verb Parsers** | Regex checking for due dates, transaction amounts, and actionable verbs inside `SignalProcessor`. | **Simplified** & relegated to fail-safe LLM recovery. | Relies on LLM entity extraction as primary; regex heuristics only execute if LLM confidence falls below a strict threshold. |

---

## 2. Canonical Signal Contract Review

The target JSON contract acts as the unified schema connecting the Signal Understanding Agent to downstream specialists.

```json
{
  "signal_id": "uuid-v4",
  "signal_type": "school_update | financial_transaction | delivery_update | travel_booking | general",
  "classes": ["ACTION", "INFORMATION", "MEMORY"],
  "domains": ["INSURANCE", "MEDICAL", "TRAVEL", "WORK", "EDUCATION", "FINANCE"],
  "importance": "CRITICAL | HIGH | MEDIUM | LOW | IGNORE",
  "summary": "Short, clear synthesis of the notification",
  "confidence": 0.95,
  "reason": "Derived from keyword 'due date' and sender 'Oakridge School'",
  "entities": {
    "people": [],
    "organizations": [],
    "merchants": [],
    "monetary_value": {
      "amount": 0.0,
      "currency": "INR"
    },
    "deadlines": [],
    "appointments": [],
    "locations": [],
    "travel_bookings": {},
    "bills": {},
    "insurance_policies": {},
    "medical_events": {}
  },
  "routes": ["TodoAgent", "FyiAgent"],
  "raw_context": {
    "source": "whatsapp | sms | email",
    "sender": "Class Group",
    "timestamp": "2026-06-23T14:20:00Z"
  }
}
```

### Recommended Schema Additions:
1. **`domains` (Array)**: Separates the **structural behavior class** (`ACTION`, `FINANCIAL`) from the **life domain** (`INSURANCE`, `MEDICAL`, `TRAVEL`).
2. **`is_verified` (Boolean)**: Explicitly tracks whether this signal bypasses human review or needs approval.
3. **Structured Sub-Entities**:
   * `travel_bookings`: `{ "pnr": "XYZ123", "departure_time": "...", "mode": "flight|train" }`
   * `bills`: `{ "biller": "Airtel", "account_number": "998811", "due_date": "YYYY-MM-DD" }`
   * `insurance_policies`: `{ "policy_number": "POL-99", "insurer": "LIC", "renewal_date": "YYYY-MM-DD" }`

---

## 3. Class & Domain Taxonomy Review

We validate the primary classes and distinguish them from domains:

### Primary Classes (Behavioral - How Jarvis processes the signal)
* **ACTION**: Demands user effort. Spawns tasks/todos downstream.
* **FINANCIAL**: Demands ledger tracking. Spawns expenses or receipts.
* **INFORMATION**: Informational circular, status update, or FYI newsletter.
* **MEMORY**: Ground truth facts, preferences, dates, or contact associations.
* **ALERT**: High-priority security or critical warnings requiring immediate alarm.
* **NOISE**: Junk, OTPs (redundant after qualification, but kept for audit).

### Domains (Semantic - Contextual categorization tags)
Domains represent areas of life. They do *not* dictate behavior on their own; instead, they refine how the downstream agents store and categorize the extracted entities:
* **INSURANCE**: Maps to policies, coverage values, renewal deadlines.
* **MEDICAL**: Maps to appointments, symptoms, prescriptions, and lab tests.
* **TRAVEL**: Maps to itineraries, PNR codes, hotels, and flight schedules.
* **WORK**: Separates occupational alerts from family and personal tasks.
* **EDUCATION**: Specific to children’s homework, school circulars, fees, and syllabus events.

---

## 4. Entity Model Review

The entity extraction schema must handle both flat entities and complex domain-specific objects:

```json
{
  "people": ["Shobana", "Teacher"],
  "organizations": ["Oakridge School", "HDFC Bank"],
  "merchants": ["Zomato", "Amazon"],
  "monetary_value": {
    "amount": 1500.00,
    "currency": "INR"
  },
  "deadlines": ["2026-06-25"],
  "appointments": ["2026-06-25T10:30:00Z"],
  "locations": ["Apollo Clinic, T-Nagar"],
  "travel_bookings": {
    "pnr": "67890AA",
    "carrier": "Indigo",
    "flight_number": "6E-123",
    "origin": "MAA",
    "destination": "BLR",
    "departure_time": "2026-07-01T08:00:00Z"
  },
  "bills": {
    "provider": "TNEB",
    "account_id": "45678",
    "billing_period": "June 2026"
  },
  "insurance_policies": {
    "policy_name": "Optima Restore",
    "policy_type": "Health",
    "insurer": "HDFC Ergo"
  },
  "medical_events": {
    "patient": "Pradeep",
    "doctor": "Dr. Ramesh",
    "specialty": "Cardiology",
    "instructions": "Fast for 12 hours before test"
  }
}
```

---

## 5. Routing Design

Downstream agent routing is triggered dynamically by evaluating the extracted `classes` and `domains`:

```
                    [Canonical Signal Contract]
                                │
             ┌──────────────────┼──────────────────┐
             ▼                  ▼                  ▼
     classes.contains   classes.contains   classes.contains
        ("ACTION")        ("FINANCIAL")       ("MEMORY")
             │                  │                  │
             ▼                  ▼                  ▼
         Todo Agent      Financial Agent       Fact Agent
```

### Composite Routing Matrix
| Signal Scenario | Class Composition | Domain | Downstream Agent Routes |
| :--- | :--- | :--- | :--- |
| **School Circular** | `[INFORMATION, ACTION]` | `EDUCATION` | `FyiAgent` (reads details), `TodoAgent` (sets deadline) |
| **UPI Debit Alert** | `[FINANCIAL]` | `FINANCE` | `FinancialAgent` (logs outflow) |
| **Insurance Renewal Alert** | `[FINANCIAL, ACTION]` | `INSURANCE` | `FinancialAgent` (logs bill), `TodoAgent` (sets renewal todo) |
| **Doctor Appointment Confirmation** | `[ACTION, MEMORY]` | `MEDICAL` | `TodoAgent` (sets calendar event), `FactAgent` (logs provider contact info) |
| **Amazon Order Delivery** | `[INFORMATION]` | `TRAVEL` | `FyiAgent` (records delivery milestone) |

---

## 6. Confidence Strategy

To maintain pipeline accuracy, we apply a hybrid logic model for calculating classification and extraction confidence.

```
                  ┌──────────────────────────────┐
                  │      Qualified Signal        │
                  └──────────────┬───────────────┘
                                 │
                     [Deterministic Rules Check]
                                 │
                 ┌───────────────┴───────────────┐
                 ▼ (Rules Match)                 ▼ (No Rules Match)
         [Confidence = 1.0]              [Invoke LLM Parser]
         [Auto-Process]                  [LLM Confidence Score (0.0-1.0)]
                                                 │
                                     ┌───────────┴───────────┐
                                     ▼ (Score >= 0.85)       ▼ (Score < 0.85)
                              [Auto-Process]        [Flag: Requires Review]
                                                             │
                                                             ▼
                                                   [Streamlit UI Queue]
```

### Threshold Action Rules
1. **Auto-Process (`>= 0.85`)**: No human verification required. Payload is committed to `understood_signals` and routed instantly.
2. **Review Required (`0.50 - 0.84`)**: Routed to downstream tables but marked `requires_review = true`. A card is added to the diagnostic Streamlit interface.
3. **Manual Override / Fail-Safe (`< 0.50` or JSON Parse Error)**: The signal's raw text is placed directly in the **Critical Inbox Review Queue**. No downstream routing occurs until the user provides classification/entity tags.

---

## 7. Persistence Design

We propose the following schema design for SQLite and Supabase to track signal understanding:

### `understood_signals` Table
| Column Name | Data Type | Constraints | Purpose |
| :--- | :--- | :--- | :--- |
| `id` | UUID | PRIMARY KEY | Unique identifier for understood state. |
| `qualified_signal_id` | UUID | FOREIGN KEY | Reference to raw qualification signal. |
| `signal_type` | VARCHAR(50) | NOT NULL | Type classification (e.g. `school_update`). |
| `importance` | VARCHAR(20) | NOT NULL | Importance score (`HIGH`, `LOW`, etc.). |
| `summary` | TEXT | NOT NULL | Synthetic summary generated by LLM. |
| `confidence` | FLOAT | NOT NULL | Confidence value between `0.0` and `1.0`. |
| `reason` | TEXT | NULL | Classification justification rationale. |
| `is_verified` | BOOLEAN | DEFAULT FALSE | Whether confirmed by user / high confidence. |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP| Ingestion timestamp. |

### `signal_entities` Table
| Column Name | Data Type | Constraints | Purpose |
| :--- | :--- | :--- | :--- |
| `id` | UUID | PRIMARY KEY | Unique entity identifier. |
| `understood_signal_id`| UUID | FOREIGN KEY | Association link to understood signal. |
| `entity_type` | VARCHAR(50) | NOT NULL | Category: `people`, `merchants`, `monetary_value`, `deadlines`. |
| `entity_value` | JSONB | NOT NULL | Structured key-value properties or list. |

### `signal_routes` Table
| Column Name | Data Type | Constraints | Purpose |
| :--- | :--- | :--- | :--- |
| `id` | UUID | PRIMARY KEY | Route record ID. |
| `understood_signal_id`| UUID | FOREIGN KEY | Link to parent understanding record. |
| `target_agent` | VARCHAR(50) | NOT NULL | Downstream agent name (`TodoAgent`, `FinancialAgent`). |
| `delivery_status` | VARCHAR(20) | DEFAULT 'PENDING' | Status: `PENDING`, `COMPLETED`, `FAILED`. |
| `error_log` | TEXT | NULL | Execution traceback log for failures. |

---

## 8. Fact Agent Dependency Review

The Fact Agent represents the memory grounding component of Jarvis. The Signal Understanding Agent feeds it metadata to extract recurring patterns and relationships.

```
[Signal Understanding Agent] ──(Emits MEMORY Class)──► [Fact Agent]
                                                          │
                                            ┌─────────────┼─────────────┐
                                            ▼             ▼             ▼
                                       Preferences  Relationships   Locations
```

### Fact Grounding Fields
* **Family Preferences**: Maps merchants/products to family members (e.g., *"Shobana ordered fish from Fishtown"* -> `{"person": "Shobana", "preference": "fresh catch fish", "merchant": "Fishtown"}`).
* **Recurring Behaviors**: Connects credit/debit alerts to scheduling (e.g., *"HDFC debit of 4500 for TNEB"* -> `{"recurring_bill": "electricity", "provider": "TNEB", "approx_day": 23}`).
* **Known Locations**: Correlates addresses/clinics (e.g., *"Appointment at Apollo Clinic"* -> `{"location": "Apollo Clinic", "association": "Health Care"}`).
* **Relationships**: Links contact names to sender tags (e.g., *"Class Group update"* -> `{"school_contact": "Class Group Group", "association": "Oakridge School"}`).

---

## 9. Migration Strategy

To swap the monolithic `SignalProcessor` pipeline with the decoupled architecture safely:

### Decoupled Pipeline Execution Flow
```
Consumer Pipeline
      │
      ▼
[qualified_signals] Table
      │
      ▼
SignalUnderstandingAgent.run()
      │
      ├── 1. Read qualified signals where signal_id NOT IN understood_signals
      ├── 2. Classify and extract entities -> insert to understood_signals & signal_entities
      └── 3. Create target route records in signal_routes
      │
      ▼
Downstream Dispatch Loop
      │
      ├── TodoAgent handles signal_routes where target_agent='TodoAgent'
      ├── FinancialAgent handles signal_routes where target_agent='FinancialAgent'
      └── FyiAgent handles signal_routes where target_agent='FyiAgent'
```

### Phase 1: Shadow Logging (Dual Processing)
* Continue running the original `SignalProcessor` pipeline so SQLite and Supabase production events are unmodified.
* Simultaneously ingest `qualified_signals` into the new `SignalUnderstandingAgent` in a dummy database / dry-run mode. Compare the classification outputs and extraction metrics.

### Phase 2: Schema Insertion
* Execute SQL migration files creating `understood_signals`, `signal_entities`, and `signal_routes`.

### Phase 3:Decoupling the Orchestrator
* Disable direct database inserts in `SignalProcessor`.
* Redirect the pipeline flow: Qualified Signals -> Signal Understanding Agent -> Understood Signals -> Route Dispatcher.

---

## 10. Recommended Final Design

The final interface of the `SignalUnderstandingAgent` is specified as follows:

```python
class SignalUnderstandingAgent:
    """
    Decoupled LLM-powered Understanding layer.
    Processes qualified signals and produces the canonical understanding contract.
    """
    
    def __init__(self, llm_router=None, rules_engine=None):
        self.llm_router = llm_router
        self.rules_engine = rules_engine

    def understand(self, signal: dict) -> dict:
        """
        Translates a qualified raw signal into a canonical understanding contract.
        """
        # 1. Deterministic rules fallback
        rule_result = self.rules_engine.check_deterministic_rules(signal)
        if rule_result:
            return rule_result
            
        # 2. LLM Extraction Prompt
        contract = self._call_llm_parser(signal)
        
        # 3. Confidence Verification
        if contract["confidence"] < 0.85:
            contract["is_verified"] = False
            contract["routes"] = ["UserReviewQueue"]
        else:
            contract["is_verified"] = True
            
        return contract

    def _call_llm_parser(self, signal: dict) -> dict:
        # Calls the local LLM Router with the structured contract schema prompt
        pass
```
