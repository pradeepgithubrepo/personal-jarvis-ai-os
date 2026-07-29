# 🧠 Signal Understanding & Analysis (SUA) & Classification

The **Signal Understanding & Analysis (SUA)** layer is the cognitive core of **Jarvis Personal AI OS**. It receives `QUALIFIED` signals from the Consumption Pipeline, extracts key semantic metadata, synthesizes unified **Intelligence Contracts**, and routes classified intent to specialized AI domain agents.

---

## 🏗️ Architecture & Dual-Path Engine

SUA operates a hybrid dual-path processing model contact_7ncing zero-latency structured execution with LLM intelligence for unstructured data.

```mermaid
flowchart TD
    subgraph Input ["📥 Qualified Signal Entry"]
        S1["Qualified Signal\n(from qualified_signals table)"]
    end

    subgraph SUA ["🧠 Signal Understanding Agent (sua/agent.py)"]
        S1 --> C1{"Source check:\nIs source GPay or Bank Statement?"}
        
        %% Fast Path Bypass
        C1 -->|YES - Metadata Complete| P1["⚡ Metadata-First Bypass Path"]
        P1 --> P2["Extract exact Amount, Currency,\nTransaction Type & Counterparty"]
        P2 --> P3["Build Contract (Confidence: 1.0)\nProcessing Path: metadata_bypass"]

        %% LLM Cognitive Path
        C1 -->|NO - Unstructured Text| L1["🤖 Cognitive LLM Path (LLMClient)"]
        L1 --> L2["Local Model: qwen2.5:1.5b\n(or Remote API Provider)"]
        L2 --> L3["Entity Extraction & Intent Classification\n(FINANCIAL, TODO, FYI, DAILY_BRIEFING)"]
        L3 --> L4["Synthesize Contract JSON & Assign\nImportance (0.0 - 1.0) & Confidence"]
    end

    subgraph DB ["💾 Intelligence Persistence"]
        P3 --> DB1["Insert into understood_signals table"]
        L4 --> DB1
    end

    subgraph Dispatch ["🔀 Intelligence Router & Dispatcher"]
        DB1 --> R1["Dispatcher (dispatch/dispatcher.py)"]
        R1 --> R2{"Lookup Signal Type in Registry"}
        R2 -->|FINANCIAL| A1["Financial Agent"]
        R2 -->|TODO| A2["Todo Agent"]
        R2 -->|FYI| A3["FYI Agent"]
        R2 -->|DAILY_BRIEFING| A4["Daily Briefing Agent"]
    end
```

---

## ⚡ Dual-Path Processing Breakdown

### Path A: Metadata-First Bypass (Deterministic, 1.0 Confidence)
When signals originate from structured sources such as bank PDF statements or Google Pay exports, the required data fields (amount, currency, counterparty, DEBIT/CREDIT) are already verified during ingestion.
* **Execution Time**: ~1ms (Zero LLM overhead)
* **Confidence Level**: `1.0` (100%)
* **LLM Used**: None (`llm_model_used: null`)
* **Contract Output**: Instantly constructs a clean schema-compliant financial transaction contract.

### Path B: LLM Cognitive Analysis (Probabilistic)
For unstructured inputs like bank SMS messages, email summaries, or ambient notifications:
1. **Model**: Utilizes `qwen2.5:1.5b` (or configured Ollama/OpenAI/Gemini providers via `LLMClient`).
2. **Entity Extraction**: `extract_entities()` extracts capitalized words, merchant names, account identifiers, and dates.
3. **Intent Classification**: Evaluates signal semantics to assign a primary target domain:
   * 💰 `FINANCIAL`: Debit/Credit notifications, bill payments, refund alerts.
   * 📝 `TODO`: Actionable task requests, bill due date reminders, follow-ups.
   * ℹ️ `FYI`: Informational updates, flight status, delivery notifications without explicit user actions.
   * 🗞️ `DAILY_BRIEFING`: Digest summary triggers or status updates.

---

## 📜 Unified Intelligence Contract Schema

Every understood signal is converted into a standard JSON payload stored in `understood_signals.contract_json`.

```json
{
  "signal_type": "FINANCIAL",
  "importance": 0.95,
  "confidence": 1.0,
  "summary": "Paid INR 450.00 to Swiggy",
  "reason": "Structured gpay metadata bypass",
  "processing_path": "metadata_bypass",
  "contract_json": {
    "amount": 450.00,
    "currency": "INR",
    "transaction_type": "DEBIT",
    "payment_channel": "UPI",
    "merchant": "Swiggy"
  }
}
```

---

## 🔄 SUA Processing Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    participant Engine as Pipeline Orchestrator
    participant SUA as SUA Agent (sua/agent.py)
    participant LLM as LLM Client (qwen2.5:1.5b)
    participant DB as Postgres (understood_signals)
    participant Dispatcher as Dispatcher (dispatch/dispatcher.py)
    participant Agent as Target Domain Agent

    Engine->>SUA: understand_signal(signal)
    alt Is Metadata Complete (GPay / Statement)
        SUA->>SUA: Extract fields from source_metadata
        SUA->>DB: Save understood_signal (path="metadata_bypass", confidence=1.0)
    else Is Unstructured Text / SMS
        SUA->>LLM: Prompt LLM for classification & JSON schema
        LLM-->>SUA: Return classified JSON payload
        SUA->>DB: Save understood_signal (path="llm", confidence=0.85-0.95)
    end

    SUA->>Dispatcher: dispatch_understood_signal(signal_id)
    Dispatcher->>DB: Fetch contract & signal_type
    Dispatcher->>Agent: Route to registered agent handler (e.g. FinancialAgent.process())
```

---

## 📑 Deep-Dive & Historical References

For detailed benchmark results, root cause analysis documents, and routing rules specifications, refer to these documents in `docs/v2/`:

* 📐 **Understood Signals Blueprint**: [UNDERSTOOD_SIGNALS_BLUEPRINT_V1.md](../v2/understanding_layer/UNDERSTOOD_SIGNALS_BLUEPRINT_V1.md)
* 🧠 **Classification RCA & Analysis**: [UNDERSTANDING_CLASSIFICATION_RCA.md](../v2/understanding_layer/UNDERSTANDING_CLASSIFICATION_RCA.md)
* 📊 **LLM Benchmark Report**: [LLM_BENCHMARK_REPORT.md](../v2/understanding_layer/LLM_BENCHMARK_REPORT.md)
* 📜 **Contract Schema Specification**: [CONTRACT_SCHEMA_V1.md](../v2/phase2b/CONTRACT_SCHEMA_V1.md)
* 🔀 **Dispatch Framework**: [DISPATCH_FRAMEWORK.md](../v2/phase2b/DISPATCH_FRAMEWORK.md)
* 🏗️ **Routing Architecture**: [ROUTING_ARCHITECTURE.md](../v2/phase2b/ROUTING_ARCHITECTURE.md)
* 🚦 **Routing Rules Specification**: [ROUTING_RULES.md](../v2/phase2b/ROUTING_RULES.md)

---

[← Consumption Pipeline](01_CONSUMPTION_PIPELINE.md) | [Return to Root README](../../README.md) | [Next: Agent Ecosystem →](03_AGENT_ECOSYSTEM.md)
