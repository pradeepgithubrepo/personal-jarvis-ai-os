# Phase 1C Timestamp Validation Report

* **Overall Status:** **PASS**
* **Total Records Analyzed:** 1698
* **Ingestion Match Count:** 0 (Match rate: 0.00%)

## Source Ranges

### Source: gpay
- **Total Records:** 277
- **Oldest source_event_time:** `2026-04-02T08:39:00+00:00`
- **Newest source_event_time:** `2026-06-30T18:45:00+00:00`
- **Sample Records:**
  - Time: `2026-04-02T08:39:00+00:00` | Sender: `user_alias` | Message: `Paid to Sample Payee A`
  - Time: `2026-04-03T16:15:00+00:00` | Sender: `user_alias` | Message: `Paid to Sample Payee B`
- **Validation Result:** **PASS**

### Source: whatsapp
- **Total Records:** 364
- **Oldest source_event_time:** `2026-06-22T16:23:59.500000+00:00`
- **Newest source_event_time:** `2026-07-09T11:24:42.102000+00:00`
- **Sample Records:**
  - Time: `2026-06-25T12:05:13.591+00:00` | Sender: `Sample Contact` | Message: `Let me see User ,pre prod week is going on I’ll update in`
  - Time: `2026-06-25T16:38:34.815+00:00` | Sender: `WhatsApp: Sample Group` | Message: `Yeah looks so`
- **Validation Result:** **PASS**

### Source: sms
- **Total Records:** 1008
- **Oldest source_event_time:** `2026-03-26T04:34:14.244000+00:00`
- **Newest source_event_time:** `2026-07-09T11:28:04.032000+00:00`
- **Sample Records:**
  - Time: `2026-06-25T13:44:11.896+00:00` | Sender: `VM-BANK-T` | Message: `000000 is the OTP for Trxn. of INR 100.00 at SAMPLE STORE`
  - Time: `2026-06-26T02:38:17.494+00:00` | Sender: `JD-BANK-S` | Message: `Pay Now! Card Bill 0000 of Rs.1000.00 is due on 01-Jul-26`
- **Validation Result:** **PASS**

### Source: bank_statement
- **Total Records:** 49
- **Oldest source_event_time:** `2026-04-04T00:00:00+00:00`
- **Newest source_event_time:** `2026-06-30T00:00:00+00:00`
- **Sample Records:**
  - Time: `2026-04-04T00:00:00+00:00` | Sender: `user_alias` | Message: `WDL TFR IY000000000000000000000 0000000000000 OF CARD PAYMENT`
  - Time: `2026-04-09T00:00:00+00:00` | Sender: `user_alias` | Message: `WDL TFR IMPS/000000000000/BANK- xx000-User/Transfer 00000`
- **Validation Result:** **PASS**

