# PIPELINE BACKFILL EXECUTION REPORT — QUALIFICATION LAYER V2

Executed At: 2026-07-11T11:32:32.933728+00:00
Status: **SUCCESS (QUALIFICATION STAGE INGESTED & FROZEN)**

## 1. Table Row Counts

| Table | Rows Before | Rows After |
|---|---|---|
| `mobile_signals` | 1700 | 1700 |
| `qualified_signals` | 1700 | 1700 |
| `understood_signals` | 0 | 0 | *(Frozen)*
| `signal_routes` | 0 | 0 | *(Frozen)*

## 2. Qualification Status Breakdown

- **QUALIFIED count**: 841
- **REVIEW count**: 297
- **REJECTED count**: 562

## 3. Post-Rebuild Validation Metrics (Audits)

| Validation Check | Failures | Status |
|---|---|---|
| Metadata Preservation Check | 0 | ✅ PASS |
| Device ID Preservation Check | 0 | ✅ PASS |
| Message Hash Preservation Check | 0 | ✅ PASS |
| Financial Metadata Check | 0 | ✅ PASS |
| Lineage Preservation Check | 0 | ✅ PASS |

## 4. Sample Qualified Records (10 Samples)

### Sample 1
- **ID**: `a1750ae5-d060-49e8-96d2-13ec05c13acb`
- **Signal ID (FK)**: `8324`
- **Source**: `gpay`
- **Sender**: `pprad`
- **Message**: `Paid to Radha Radha`
- **Device ID**: `pradeep`
- **Message Hash**: `6f1de9d316d846cbe4d194ea2f01c1d4186d14f7dd6db671e532b70e5407ae79`
- **Promoted Fields**:
  - **Amount**: 1536.0
  - **Currency**: INR
  - **Transaction Type**: DEBIT
- **Metadata Canonical Payload**:
```json
{
  "source_metadata": {
    "amount": 1536.0,
    "sender": "pprad",
    "currency": "INR",
    "receiver": "Radha Radha",
    "signal_id": "e9757722-a26c-4777-8d8c-df5e5f85e188",
    "description": "Paid to Radha Radha",
    "counterparty": "Radha Radha",
    "source_subtype": "gpay",
    "reference_number": "120940047278",
    "source_file_hash": "d28c9e1f03679cde2396abf50149fa3cec6a60e0022bfeebf19431569e22039d",
    "source_file_name": "gpay_statement_20260401_20260630.pdf",
    "transaction_date": "2026-04-02T08:39:00+00:00",
    "transaction_type": "DEBIT",
    "source_ingested_at": "2026-07-09T16:44:42.691417+00:00"
  },
  "canonical_version": 1,
  "qualification_info": {
    "score": 100.0,
    "reason": "gpay_structured_metadata",
    "status": "QUALIFIED",
    "evaluated_at": "2026-07-11T11:31:36.282908+00:00"
  }
}
```

### Sample 2
- **ID**: `5a7ccd0b-0c86-4c9d-927e-1e286a3761aa`
- **Signal ID (FK)**: `8325`
- **Source**: `gpay`
- **Sender**: `pprad`
- **Message**: `Paid to JISHA JOHN C`
- **Device ID**: `pradeep`
- **Message Hash**: `0e650dbaada1a97c0bdeaefdf35626d5ebb2ed4992049cc3b9147b50782a7c7c`
- **Promoted Fields**:
  - **Amount**: 55.0
  - **Currency**: INR
  - **Transaction Type**: DEBIT
- **Metadata Canonical Payload**:
```json
{
  "source_metadata": {
    "amount": 55.0,
    "sender": "pprad",
    "currency": "INR",
    "receiver": "JISHA JOHN C",
    "signal_id": "d444e57b-4594-4419-980e-bf44670e0ee5",
    "description": "Paid to JISHA JOHN C",
    "counterparty": "JISHA JOHN C",
    "source_subtype": "gpay",
    "reference_number": "645932563498",
    "source_file_hash": "d28c9e1f03679cde2396abf50149fa3cec6a60e0022bfeebf19431569e22039d",
    "source_file_name": "gpay_statement_20260401_20260630.pdf",
    "transaction_date": "2026-04-03T16:15:00+00:00",
    "transaction_type": "DEBIT",
    "source_ingested_at": "2026-07-09T16:44:42.691445+00:00"
  },
  "canonical_version": 1,
  "qualification_info": {
    "score": 100.0,
    "reason": "gpay_structured_metadata",
    "status": "QUALIFIED",
    "evaluated_at": "2026-07-11T11:31:36.282986+00:00"
  }
}
```

### Sample 3
- **ID**: `6d6c2a79-2e9e-439f-884f-7d79e760f181`
- **Signal ID (FK)**: `8326`
- **Source**: `gpay`
- **Sender**: `pprad`
- **Message**: `Paid to Anbu Fruits Shop`
- **Device ID**: `pradeep`
- **Message Hash**: `62ee591b23ec2d32a2141922720df7f79841fcf0ef04fe6208be5dd507aed7f7`
- **Promoted Fields**:
  - **Amount**: 50.0
  - **Currency**: INR
  - **Transaction Type**: DEBIT
- **Metadata Canonical Payload**:
```json
{
  "source_metadata": {
    "amount": 50.0,
    "sender": "pprad",
    "currency": "INR",
    "receiver": "Anbu Fruits Shop",
    "signal_id": "d7a8e4b3-b992-4aae-a43a-898772af0c50",
    "description": "Paid to Anbu Fruits Shop",
    "counterparty": "Anbu Fruits Shop",
    "source_subtype": "gpay",
    "reference_number": "645910181099",
    "source_file_hash": "d28c9e1f03679cde2396abf50149fa3cec6a60e0022bfeebf19431569e22039d",
    "source_file_name": "gpay_statement_20260401_20260630.pdf",
    "transaction_date": "2026-04-03T19:16:00+00:00",
    "transaction_type": "DEBIT",
    "source_ingested_at": "2026-07-09T16:44:42.691460+00:00"
  },
  "canonical_version": 1,
  "qualification_info": {
    "score": 100.0,
    "reason": "gpay_structured_metadata",
    "status": "QUALIFIED",
    "evaluated_at": "2026-07-11T11:31:36.283013+00:00"
  }
}
```

### Sample 4
- **ID**: `d9661407-2139-4920-b4ad-e407c22d2f0b`
- **Signal ID (FK)**: `8327`
- **Source**: `gpay`
- **Sender**: `pprad`
- **Message**: `Paid to Mr HAJNOOL AKBAR S`
- **Device ID**: `pradeep`
- **Message Hash**: `9c5b22e6967fc2e1eafc880d11ab0c047a7d9853a913133d9412103150bd65b4`
- **Promoted Fields**:
  - **Amount**: 550.0
  - **Currency**: INR
  - **Transaction Type**: DEBIT
- **Metadata Canonical Payload**:
```json
{
  "source_metadata": {
    "amount": 550.0,
    "sender": "pprad",
    "currency": "INR",
    "receiver": "Mr HAJNOOL AKBAR S",
    "signal_id": "5ad272f3-eee2-4e0e-97d0-fa7e7b432743",
    "description": "Paid to Mr HAJNOOL AKBAR S",
    "counterparty": "Mr HAJNOOL AKBAR S",
    "source_subtype": "gpay",
    "reference_number": "609499708547",
    "source_file_hash": "d28c9e1f03679cde2396abf50149fa3cec6a60e0022bfeebf19431569e22039d",
    "source_file_name": "gpay_statement_20260401_20260630.pdf",
    "transaction_date": "2026-04-04T06:52:00+00:00",
    "transaction_type": "DEBIT",
    "source_ingested_at": "2026-07-09T16:44:42.691472+00:00"
  },
  "canonical_version": 1,
  "qualification_info": {
    "score": 100.0,
    "reason": "gpay_structured_metadata",
    "status": "QUALIFIED",
    "evaluated_at": "2026-07-11T11:31:36.283032+00:00"
  }
}
```

### Sample 5
- **ID**: `83e1ca10-9065-45c8-b32b-bad1387e53da`
- **Signal ID (FK)**: `8328`
- **Source**: `gpay`
- **Sender**: `pprad`
- **Message**: `Paid to IRCTC Web UPI`
- **Device ID**: `pradeep`
- **Message Hash**: `ec8c3c4a2aa2e41a0a8839f9247d3a76cfae895371b2d146042971d94685eb62`
- **Promoted Fields**:
  - **Amount**: 1314.05
  - **Currency**: INR
  - **Transaction Type**: DEBIT
- **Metadata Canonical Payload**:
```json
{
  "source_metadata": {
    "amount": 1314.05,
    "sender": "pprad",
    "currency": "INR",
    "receiver": "IRCTC Web UPI",
    "signal_id": "453ed4c1-4fb6-4b0f-b752-00ccbcdc70c9",
    "description": "Paid to IRCTC Web UPI",
    "counterparty": "IRCTC Web UPI",
    "source_subtype": "gpay",
    "reference_number": "121047244105",
    "source_file_hash": "d28c9e1f03679cde2396abf50149fa3cec6a60e0022bfeebf19431569e22039d",
    "source_file_name": "gpay_statement_20260401_20260630.pdf",
    "transaction_date": "2026-04-04T10:02:00+00:00",
    "transaction_type": "DEBIT",
    "source_ingested_at": "2026-07-09T16:44:42.691482+00:00"
  },
  "canonical_version": 1,
  "qualification_info": {
    "score": 100.0,
    "reason": "gpay_structured_metadata",
    "status": "QUALIFIED",
    "evaluated_at": "2026-07-11T11:31:36.283045+00:00"
  }
}
```

### Sample 6
- **ID**: `75eb89ef-902f-4328-b323-57a83787ebcb`
- **Signal ID (FK)**: `8329`
- **Source**: `gpay`
- **Sender**: `Nagarajan A`
- **Message**: `Received from Nagarajan A`
- **Device ID**: `pradeep`
- **Message Hash**: `5f9735f13a313f7f17125b96c108e9f40bc0b5aa60c711239e002d0009825358`
- **Promoted Fields**:
  - **Amount**: 1314.0
  - **Currency**: INR
  - **Transaction Type**: CREDIT
- **Metadata Canonical Payload**:
```json
{
  "source_metadata": {
    "amount": 1314.0,
    "sender": "Nagarajan A",
    "currency": "INR",
    "receiver": "pprad",
    "signal_id": "b8c912dc-306a-48f5-b05c-b6845094ae32",
    "description": "Received from Nagarajan A",
    "counterparty": "Nagarajan A",
    "source_subtype": "gpay",
    "reference_number": "609454912968",
    "source_file_hash": "d28c9e1f03679cde2396abf50149fa3cec6a60e0022bfeebf19431569e22039d",
    "source_file_name": "gpay_statement_20260401_20260630.pdf",
    "transaction_date": "2026-04-04T10:10:00+00:00",
    "transaction_type": "CREDIT",
    "source_ingested_at": "2026-07-09T16:44:42.691495+00:00"
  },
  "canonical_version": 1,
  "qualification_info": {
    "score": 100.0,
    "reason": "gpay_structured_metadata",
    "status": "QUALIFIED",
    "evaluated_at": "2026-07-11T11:31:36.283060+00:00"
  }
}
```

### Sample 7
- **ID**: `a12dc2a0-7f21-4032-bd98-b19a2a96e78a`
- **Signal ID (FK)**: `8330`
- **Source**: `gpay`
- **Sender**: `pprad`
- **Message**: `Paid to Sumithra K`
- **Device ID**: `pradeep`
- **Message Hash**: `f3872bcfc5def98185b4432686492fa017c8bf93e9fb46de1ead945d713497ed`
- **Promoted Fields**:
  - **Amount**: 147.0
  - **Currency**: INR
  - **Transaction Type**: DEBIT
- **Metadata Canonical Payload**:
```json
{
  "source_metadata": {
    "amount": 147.0,
    "sender": "pprad",
    "currency": "INR",
    "receiver": "Sumithra K",
    "signal_id": "b82c55d1-c84c-4dd8-92d1-96df4e064d82",
    "description": "Paid to Sumithra K",
    "counterparty": "Sumithra K",
    "source_subtype": "gpay",
    "reference_number": "609467718814",
    "source_file_hash": "d28c9e1f03679cde2396abf50149fa3cec6a60e0022bfeebf19431569e22039d",
    "source_file_name": "gpay_statement_20260401_20260630.pdf",
    "transaction_date": "2026-04-04T10:36:00+00:00",
    "transaction_type": "DEBIT",
    "source_ingested_at": "2026-07-09T16:44:42.691504+00:00"
  },
  "canonical_version": 1,
  "qualification_info": {
    "score": 100.0,
    "reason": "gpay_structured_metadata",
    "status": "QUALIFIED",
    "evaluated_at": "2026-07-11T11:31:36.283083+00:00"
  }
}
```

### Sample 8
- **ID**: `f5ab096b-3090-499d-ab04-d8588f00ac1c`
- **Signal ID (FK)**: `8331`
- **Source**: `gpay`
- **Sender**: `pprad`
- **Message**: `Paid to PAMMAL SARAVANA SHOPPING`
- **Device ID**: `pradeep`
- **Message Hash**: `bf4f35d574ef1550303d3309ff021c2afa989a0f451acd20b939e1b81f340712`
- **Promoted Fields**:
  - **Amount**: 45.0
  - **Currency**: INR
  - **Transaction Type**: DEBIT
- **Metadata Canonical Payload**:
```json
{
  "source_metadata": {
    "amount": 45.0,
    "sender": "pprad",
    "currency": "INR",
    "receiver": "PAMMAL SARAVANA SHOPPING",
    "signal_id": "f319f530-cc14-4d0c-9479-67d8cc2b64cd",
    "description": "Paid to PAMMAL SARAVANA SHOPPING",
    "counterparty": "PAMMAL SARAVANA SHOPPING",
    "source_subtype": "gpay",
    "reference_number": "609447651847",
    "source_file_hash": "d28c9e1f03679cde2396abf50149fa3cec6a60e0022bfeebf19431569e22039d",
    "source_file_name": "gpay_statement_20260401_20260630.pdf",
    "transaction_date": "2026-04-04T18:08:00+00:00",
    "transaction_type": "DEBIT",
    "source_ingested_at": "2026-07-09T16:44:42.691512+00:00"
  },
  "canonical_version": 1,
  "qualification_info": {
    "score": 100.0,
    "reason": "gpay_structured_metadata",
    "status": "QUALIFIED",
    "evaluated_at": "2026-07-11T11:31:36.283095+00:00"
  }
}
```

### Sample 9
- **ID**: `49e36570-0e93-4f42-82d2-d38ec428db37`
- **Signal ID (FK)**: `8332`
- **Source**: `gpay`
- **Sender**: `pprad`
- **Message**: `Paid to Mrs V Deepa`
- **Device ID**: `pradeep`
- **Message Hash**: `5e95fe2a128b9fa853e431129ae9f0e5fae1633e53bc18c24938699bad5d328f`
- **Promoted Fields**:
  - **Amount**: 160.0
  - **Currency**: INR
  - **Transaction Type**: DEBIT
- **Metadata Canonical Payload**:
```json
{
  "source_metadata": {
    "amount": 160.0,
    "sender": "pprad",
    "currency": "INR",
    "receiver": "Mrs V Deepa",
    "signal_id": "c7ea09e1-4563-498f-83d2-36f02234670b",
    "description": "Paid to Mrs V Deepa",
    "counterparty": "Mrs V Deepa",
    "source_subtype": "gpay",
    "reference_number": "609417259207",
    "source_file_hash": "d28c9e1f03679cde2396abf50149fa3cec6a60e0022bfeebf19431569e22039d",
    "source_file_name": "gpay_statement_20260401_20260630.pdf",
    "transaction_date": "2026-04-04T18:27:00+00:00",
    "transaction_type": "DEBIT",
    "source_ingested_at": "2026-07-09T16:44:42.691521+00:00"
  },
  "canonical_version": 1,
  "qualification_info": {
    "score": 100.0,
    "reason": "gpay_structured_metadata",
    "status": "QUALIFIED",
    "evaluated_at": "2026-07-11T11:31:36.283106+00:00"
  }
}
```

### Sample 10
- **ID**: `02cfe8b7-0bc6-4090-85a9-a2d402aa7bdd`
- **Signal ID (FK)**: `8333`
- **Source**: `gpay`
- **Sender**: `pprad`
- **Message**: `Paid to MOHAMMED RIYAS MOHAM`
- **Device ID**: `pradeep`
- **Message Hash**: `c2b2c1fed30328f04c181091e7dafeb034d1f092a70b871d1cb5aff923ff6823`
- **Promoted Fields**:
  - **Amount**: 500.0
  - **Currency**: INR
  - **Transaction Type**: DEBIT
- **Metadata Canonical Payload**:
```json
{
  "source_metadata": {
    "amount": 500.0,
    "sender": "pprad",
    "currency": "INR",
    "receiver": "MOHAMMED RIYAS MOHAM",
    "signal_id": "53713aa5-aa43-4fa3-9fa1-27596bec12a8",
    "description": "Paid to MOHAMMED RIYAS MOHAM",
    "counterparty": "MOHAMMED RIYAS MOHAM",
    "source_subtype": "gpay",
    "reference_number": "609579196038",
    "source_file_hash": "d28c9e1f03679cde2396abf50149fa3cec6a60e0022bfeebf19431569e22039d",
    "source_file_name": "gpay_statement_20260401_20260630.pdf",
    "transaction_date": "2026-04-05T08:00:00+00:00",
    "transaction_type": "DEBIT",
    "source_ingested_at": "2026-07-09T16:44:42.691529+00:00"
  },
  "canonical_version": 1,
  "qualification_info": {
    "score": 100.0,
    "reason": "gpay_structured_metadata",
    "status": "QUALIFIED",
    "evaluated_at": "2026-07-11T11:31:36.283117+00:00"
  }
}
```

