# 📐 End-to-End System Architecture & Data Lifecycle

This document provides a holistic blueprint of the **Jarvis Personal AI OS**, illustrating how hardware collectors, storage infrastructure, processing agents, intelligence routing, and domain ledgers interlock across the complete signal processing lifecycle.

---

## 🗺️ Complete End-to-End System Topology

```mermaid
flowchart TD
    subgraph Layer1 ["1️⃣ Data Collection Layer"]
        App["📱 Android Collector App\n(jarviscollector)"]
        Pdf["📄 PDF Statements & Bank Receipts"]
        Api["🌐 External Webhooks & APIs"]
    end

    subgraph Layer2 ["2️⃣ Ingestion & Qualification Layer (Consumer Agent)"]
        S_Bucket[("☁️ Supabase Storage\n(Ingest Bucket)")]
        App -->|Upload JSON| S_Bucket
        Pdf -->|Upload PDF| S_Bucket
        Api -->|Payload| S_Bucket

        Discovery["ConsumerAgent.discover_files()"]
        HashCheck{"SHA-256 Check\n(processed_files)"}
        QualAgent["SignalQualificationAgent"]
        
        S_Bucket --> Discovery
        Discovery --> HashCheck
        HashCheck -->|New File| QualAgent
        QualAgent --> DB_Qual[("database:\nqualified_signals")]
    end

    subgraph Layer3 ["3️⃣ Cognitive Intelligence Layer (SUA Agent)"]
        DB_Qual -->|QUALIFIED| SUA["SignalUnderstandingAgent"]
        Bypass{"Metadata\nComplete?"}
        LLM["🤖 Local LLM Client\n(qwen2.5:1.5b)"]
        
        SUA --> Bypass
        Bypass -->|Yes| FastPath["⚡ 1.0 Conf Metadata Bypass"]
        Bypass -->|No| LLM
        FastPath --> DB_Understood[("database:\nunderstood_signals")]
        LLM --> DB_Understood
    end

    subgraph Layer4 ["4️⃣ Routing & Dispatch Layer"]
        DB_Understood --> Dispatcher["Dispatcher\n(dispatch/dispatcher.py)"]
        Registry["Dispatch Registry\n(dispatch_registry.py)"]
        Dispatcher --- Registry
    end

    subgraph Layer5 ["5️⃣ Domain Execution & Ledger Persistence Layer"]
        Dispatcher -->|FINANCIAL| Agent_Fin["💳 Financial Agent"]
        Dispatcher -->|FINANCIAL| Agent_FinSum["📊 Financial Summary Agent"]
        Dispatcher -->|TODO| Agent_Todo["📝 Todo Agent"]
        Dispatcher -->|FYI| Agent_FYI["ℹ️ FYI Agent"]
        Dispatcher -->|DAILY_BRIEFING| Agent_Brief["🗞️ Daily Briefing Agent"]

        Agent_Fin --> DB_Fin[("financial_transactions")]
        Agent_FinSum --> DB_FinSum[("financial_summaries")]
        Agent_Todo --> DB_Todo[("todos")]
        Agent_FYI --> DB_FYI[("fyi_entries")]
        Agent_Brief --> DB_Brief[("daily_briefings")]
    end

    subgraph Layer6 ["6️⃣ System Supervision & Replay"]
        Lifecycle["🔄 Lifecycle Agent"] -.->|Health & Backfill| Layer2
        Lifecycle -.->|Replay Engine| Layer3
    end
```

---

## 💾 Primary Data Schema Relationships

The data persistence layer relies on Supabase PostgreSQL. Below is the simplified Entity-Relationship diagram illustrating signal flow through table states:

```mermaid
erDiagram
    pipeline_runs ||--o{ pipeline_run_events : logs
    processed_files ||--|| qualified_signals : qualifies
    qualified_signals ||--|| understood_signals : classifies
    understood_signals }|--o| financial_transactions : creates
    understood_signals }|--o| todos : creates
    understood_signals }|--o| fyi_entries : creates
    understood_signals }|--o| daily_briefings : creates

    processed_files {
        string file_hash PK
        string source_file_name
        timestamp processed_at
    }

    qualified_signals {
        uuid id PK
        string source
        float qualification_score
        string qualification_status
        jsonb metadata
    }

    understood_signals {
        uuid id PK
        uuid qualified_signal_id FK
        string signal_type
        float confidence
        float importance
        jsonb contract_json
    }

    financial_transactions {
        uuid id PK
        decimal amount
        string currency
        string transaction_type
        string category
        string merchant
    }
```

---

## 🔄 End-to-End Signal Execution Lifecycle

1. **Collection**: The mobile collector ([jarviscollector](https://github.com/pradeepgithubrepo/jarviscollector)) intercepts transactional SMS/notifications on Android devices and pushes structured JSON to Supabase.
2. **Ingestion & Dedup**: `ConsumerAgent` computes the SHA-256 digest of the payload. If unique, the file is logged in `processed_files` and passed to `SignalQualificationAgent`.
3. **Qualification**: `SignalQualificationAgent` applies heuristic domain context matching (`config/qualification_rules.json`). Qualified entries are inserted into `qualified_signals` with status `QUALIFIED`.
4. **Understanding (SUA)**: `SignalUnderstandingAgent` reads `QUALIFIED` signals. Structured inputs (GPay, Bank Statements) take the 1.0 confidence metadata bypass path. Unstructured SMS entries are parsed via Ollama/Local LLM (`qwen2.5:1.5b`). Output is saved in `understood_signals`.
5. **Dispatch**: `Dispatcher` matches `signal_type` in `dispatch_registry.py` and routes the contract to registered domain agent handlers.
6. **Execution & Ledger**: Target domain agents (`FinancialAgent`, `TodoAgent`, `FYIAgent`, `DailyBriefingAgent`) write domain-specific entities to dedicated database tables.
7. **Orchestration & Replay**: `LifecycleAgent` monitors pipeline health, executes historical backfills, and triggers the `Replay Framework` when rules or models are updated.

---

## 📑 Deep-Dive & Historical References

For comprehensive technical specifications, replay frameworks, backfill execution reports, and database schemas:

* 🔄 **Replay Framework**: [REPLAY_FRAMEWORK.md](../v2/phase2b/REPLAY_FRAMEWORK.md)
* 📊 **Pipeline Backfill Execution Report**: [PIPELINE_BACKFILL_EXECUTION_REPORT.md](../v2/PIPELINE_BACKFILL_EXECUTION_REPORT.md)
* 📜 **Phase 2b Validation Report**: [PHASE2B_VALIDATION_REPORT.md](../v2/phase2b/PHASE2B_VALIDATION_REPORT.md)
* 🗄️ **Phase 1a Core Database Schema**: [Phase 1a Schema](../v2/phase1a/SCHEMA.md)

---

[← Agent Ecosystem](03_AGENT_ECOSYSTEM.md) | [Return to Root README →](../../README.md)
