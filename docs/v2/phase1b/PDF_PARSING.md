# Phase 1B PDF Parsing Strategy — GPay & Bank Statements

This document details the text extraction methods, transaction alignment rules, and regular expressions implemented in Jarvis V2.

---

## 1. Reusable PDF Reader Engine

We use `pypdf` as our PDF reader engine. The `parse_pdf(file_bytes)` function in [pdf_parser.py](file:///home/user/petprojects/ai/jarvis/src/agents/consumer/parsers/pdf_parser.py) extracts raw text from each page, yielding a structured `ParsedDocument` containing raw string text, page lists, and parsed tables.

---

## 2. Google Pay Statement Ingestion Rules

GPay PDF statements are parsed using line-level scanning on each extracted page. 
* **Transaction Pattern:**
  Transactions have a fixed sequence of 5 to 6 lines:
  1. **Date:** `^\d{2}\s+[A-Za-z]{3},\s+\d{4}$` (e.g. `02 Apr, 2026`)
  2. **Time:** `^\d{2}:\d{2}\s*[AP]M$` (e.g. `08:39AM`)
  3. **Details:** Starts with `Paid to`, `Received from`, or `Self transfer to`.
  4. **Transaction ID:** `UPITransactionID:(\d+)`
  5. **Payment Method:** Starts with `Paidby`, `Paidto`, or `Receivedby`.
  6. **Amount:** `₹([\d,]+(?:\.\d{2})?)` (e.g. `₹1,536`)

---

## 3. State Bank of India (SBI) Ingestion Rules

SBI statements are printed in tables where debits and credits align to separate columns, causing different line mappings:
* **Row Start Date:**
  A transaction starts with a line containing two dates (Post Date and Value Date):
  ```text
  ^(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})(.*)$
  ```
  (e.g., `04/04/2026 04/04/2026`)

* **Multi-Line Description:**
  Subsequent lines are captured as part of the description block until the amount/contact_7nce line is hit.

* **Amount & Contact_7nce Extraction:**
  - **Debit Pattern:**
    ```text
    ^-\s+([\d,]+\.\d{2})\s+--\s+([\d,]+\.\d{2})\s*(?:CR)?$
    ```
    Matches `- [debit_amt] - [contact_7nce]`.
  - **Credit Pattern:**
    ```text
    ^-\s+-\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s*(?:CR)?$
    ```
    Matches `- - [credit_amt] [contact_7nce]`.

---

## 4. HDFC Ingestion Rules

HDFC statements are structured similarly to SBI but formatted differently:
* **Row Pattern:**
  ```text
  ^(\d{2}/\d{2}/\d{2,4})\s+(.+?)\s+(\d{2}/\d{2}/\d{2,4})\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})
  ```
  Extracts Date, Narration, Value Date, Amount, and Contact_7nce.
  * Narration is scanned for keywords (`CR`, `CREDIT`, `DEP`, `RECEIVED`) to distinguish debits and credits.
