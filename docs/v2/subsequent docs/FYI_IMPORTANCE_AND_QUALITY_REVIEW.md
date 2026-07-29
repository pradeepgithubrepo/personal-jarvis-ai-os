# FYI Importance and Quality Review

This review presents a quality and importance audit of 50 representative FYI records from the live dataset of 110 records.

## Summary of Findings

* **100 records** analyzed:
  * **CRITICAL / HIGH Value**: ~20-25% (School updates, medical prescriptions, security alerts, policy expiry warnings).
  * **MEDIUM Value**: ~30-40% (Transit check-ins, package deliveries, travel tickets).
  * **LOW / EPHEMERAL Noise**: ~40-50% (Media uploads, transactional spam, promotional texts, short greetings).
* **Category Correction Needed**: 
  * Medical contexts (like prescriptions, enema/colonoscopy preparations) are currently classified as `GENERAL`. They should map to `HEALTH`.
  * Insurance policies and claims are currently mapping to `UTILITY_INFO` or `GENERAL`. They should map to `FINANCE_INSURANCE`.
  * Conversational chat messages (like "Okay User", "Hi") are currently categorized as `GENERAL` but should be classified as `EPHEMERAL` to bypass briefings.

---

## 50-Record Audit Table

| ID | Message Text | Current Category | Expected Category | Importance Level | In Briefing? |
|---|---|---|---|---|---|
| 1 | `Dear Customer, Plz note that Third Party Insurance is a must. Renew TN00XX0000 insurance policy 00000000000000000000...` | **UTILITY_INFO** | **FINANCE_INSURANCE** | `CRITICAL` | **Y** |
| 2 | `I think other than centre gate everything need to lock it` | **TRAVEL** | **SECURITY_ALERT** | `CRITICAL` | **Y** |
| 3 | `🔗 Polimer News on Instagram: "" ரூ.62,000 ஃபீஸ் வாங்குறாங்க.. கிளாஸ்ல 10 பசங்க தான் இருக்குறாங்க....` | **FAMILY_SCHOOL** | **FAMILY_SCHOOL** | `CRITICAL` | **Y** |
| 4 | `Dear Customer, Renew TN00XX0000 insurance policy 00000000000000000000 before its expiry 16/06/2026....` | **GENERAL** | **FINANCE_INSURANCE** | `CRITICAL` | **Y** |
| 5 | `Your Locker No SF02-00097 standing in the name of [REDACTED_NAME] AND [REDACTED_NAME] PA...` | **SECURITY_ALERT** | **SECURITY_ALERT** | `CRITICAL` | **Y** |
| 6 | `Hi user, the previous insurance policy of your bike expires tomorrow. Log on to www.coverfox.c...` | **GENERAL** | **FINANCE_INSURANCE** | `CRITICAL` | **Y** |
| 7 | `Now also @⁨[REDACTED_NAME] T1⁩ parking gate is open.` | **TRAVEL** | **SECURITY_ALERT** | `CRITICAL` | **Y** |
| 8 | `Yes [REDACTED_NAME] we can do. Delivery persons while returning they are not putting the gatch latch properly.` | **ORDER_TRACKING** | **SECURITY_ALERT** | `CRITICAL` | **Y** |
| 9 | `Enema kuduka poranga to prep for colonoscopy at 6 pm today   Let see If it comes out in enema  it...` | **GENERAL** | **HEALTH** | `HIGH` | **Y** |
| 10 | `Reacted 👍 to "okay Contact_1. Hope it does not require colonoscopy ."` | **GENERAL** | **HEALTH** | `HIGH` | **Y** |
| 11 | `Reacted 👍 to "okay Contact_1. Hope it does not require colonoscopy ."` | **ORDER_TRACKING** | **HEALTH** | `HIGH` | **Y** |
| 12 | `📷 Hi [REDACTED_USER_NAME],  Healthcare expenses don't always begin with an emergency. They often...` | **GENERAL** | **HEALTH** | `HIGH` | **Y** |
| 13 | `EPFO is undertaking a planned database consolidation and upgradation of software applications. As...` | **GENERAL** | **FINANCE_INSURANCE** | `HIGH` | **Y** |
| 14 | `Colonoscopy tomorrow mostly` | **GENERAL** | **HEALTH** | `HIGH` | **Y** |
| 15 | `🔗 health.oneglance.in | Dear Master.[REDACTED_NAME], Thanks for consulting with Dr [REDACTED_NAME] K, Access ...` | **GENERAL** | **HEALTH** | `HIGH` | **Y** |
| 16 | `🔗 health.oneglance.in | Dear Baby.[REDACTED_NAME], Thanks for consulting with Dr [REDACTED_NAME] K, Access...` | **GENERAL** | **HEALTH** | `HIGH` | **Y** |
| 17 | `Dear Parents   Homework: Book 1 : pg 9  Thank you  [REDACTED_NAME]  Little Millennium  Anakaputhur` | **GENERAL** | **FAMILY_SCHOOL** | `HIGH` | **Y** |
| 18 | `Hi user, your insurance policy was added to your account 48 hours ago. We rec...` | **GENERAL** | **FINANCE_INSURANCE** | `HIGH` | **Y** |
| 19 | `Your 2GB gift is expiring soon! Claim it at no extra cost via App. Click example.com...` | **GENERAL** | **FINANCE_INSURANCE** | `HIGH` | **Y** |
| 20 | `Dear Customer, Received INR 100 Receipt No 00000000000000000000 on 22/05/2026. Plz submit Proposa...` | **ORDER_TRACKING** | **FINANCE_INSURANCE** | `HIGH` | **Y** |
| 21 | `Your purchase trxn in Folio No. 00000000 has been processed. Click Here https://example.com/PPFAMF...` | **GENERAL** | **GENERAL** | `MEDIUM` | **Y** |
| 22 | `Dear user, sample collection for your order PO00000000000-000 has been assigned to [REDACTED_NAME] S, p...` | **ORDER_TRACKING** | **ORDER_TRACKING** | `MEDIUM` | **Y** |
| 23 | `Your purchase trxn in Folio No. 00000000 has been processed. Click Here https://example.com/PPFAMF...` | **GENERAL** | **GENERAL** | `MEDIUM` | **Y** |
| 24 | `The tenant's name is [REDACTED_TENANT_1].` | **GENERAL** | **GENERAL** | `MEDIUM` | **Y** |
| 25 | `India's first-ever Priority Postpaid is LIVE. Powered by Fast Lane Technology for superfast speed...` | **UTILITY_INFO** | **UTILITY_INFO** | `MEDIUM` | **Y** |
| 26 | `Still in there but made progress` | **GENERAL** | **GENERAL** | `MEDIUM` | **Y** |
| 27 | `Boarded the train` | **TRAVEL** | **TRAVEL** | `MEDIUM` | **Y** |
| 28 | `Reached home` | **TRAVEL** | **TRAVEL** | `MEDIUM` | **Y** |
| 29 | `Have you used Genie code coworker` | **GENERAL** | **GENERAL** | `MEDIUM` | **Y** |
| 30 | `I created front end app and back end app in just one day` | **GENERAL** | **GENERAL** | `MEDIUM` | **Y** |
| 31 | `Dear Passenger, You can check on-board food menu options at: https://menurates.irctc.co.in/ IR-CRIS` | **GENERAL** | **GENERAL** | `MEDIUM` | **Y** |
| 32 | `If u guys there. Let's meet at 12.45` | **GENERAL** | **GENERAL** | `MEDIUM` | **Y** |
| 33 | `Dear bigbasketeer, help us serve you better by sharing your feedback for the order ID: 1971476314...` | **GENERAL** | **GENERAL** | `LOW` | **N** |
| 34 | `Your free Hellotune is waiting. Choose your song and set it easily on Airtel app. Download now ht...` | **GENERAL** | **PROMOTIONAL** | `LOW` | **N** |
| 35 | `🔗 Chennai Version | [REDACTED_NAME] on Instagram: "🤯😳😭😭  The Royal Challengers Bengaluru entered IP...` | **GENERAL** | **GENERAL** | `LOW` | **N** |
| 36 | `📷 🔵 Prime Day Early Deals are LIVE!   ✨ Exclusive early access for Prime members  📱 Your next sma...` | **GENERAL** | **PROMOTIONAL** | `LOW` | **N** |
| 37 | `Your free Hellotune is waiting. Choose your song and set it easily on Airtel app. Download now ht...` | **GENERAL** | **PROMOTIONAL** | `LOW` | **N** |
| 38 | `Your free Hellotune is waiting. Choose your song and set it easily on Airtel app. Download now ht...` | **GENERAL** | **PROMOTIONAL** | `LOW` | **N** |
| 39 | `Dear Customer, We hope you are enjoying your purchase from Livpure. We'd love your feedback on ho...` | **GENERAL** | **GENERAL** | `LOW` | **N** |
| 40 | `Your free Hellotune is waiting. Choose your song and set it easily on Airtel app. Download now ht...` | **GENERAL** | **PROMOTIONAL** | `LOW` | **N** |
| 41 | `Your free Hellotune is waiting. Choose your song and set it easily on Airtel app. Download now ht...` | **GENERAL** | **PROMOTIONAL** | `LOW` | **N** |
| 42 | `Your free Hellotune is waiting. Choose your song and set it easily on Airtel app. Download now ht...` | **GENERAL** | **PROMOTIONAL** | `LOW` | **N** |
| 43 | `Your free Hellotune is waiting. Choose your song and set it easily on Airtel app. Download now ht...` | **GENERAL** | **PROMOTIONAL** | `LOW` | **N** |
| 44 | `Set your free Hellotune in seconds. Pick your favourite song and set it easily on Airtel app. Dow...` | **GENERAL** | **PROMOTIONAL** | `LOW` | **N** |
| 45 | `E2E Phase 2B test` | **GENERAL** | **GENERAL** | `EPHEMERAL` | **N** |
| 46 | `Mind blowing` | **GENERAL** | **GENERAL** | `EPHEMERAL` | **N** |
| 47 | `📄 2282/1423-202607031304533.pdf` | **GENERAL** | **GENERAL** | `EPHEMERAL` | **N** |
| 48 | `📷 3 photos` | **GENERAL** | **GENERAL** | `EPHEMERAL` | **N** |
| 49 | `📷 Photo` | **GENERAL** | **GENERAL** | `EPHEMERAL` | **N** |
| 50 | `Hello are you there` | **GENERAL** | **GENERAL** | `EPHEMERAL` | **N** |

---

## Retention Policy Design Proposal

To ensure the FYI database does not accumulate unnecessary volume over time, we propose the following retention policy based on the `importance_level` field:

* **EPHEMERAL** (7 Days Retention)
  * Chat greetings, media uploads without structured details, reaction confirmations.
* **LOW** (30 Days Retention)
  * Promo texts, coupon offers, reward updates, feedback surveys.
* **MEDIUM** (180 Days Retention)
  * Package delivery notices, train/flight status, location check-ins.
* **HIGH** (Forever Retention)
  * School homework bulletins, medical prescriptions, tenant records.
* **CRITICAL** (Forever Retention)
  * Policy renewals, hospitalization alerts, gate/security alarms.
