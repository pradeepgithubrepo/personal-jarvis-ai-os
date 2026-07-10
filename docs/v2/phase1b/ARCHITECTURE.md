# Phase 1B Architecture Document — Source Collectors

This document defines the modular architecture, component relationships, and data dependencies of the Jarvis V2 Source Collectors.

---

## 1. Directory Structure Layout

The Phase 1B implementation is structured inside `src/agents/consumer/` alongside the Phase 1A baseline:

```text
src/agents/consumer/
├── agent.py                 # Core agent (Supabase wrapper)
├── orchestrator.py          # Orchestration pipeline execution
│
├── collectors/              # Subdirectory polling & ingestion
│   ├── whatsapp_collector.py
│   ├── sms_collector.py
│   ├── gpay_collector.py
│   └── bank_statement_collector.py
│
├── parsers/                 # Parsing validation and text extraction
│   ├── whatsapp_parser.py
│   ├── sms_parser.py
│   └── pdf_parser.py        # Reusable PDF extractor (using pypdf)
│
└── normalizers/             # Standardizing to Unified Signal Schema
    ├── whatsapp_normalizer.py
    ├── sms_normalizer.py
    └── financial_normalizer.py
```

---

## 2. Component Dependency Relationships

```mermaid
graph TD
    Orchestrator[orchestrator.py]
    Agent[agent.py]
    
    Orchestrator --> WA_Coll[whatsapp_collector.py]
    Orchestrator --> SMS_Coll[sms_collector.py]
    Orchestrator --> GPay_Coll[gpay_collector.py]
    Orchestrator --> Bank_Coll[bank_statement_collector.py]
    
    WA_Coll --> WA_Pars[whatsapp_parser.py]
    WA_Coll --> WA_Norm[whatsapp_normalizer.py]
    WA_Coll --> Agent
    
    SMS_Coll --> SMS_Pars[sms_parser.py]
    SMS_Coll --> SMS_Norm[sms_normalizer.py]
    SMS_Coll --> Agent
    
    GPay_Coll --> PDF_Pars[pdf_parser.py]
    GPay_Coll --> Fin_Norm[financial_normalizer.py]
    GPay_Coll --> Agent
    
    Bank_Coll --> PDF_Pars[pdf_parser.py]
    Bank_Coll --> Fin_Norm[financial_normalizer.py]
    Bank_Coll --> Agent
```

* **Orchestrator (`orchestrator.py`):** Acts as the entrypoint pipeline. Instantiates the client and triggers all collectors.
* **Collectors (`collectors/`):** Own subdirectory discovery, downloading, parser/normalizer delegation, database insertion, archiving, and error catching.
* **Parsers (`parsers/`):** Read raw files (JSON formats or PDF bytes via `pdf_parser.py`) and perform DTD/schema validation.
* **Normalizers (`normalizers/`):** Translate the parsed structures into the Unified Signal Schema dictionary representation.
* **Agent (`agent.py`):** Provides the direct Supabase API interface for inserts, updates, file moves, and logging.
