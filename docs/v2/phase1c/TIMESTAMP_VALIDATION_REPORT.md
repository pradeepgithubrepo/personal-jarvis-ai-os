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
  - Time: `2026-04-02T08:39:00+00:00` | Sender: `pprad` | Message: `Paid to Radha Radha`
  - Time: `2026-04-03T16:15:00+00:00` | Sender: `pprad` | Message: `Paid to JISHA JOHN C`
- **Validation Result:** **PASS**

### Source: whatsapp
- **Total Records:** 364
- **Oldest source_event_time:** `2026-06-22T16:23:59.500000+00:00`
- **Newest source_event_time:** `2026-07-09T11:24:42.102000+00:00`
- **Sample Records:**
  - Time: `2026-06-25T12:05:13.591+00:00` | Sender: `Shraddha Jaiswal` | Message: `Let me see Pradeep ,pre prod week is going on I’ll update in`
  - Time: `2026-06-25T16:38:34.815+00:00` | Sender: `WhatsApp: Senthil RFC` | Message: `Yeah looks so`
- **Validation Result:** **PASS**

### Source: sms
- **Total Records:** 1008
- **Oldest source_event_time:** `2026-03-26T04:34:14.244000+00:00`
- **Newest source_event_time:** `2026-07-09T11:28:04.032000+00:00`
- **Sample Records:**
  - Time: `2026-06-25T13:44:11.896+00:00` | Sender: `VM-SBICRD-T` | Message: `348959 is the OTP for Trxn. of INR 244.00 at FLIPKART I with`
  - Time: `2026-06-26T02:38:17.494+00:00` | Sender: `JD-HDFCBK-S` | Message: `Pay Now!
SBI Card Bill 8707 of Rs.3141.02 is due on 01-Jul-2`
- **Validation Result:** **PASS**

### Source: bank_statement
- **Total Records:** 49
- **Oldest source_event_time:** `2026-04-04T00:00:00+00:00`
- **Newest source_event_time:** `2026-06-30T00:00:00+00:00`
- **Sample Records:**
  - Time: `2026-04-04T00:00:00+00:00` | Sender: `pprad` | Message: `WDL TFR IY209420261713387162172 0036515075873 OF SBI CARDS A`
  - Time: `2026-04-09T00:00:00+00:00` | Sender: `pprad` | Message: `WDL TFR IMPS/609916501529/HDFC- xx221-Pradeep/Transfer 00982`
- **Validation Result:** **PASS**

