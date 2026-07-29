# PIPELINE BACKFILL EXECUTION REPORT — JARVIS V2 (UNDERSTANDING BOUNDARY)

Executed At: 2026-07-15T16:44:19.093259+00:00
Status: **SUCCESS (QUALIFICATION, UNDERSTANDING & ROUTING INGESTED)**

## 1. Table Row Counts

| Table | Rows Before | Rows After |
|---|---|---|
| `mobile_signals` | 2081 | 2081 |
| `qualified_signals` | 2080 | 2081 |
| `understood_signals` | 0 | 1037 |
| `signal_routes` | 0 | 1034 |

## 2. Understood Signal Type Breakdown

- **FINANCIAL count**: 839
- **ACTION count**: 46
- **FYI count**: 103
- **FACT count**: 0
- **NOISE count**: 49

## 3. Post-Rebuild Validation Metrics (Audits)

### 3.1 Qualification Layer Audits

| Validation Check | Failures | Status |
|---|---|---|
| Metadata Preservation Check | 0 | ✅ PASS |
| Device ID Preservation Check | 0 | ✅ PASS |
| Message Hash Preservation Check | 0 | ✅ PASS |
| Financial Metadata Check | 0 | ✅ PASS |
| Lineage Preservation Check | 0 | ✅ PASS |

### 3.2 Understanding Layer Audits

| Validation Check | Failures | Status |
|---|---|---|
| Metadata Preservation Check | 0 | ✅ PASS |
| Device ID Preservation Check | 0 | ✅ PASS |
| Message Hash Preservation Check | 0 | ✅ PASS |
| Lineage Preservation Check | 0 | ✅ PASS |

### 3.3 Routing Layer Audits

| Validation Check | Failures | Status |
|---|---|---|
| Lineage Check (FK constraints) | 0 | ✅ PASS |
| Route Reason Check (Non-empty reason) | 0 | ✅ PASS |
| Route Confidence Check (Match Signal) | 0 | ✅ PASS |

## 4. Sample Understood Records (10 Samples)

### Sample 1
- **ID**: `47fedc04-9082-4a94-99dc-a8057a8d909a`
- **Qualified ID (FK)**: `ee6b9ad0-215b-44ae-81be-e3b70110e7ff`
- **Source Raw ID**: `15346`
- **Signal Type**: `FYI`
- **Confidence**: 0.9
- **Processing Path**: `CEREBRAS_DIRECT`
- **Device ID**: `user_phone`
- **Message Hash**: `d08263eef5b2449f2da73227ea0191214f8e17f135f0517162a98cb0840e7b50`
- **Summary**: *Incoming call notification from Aappa.*
- **Contract Schema JSON (`contract_json`)**:
```json
{
  "entities": [
    "Ringing"
  ],
  "event_name": "Incoming call",
  "event_time": "2026-07-11T13:58:25.11+00:00",
  "description": "Ringing notification from Aappa on WhatsApp.",
  "fyi_candidate": true,
  "fact_candidate": false,
  "noise_candidate": false,
  "requires_action": false,
  "memory_candidate": true,
  "financial_candidate": false
}
```
- **Canonical Metadata Payload**:
```json
{
  "llm_model_used": "gemma-4-31b",
  "processing_path": "CEREBRAS_DIRECT",
  "source_metadata": {
    "sender": "Aappa",
    "receiver": "user_phone",
    "signal_id": null,
    "source_subtype": "",
    "source_file_hash": null,
    "source_file_name": "user_1783783504741.json",
    "source_ingested_at": null
  },
  "canonical_version": 1,
  "escalation_reason": "",
  "qualification_info": {
    "score": 95.0,
    "reason": "trusted_sender_qualification",
    "status": "QUALIFIED",
    "evaluated_at": "2026-07-14T15:43:28.231644+00:00"
  },
  "processing_duration_ms": 1825
}
```

### Sample 2
- **ID**: `d537a5d0-6243-46ef-a412-40b54f874c19`
- **Qualified ID (FK)**: `cf11c401-9366-4d45-a00e-8ddf276d21cd`
- **Source Raw ID**: `15348`
- **Signal Type**: `FINANCIAL`
- **Confidence**: 0.99
- **Processing Path**: `CEREBRAS_DIRECT`
- **Device ID**: `user_phone`
- **Message Hash**: `f68d20090eefb2df755f6363d886b51739e74166c87d34a69ee950bc6bc05534`
- **Summary**: *Debit transaction of Rs.2351.00 from HDFC Bank A/C *3221 to TANGEDCO.*
- **Contract Schema JSON (`contract_json`)**:
```json
{
  "amount": 2351.0,
  "currency": "INR",
  "entities": [
    "Sent",
    "Not",
    "BLOCK",
    "You",
    "HDFC",
    "Call",
    "SMS",
    "From",
    "Ref",
    "UPI",
    "TANGEDCO",
    "To",
    "On"
  ],
  "merchant": "TANGEDCO",
  "fyi_candidate": false,
  "fact_candidate": false,
  "noise_candidate": false,
  "payment_channel": "UNKNOWN",
  "requires_action": false,
  "memory_candidate": false,
  "transaction_type": "DEBIT",
  "financial_candidate": true
}
```
- **Canonical Metadata Payload**:
```json
{
  "llm_model_used": "gemma-4-31b",
  "processing_path": "CEREBRAS_DIRECT",
  "source_metadata": {
    "sender": "JD-HDFCBK-T",
    "receiver": "user_phone",
    "signal_id": null,
    "source_subtype": "",
    "source_file_hash": null,
    "source_file_name": "user_1783783504741.json",
    "source_ingested_at": null
  },
  "canonical_version": 1,
  "escalation_reason": "",
  "qualification_info": {
    "score": 95.0,
    "reason": "financial_signal_detected",
    "status": "QUALIFIED",
    "evaluated_at": "2026-07-14T15:43:28.231723+00:00"
  },
  "processing_duration_ms": 1583
}
```

### Sample 3
- **ID**: `35a97292-5778-4289-83f6-625e29e6ac16`
- **Qualified ID (FK)**: `2918045a-c798-4b5c-9c95-0d8874952759`
- **Source Raw ID**: `15352`
- **Signal Type**: `ACTION`
- **Confidence**: 1
- **Processing Path**: `CEREBRAS_DIRECT`
- **Device ID**: `user_phone`
- **Message Hash**: `499644b4d3ee6d3c0077f02c8e1213af27b22ab6ee2919514513674b73bcbf7d`
- **Summary**: *Electricity bill of Rs.2351 is due on 30/07/2026.*
- **Contract Schema JSON (`contract_json`)**:
```json
{
  "assignee": "user",
  "due_date": "2026-07-30",
  "entities": [
    "Pay",
    "SC",
    "TANGEDCO",
    "Electricity",
    "No"
  ],
  "task_name": "Pay electricity bill",
  "fyi_candidate": false,
  "fact_candidate": false,
  "noise_candidate": false,
  "requires_action": true,
  "memory_candidate": true,
  "financial_candidate": false
}
```
- **Canonical Metadata Payload**:
```json
{
  "llm_model_used": "gemma-4-31b",
  "processing_path": "CEREBRAS_DIRECT",
  "source_metadata": {
    "sender": "AD-TANGED-S",
    "receiver": "user_phone",
    "signal_id": null,
    "source_subtype": "",
    "source_file_hash": null,
    "source_file_name": "user_1783783504741.json",
    "source_ingested_at": null
  },
  "canonical_version": 1,
  "escalation_reason": "",
  "qualification_info": {
    "score": 95.0,
    "reason": "financial_signal_detected",
    "status": "QUALIFIED",
    "evaluated_at": "2026-07-14T15:43:28.232192+00:00"
  },
  "processing_duration_ms": 1819
}
```

### Sample 4
- **ID**: `0a58ce6a-4030-49cb-b05a-97bf151c7df2`
- **Qualified ID (FK)**: `14945a87-b914-4aaa-976b-6d70c615caed`
- **Source Raw ID**: `15355`
- **Signal Type**: `FYI`
- **Confidence**: 0.9
- **Processing Path**: `CEREBRAS_DIRECT`
- **Device ID**: `user_phone`
- **Message Hash**: `dd8168d003171c49599e22acfeda2e5b78879a6d0c4fbdd722ab0650e06312e2`
- **Summary**: *Maintenance charges for June 2026 have been shared for the flat.*
- **Contract Schema JSON (`contract_json`)**:
```json
{
  "entities": [
    "Hi",
    "Please",
    "Maintenance",
    "Jun26"
  ],
  "event_name": "Maintenance Charges Notification",
  "event_time": "2026-06",
  "description": "Maintenance charges for Jun26 shared via attachment",
  "fyi_candidate": true,
  "fact_candidate": false,
  "noise_candidate": false,
  "requires_action": false,
  "memory_candidate": true,
  "financial_candidate": false
}
```
- **Canonical Metadata Payload**:
```json
{
  "llm_model_used": "gemma-4-31b",
  "processing_path": "CEREBRAS_DIRECT",
  "source_metadata": {
    "sender": "[REDACTED_BUILDING_GROUP]: [REDACTED_NAME] T1",
    "receiver": "user_phone",
    "signal_id": null,
    "source_subtype": "",
    "source_file_hash": null,
    "source_file_name": "user_1783815911734.json",
    "source_ingested_at": null
  },
  "canonical_version": 1,
  "escalation_reason": "",
  "qualification_info": {
    "score": 95.0,
    "reason": "trusted_sender_qualification",
    "status": "QUALIFIED",
    "evaluated_at": "2026-07-14T15:43:28.232501+00:00"
  },
  "processing_duration_ms": 612
}
```

### Sample 5
- **ID**: `64ed2d77-2941-450f-9d9a-0bb7ef37f161`
- **Qualified ID (FK)**: `09e54c7b-29df-45fe-8536-79ca4f7e5574`
- **Source Raw ID**: `15364`
- **Signal Type**: `FYI`
- **Confidence**: 0.9
- **Processing Path**: `CEREBRAS_DIRECT`
- **Device ID**: `user_phone`
- **Message Hash**: `72ef8c77a568f3e64f72c89d5fc82c6eda144449043c7afda6e2cf9d6b334f85`
- **Summary**: *Contact_1 notified that the shoes have arrived.*
- **Contract Schema JSON (`contract_json`)**:
```json
{
  "entities": [
    "Shoe"
  ],
  "event_name": "Delivery Arrival",
  "event_time": null,
  "description": "Shoe came ji",
  "fyi_candidate": true,
  "fact_candidate": false,
  "noise_candidate": false,
  "requires_action": false,
  "memory_candidate": true,
  "financial_candidate": false
}
```
- **Canonical Metadata Payload**:
```json
{
  "llm_model_used": "gemma-4-31b",
  "processing_path": "CEREBRAS_DIRECT",
  "source_metadata": {
    "sender": "Contact_1",
    "receiver": "user_phone",
    "signal_id": null,
    "source_subtype": "",
    "source_file_hash": null,
    "source_file_name": "user_1783845181697.json",
    "source_ingested_at": null
  },
  "canonical_version": 1,
  "escalation_reason": "",
  "qualification_info": {
    "score": 95.0,
    "reason": "trusted_sender_qualification",
    "status": "QUALIFIED",
    "evaluated_at": "2026-07-14T15:43:28.232654+00:00"
  },
  "processing_duration_ms": 981
}
```

### Sample 6
- **ID**: `4b460d74-a793-4f35-8994-325ed3f108dd`
- **Qualified ID (FK)**: `c430635b-02a7-453a-9174-3c7fbefb60b3`
- **Source Raw ID**: `15257`
- **Signal Type**: `FINANCIAL`
- **Confidence**: 1
- **Processing Path**: `metadata_bypass`
- **Device ID**: `user`
- **Message Hash**: `3c0f2af6adc11476aa95f0a9474b8912eea101e8e27f11993e3e9a39cd99ee1b`
- **Summary**: *Paid 1500.0 INR to UPI-LITE-50100534333221-615732889848-ADD MONEY.*
- **Contract Schema JSON (`contract_json`)**:
```json
{
  "amount": 1500.0,
  "currency": "INR",
  "entities": [
    "UPI",
    "LITE",
    "MONEY",
    "ADD"
  ],
  "merchant": "UPI-LITE-50100534333221-615732889848-ADD MONEY",
  "fyi_candidate": false,
  "fact_candidate": false,
  "noise_candidate": false,
  "payment_channel": "UPI",
  "requires_action": false,
  "memory_candidate": false,
  "transaction_type": "DEBIT",
  "financial_candidate": true
}
```
- **Canonical Metadata Payload**:
```json
{
  "llm_model_used": null,
  "processing_path": "metadata_bypass",
  "source_metadata": {
    "amount": 1500.0,
    "sender": "user_alias",
    "currency": "INR",
    "receiver": "UPI-LITE-50100534333221-615732889848-ADD MONEY",
    "signal_id": "8348b254-ffa6-4242-8cc5-49f4f0bb9e98",
    "description": "UPI-LITE-50100534333221-615732889848-ADD MONEY",
    "counterparty": "UPI-LITE-50100534333221-615732889848-ADD MONEY",
    "source_subtype": "bank_statement",
    "reference_number": "615732889848",
    "source_file_hash": "0f3d2fe7869d4ba3f9940d790d4b58e254b92e6fea7203dba34965c083bdb466",
    "source_file_name": "5010XXXXXX3221_e5444aa8_01Apr2026_TO_30Jun2026_084431939.pdf",
    "transaction_date": "2026-06-06T00:00:00+00:00",
    "transaction_type": "DEBIT",
    "source_ingested_at": "2026-07-13T14:34:04.191430+00:00"
  },
  "canonical_version": 1,
  "escalation_reason": "",
  "qualification_info": {
    "score": 100.0,
    "reason": "bank_statement_structured_metadata",
    "status": "QUALIFIED",
    "evaluated_at": "2026-07-14T15:43:28.227082+00:00"
  }
}
```

### Sample 7
- **ID**: `d284e364-6e49-4453-b17b-ff05673dfa08`
- **Qualified ID (FK)**: `1f6a2cd6-1097-459e-9e4b-e88e9ca0da83`
- **Source Raw ID**: `15347`
- **Signal Type**: `FYI`
- **Confidence**: 0.95
- **Processing Path**: `CEREBRAS_DIRECT`
- **Device ID**: `user_phone`
- **Message Hash**: `bb9788259e8e371e4f224e75fdcd99f78b949c83cb07eee35bc81f5a3fe983f4`
- **Summary**: *Notification about an ongoing video call from Aappa.*
- **Contract Schema JSON (`contract_json`)**:
```json
{
  "entities": [
    "Ongoing"
  ],
  "event_name": "Ongoing video call",
  "event_time": "2026-07-11T13:58:44.527+00:00",
  "description": "Notification from Aappa about an ongoing video call.",
  "fyi_candidate": true,
  "fact_candidate": false,
  "noise_candidate": false,
  "requires_action": false,
  "memory_candidate": true,
  "financial_candidate": false
}
```
- **Canonical Metadata Payload**:
```json
{
  "llm_model_used": "gemma-4-31b",
  "processing_path": "CEREBRAS_DIRECT",
  "source_metadata": {
    "sender": "Aappa",
    "receiver": "user_phone",
    "signal_id": null,
    "source_subtype": "",
    "source_file_hash": null,
    "source_file_name": "user_1783783504741.json",
    "source_ingested_at": null
  },
  "canonical_version": 1,
  "escalation_reason": "",
  "qualification_info": {
    "score": 95.0,
    "reason": "trusted_sender_qualification",
    "status": "QUALIFIED",
    "evaluated_at": "2026-07-14T15:43:28.231681+00:00"
  },
  "processing_duration_ms": 1579
}
```

### Sample 8
- **ID**: `39c3fe40-b34f-40bf-8110-e6caccf2c778`
- **Qualified ID (FK)**: `f33b51b9-f45c-41aa-bf28-3dffab22a98e`
- **Source Raw ID**: `15350`
- **Signal Type**: `FINANCIAL`
- **Confidence**: 0.99
- **Processing Path**: `CEREBRAS_DIRECT`
- **Device ID**: `user_phone`
- **Message Hash**: `fe400769b360209fda29b9f95d03b9629b16f4b9874d81b8bb5309e5c7d7a99e`
- **Summary**: *Received INR 1,500.00 in HDFC Bank account via IMPS transfer.*
- **Contract Schema JSON (`contract_json`)**:
```json
{
  "amount": 1500.0,
  "currency": "INR",
  "entities": [
    "INR",
    "HDFC",
    "Avl",
    "On",
    "IMPS",
    "Received",
    "USER"
  ],
  "merchant": "USER P",
  "fyi_candidate": false,
  "fact_candidate": false,
  "noise_candidate": false,
  "payment_channel": "UPI",
  "requires_action": false,
  "memory_candidate": false,
  "transaction_type": "CREDIT",
  "financial_candidate": true
}
```
- **Canonical Metadata Payload**:
```json
{
  "llm_model_used": "gemma-4-31b",
  "processing_path": "CEREBRAS_DIRECT",
  "source_metadata": {
    "sender": "JM-HDFCBK-S",
    "receiver": "user_phone",
    "signal_id": null,
    "source_subtype": "",
    "source_file_hash": null,
    "source_file_name": "user_1783783504741.json",
    "source_ingested_at": null
  },
  "canonical_version": 1,
  "escalation_reason": "",
  "qualification_info": {
    "score": 95.0,
    "reason": "financial_signal_detected",
    "status": "QUALIFIED",
    "evaluated_at": "2026-07-14T15:43:28.232088+00:00"
  },
  "processing_duration_ms": 1776
}
```

### Sample 9
- **ID**: `b49727d1-df49-482b-bb33-1a0507c74f50`
- **Qualified ID (FK)**: `175901ba-eb7e-4407-85f8-691fa528f203`
- **Source Raw ID**: `15354`
- **Signal Type**: `ACTION`
- **Confidence**: 0.9
- **Processing Path**: `CEREBRAS_DIRECT`
- **Device ID**: `user_phone`
- **Message Hash**: `f2a4e13641c024bc1e851393bc2581ba6a3e9f8b1c06afc3fa1e14481cd553c3`
- **Summary**: *Axis Bank credit card statement generated with a zero contact_7nce due on 30-07-26.*
- **Contract Schema JSON (`contract_json`)**:
```json
{
  "assignee": "parent",
  "due_date": null,
  "entities": [
    "Axis",
    "Pay",
    "INR",
    "Credit",
    "AXISBK",
    "Card",
    "Total",
    "To",
    "XX6540",
    "Min",
    "Due"
  ],
  "task_name": "Axis Bank credit card statement generated with a zero contact_7nce due on 30-07-26.",
  "event_name": "Credit Card Statement Generation",
  "event_time": "2026-07-30",
  "description": "Statement generated for card XX6540 with 0.00 amount due.",
  "fyi_candidate": false,
  "fact_candidate": false,
  "noise_candidate": false,
  "requires_action": true,
  "memory_candidate": true,
  "financial_candidate": false
}
```
- **Canonical Metadata Payload**:
```json
{
  "llm_model_used": "gemma-4-31b",
  "processing_path": "CEREBRAS_DIRECT",
  "source_metadata": {
    "sender": "AD-AXISBK-S",
    "receiver": "user_phone",
    "signal_id": null,
    "source_subtype": "",
    "source_file_hash": null,
    "source_file_name": "user_1783815911734.json",
    "source_ingested_at": null
  },
  "canonical_version": 1,
  "escalation_reason": "",
  "qualification_info": {
    "score": 95.0,
    "reason": "financial_signal_detected",
    "status": "QUALIFIED",
    "evaluated_at": "2026-07-14T15:43:28.232377+00:00"
  },
  "processing_duration_ms": 2536
}
```

### Sample 10
- **ID**: `e6c6b298-4f9f-41eb-a72b-ff631920bcfb`
- **Qualified ID (FK)**: `6239f5c6-7497-4c71-ac15-f5735f5345bf`
- **Source Raw ID**: `15362`
- **Signal Type**: `FYI`
- **Confidence**: 0.9
- **Processing Path**: `CEREBRAS_DIRECT`
- **Device ID**: `user_phone`
- **Message Hash**: `29665422fe032d6b398db6320f31edf8daf6779b8de4881db17636157730e4ee`
- **Summary**: *Contact_1 sent a photo via WhatsApp.*
- **Contract Schema JSON (`contract_json`)**:
```json
{
  "entities": [
    "Photo"
  ],
  "event_name": "Photo attachment",
  "event_time": "2026-07-12T02:07:57.656+00:00",
  "description": "Photo sent by Contact_1 via WhatsApp.",
  "fyi_candidate": true,
  "fact_candidate": false,
  "noise_candidate": false,
  "requires_action": false,
  "memory_candidate": true,
  "financial_candidate": false
}
```
- **Canonical Metadata Payload**:
```json
{
  "llm_model_used": "gemma-4-31b",
  "processing_path": "CEREBRAS_DIRECT",
  "source_metadata": {
    "sender": "Contact_1",
    "receiver": "user_phone",
    "signal_id": null,
    "source_subtype": "",
    "source_file_hash": null,
    "source_file_name": "user_1783845181697.json",
    "source_ingested_at": null
  },
  "canonical_version": 1,
  "escalation_reason": "",
  "qualification_info": {
    "score": 95.0,
    "reason": "trusted_sender_qualification",
    "status": "QUALIFIED",
    "evaluated_at": "2026-07-14T15:43:28.232609+00:00"
  },
  "processing_duration_ms": 1743
}
```

