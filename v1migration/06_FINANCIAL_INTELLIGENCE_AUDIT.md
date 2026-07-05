# Jarvis V1 — Financial Intelligence Audit

> Migration Knowledge Base · Document 06  
> Produced: 2026-07-04 · Source: `services/financial_agent.py`, `services/financial_classifier.py`, `services/aggregation_service.py`, `docs/JARVIS_ARCHITECTURAL_ANCHOR.md` Section 9

---

## Overview

The financial intelligence subsystem is the most mature and technically sophisticated component of Jarvis V1. It converts raw SMS messages about monetary events into a structured, typed financial ledger with full signal lineage, accurate category breakdowns, internal transfer exclusion, salary detection, and refund offsetting.

This audit documents what exists, what works, what is missing, and what users actually need.

---

## Current Processing Flow

### Step 1 — Signal Capture

Raw bank SMS messages arrive in the Android device. They are captured by `SmsRepository` and queued as `mobile_signals`. Examples:

- "Your a/c XXXX9012 is debited with Rs.450.00 on 04-07-26 to ZOMATO INTERNET PVT LTD"
- "INR 2,500 received in your HDFC Bank account XXXX1234 from A/C XXXX5678"
- "Your SBI account XXXX3456 debited Rs.12,500 via NEFT to HDFC A/C XXXX9012"

### Step 2 — Qualification

`SignalQualificationAgent` applies:
- Age filter: signals older than 90 days → REJECTED
- Duplicate check: same message within 48 hours → REJECTED
- Financial preservation override: any message with financial keywords cannot be silently rejected

### Step 3 — Signal Understanding

`SignalUnderstandingAgent` runs the deterministic path:

**Financial Transaction Rule (RULE_ENGINE path):**
Keywords triggering FINANCIAL class: `debited`, `credited`, `spent`, `transacted`, `received rs`, `received inr`, `amount credited`, `transaction of inr`.

Whitespace normalisation is applied before matching (`re.sub(r'\s+', ' ', msg_lower)`) to handle multi-line bank SMS formats.

Amount extraction regex: `(?:rs\.?|inr)\s?[\d,]+`
Merchant extraction: regex patterns targeting "to [MERCHANT_NAME]", "at [MERCHANT_NAME]", VPA patterns

Contract produced includes:
- `classes: ["FINANCIAL"]`
- `entities.monetary_value.amount`
- `entities.merchants[]`
- `confidence`: 1.0 for rule-engine path

### Step 4 — Financial Agent Processing

`FinancialAgent.process_contract(contract)` receives the contract and:

1. Checks contract is FINANCIAL class (rejects non-FINANCIAL immediately)
2. Persists `FinancialEvent` (idempotent — checks `source_signal_id` before creating)
3. Resolves merchant canonical name from registry
4. Runs 4-condition internal transfer detection
5. Runs 4-tier salary detection
6. Classifies expense category (`FinancialClassifier`)
7. Writes `FinancialFact` with full lineage
8. Updates `MerchantProfile`
9. Triggers `AggregationService.run_for_month()`

### Step 5 — Aggregation

`AggregationService.run_for_month(month_key)` recomputes monthly rollups:
- Accounting Spend (all debits minus internal transfers)
- Lifestyle Spend (Accounting Spend minus investments, insurance, CC payments)
- Total Income (confirmed salary + INCOME_UNCLASSIFIED)
- Net Cashflow (Income − Accounting Spend)
- Per-category totals
- MoM percentage trends

Writes to `monthly_spending_summary`, `monthly_category_spend`, `monthly_category_trends` (all Supabase).

---

## Current Classification Logic

### Category Taxonomy (25 categories)

**Lifestyle spend categories:**
- FOOD_DINING (Zomato, Swiggy)
- GROCERIES (BigBasket, Zepto, Blinkit)
- TRANSPORT (Ola, Uber, Rapido)
- TRAVEL (IRCTC, MakeMyTrip)
- ENTERTAINMENT (Netflix, Spotify, Amazon Prime, Hotstar)
- MEDICAL (Apollo Pharmacy, MedPlus)
- SHOPPING (Amazon, Flipkart)
- UTILITIES (Airtel, Jio, TNEB/Tangedco)
- EDUCATION
- FAMILY
- FUEL
- FISH (niche personal category)
- MUTTON (niche personal category)
- VEGETABLES (niche personal category)

**Financial obligation categories (excluded from Lifestyle Spend):**
- INSURANCE
- INVESTMENT
- BILL_PAYMENT

**Income and system types (not spending):**
- INCOME_SALARY
- INCOME_UNCLASSIFIED
- REFUND_EVENT
- INTERNAL_TRANSFER

**Fallback:**
- OTHER

### Classification Resolution Order

1. **Pre-seeded merchant registry** (24 merchants, 45+ aliases) — substring match, `confidence = 1.0`
2. **Heuristic keyword checks** (fish/meen/fresh catch → FISH; mutton/goat → MUTTON; vegetables/greens → VEGETABLES)
3. **Rules Engine** (user overrides + dynamic merchant/VPA mappings from `jarvis_rules.json`)
4. **LLM fallback** (Ollama `qwen3:1.7b` prompt, result cached by SHA-256 hash)

### Pre-seeded Merchant Registry

| Category | Merchants |
|----------|----------|
| FOOD_DINING | Zomato, Swiggy |
| GROCERIES | BigBasket, Zepto, Blinkit, Grofers |
| MEDICAL | Apollo Pharmacy, MedPlus |
| UTILITIES | Airtel, Jio, TNEB/Tangedco |
| ENTERTAINMENT | Netflix, Spotify, Amazon Prime, Hotstar |
| SHOPPING | Amazon Seller, Flipkart |
| TRANSPORT | Ola Cabs, Uber India, Rapido |
| TRAVEL | IRCTC, MakeMyTrip |
| INSURANCE | Coverfox, LIC of India |
| BILL_PAYMENT | SBI Card, HDFC Card |
| INVESTMENT | Zerodha, Groww, Coin by Zerodha, Paytm Money, Mirae Asset, Axis Mutual, SBI Mutual, HDFC Mutual, ICICI Pru, Franklin Templeton, Navi Mutual |

---

## Known Gaps

### Gap 01 — GPay Lite / Wallet Funding Transactions

**What happens:** When the user funds a Google Pay balance (GPay Lite), the bank SMS shows a debit of the funded amount. This debit is captured by Jarvis and appears as a transfer from the bank account.

**The problem:** The actual spending that occurs *from* the wallet is invisible. The bank does not send SMS for wallet-to-merchant payments. The user's "₹1,000 topped up to GPay" appears as a debit, but the ₹250 spent at a local shop via GPay tap-to-pay is never seen.

**Impact:** Wallet top-ups inflate debit totals without the corresponding spend being visible. Monthly spending appears lower than actual because wallet spend is hidden.

**Current handling:** Wallet top-ups may be classified as INTERNAL_TRANSFER (if the rules engine matches the GPay UPI VPA) or as OTHER (if unclassified). Neither is accurate.

**V2 recommendation:** Tag GPay Lite funding debits explicitly as `WALLET_FUNDING` (excluded from lifestyle spend). Surface wallet balance as a known gap in the spending picture. Consider requesting UPI statement from the user periodically.

---

### Gap 02 — Credit Card Actual Spend Invisibility

**What happens:** The user has an SBI credit card. Every month, the bank sends one SMS: "Your SBI Card payment of ₹45,000 has been processed." Jarvis captures this as `BILL_PAYMENT_CC` (excluded from lifestyle spend, as designed). But the ₹45,000 represents actual spending across multiple merchants over the month — food, shopping, entertainment — and none of this is visible to Jarvis.

**The problem:** Credit card usage is a black box. The user may spend heavily on a card but Jarvis only sees the monthly payment, not the breakdown.

**Impact:** A household that uses credit cards extensively will have a misleadingly low "lifestyle spend" in Jarvis because card expenses are excluded from lifestyle spend (correctly, to avoid double-counting the card payment itself).

**Current handling:** `BILL_PAYMENT_CC` is excluded from lifestyle spend. This is architecturally correct to prevent double-counting, but leaves the user without visibility into what drove the card bill.

**V2 recommendation:** Request credit card statements (via email/SMS) for offline parsing. Alternatively, surface "card statement pending" as an explicit gap. Do not present an incomplete financial picture without labelling it as such.

---

### Gap 03 — NACH/ECS Debit for SIPs and Subscriptions

**What happens:** Mutual Fund SIP deductions via NACH (National Automated Clearing House) generate bank SMS that look like: "HDFC Bank Acct XXXX1234 debited Rs.10,000/- for NACH MANDATE SBI MUTUAL FUND." The sender alias or description often includes the fund house name, but the format varies.

**Current handling:** The merchant seed list covers some fund houses (`sbi mutual`, `hdfc mutual`, `mirae asset`, etc.). When the NACH description includes a recognised alias, it classifies correctly as INVESTMENT. When the description is generic (e.g., "NACH-ECS DEBIT") with no fund house name, it falls through to LLM or OTHER.

**Impact:** Some SIP deductions are correctly classified as INVESTMENT (and excluded from lifestyle spend). Others land in OTHER and inflate the unclassified spend bucket.

**V2 recommendation:** Expand the NACH/SIP keyword list. Add patterns for common NACH mandate descriptions from fund houses. Specifically: `NACH MANDATE`, `NACHWEB`, `NACHDR`, followed by fund house identification patterns.

---

### Gap 04 — Salary Handling — Registry Starts Empty

**Current state:** The 4-tier salary detection algorithm is correct. However, the `salary_sources` table (which powers Tier 2 — registry match) is empty at launch and must accumulate from Tier 3 candidates (recurring credit pattern). This means:
- Tier 1: Keyword match fires for messages with "salary" in the description
- Tier 2: Never fires until a Tier 3 candidate is confirmed
- Tier 3: Requires 3 months of consistent credits before generating a candidate
- Tier 4: Large credits (≥₹20,000) not matched by Tiers 1-3 are INCOME_UNCLASSIFIED

**Impact:** For the first 3 months, salary may be detected by Tier 1 (keyword) but if the employer uses generic NEFT credit descriptions without "salary" text, it will not be detected until Tier 3 kicks in.

**V2 recommendation:** During initial setup, present the user with a historical review of large recurring credits (last 6 months) and ask them to confirm which are salary. Seed the `salary_sources` registry from this confirmation exercise.

---

### Gap 05 — Interbank Transfer Detection — Supabase Tables Missing

**Current state:** The 4-condition internal transfer detection algorithm in `FinancialAgent` is correct and runs locally. However, `transfer_pairs` and `salary_sources` tables do not yet exist in Supabase (Technical Debt TD-4, TD-5). This means:
- Transfer pair records are created in SQLite only
- The detection logic no-ops gracefully when Supabase writes fail
- Transfer pairs are visible locally but not queryable from the dashboard or Android app

**V2 recommendation:** Create `transfer_pairs` and `salary_sources` tables in Supabase and run the pending DDL migrations.

---

### Gap 06 — Refund Matching Accuracy

**Current state:** The refund algorithm searches for a matching `EXPENSE_EVENT` in `financial_facts` with the same merchant and amount within the last 30 days. If found, the originating fact is flagged `is_refunded = True` and the refund is linked.

**Known weakness:** If the refund amount differs from the original (partial refunds, service charges) or if the refund arrives after 30 days, the link may not be established and the refund falls to `OTHER` category.

**Impact:** Partial refunds or delayed refunds may appear as unclassified income instead of expense offsets.

**V2 recommendation:** Extend the refund matching window to 90 days. Add tolerance for partial refund matching (e.g., refund is 70%+ of original amount).

---

### Gap 07 — Mutual Fund NAV / Portfolio Value

**Current state:** Jarvis tracks SIP debits as `INVESTMENT` category expenses. It has no visibility into the fund performance, current portfolio value, or NAV changes.

**Impact:** The user knows how much they invest monthly (via SIP debits) but not what the portfolio is worth.

**V2 recommendation:** This is out of scope for V2 (requires integration with fund account statements or a financial aggregator API). Document it as a known gap. Do not attempt to build it for V2.

---

## What Users Actually Need

Based on the design intent and the gaps identified, what users actually need from financial intelligence is:

### Need 01 — Consumption Tracking (Not Just Bank Debits)

Users want to know: "What did I actually spend my money on this month?" This requires:
- Lifestyle spend categorised by type (food, groceries, entertainment, utilities, transport)
- Explicit labelling of what is NOT visible (wallet spend, card underlying spend)
- A truthful "here's what I can see" stance rather than false completeness

### Need 02 — Spending Categories with Actual Names

"₹12,450 on FOOD_DINING" is better than "₹12,450 on dining". But "₹6,200 on Zomato, ₹4,100 on Swiggy, ₹2,150 at restaurants" is even better. The merchant-level detail exists (in `merchant_profiles`) but is not surfaced in the Daily Brief.

### Need 03 — Monthly Trends

"You spent ₹12,450 on food this month. That's ₹2,100 more than last month (+20%)." This is already computed in `monthly_category_trends`. The gap is surfacing it clearly in the brief.

### Need 04 — Investment Visibility

"You invested ₹25,000 this month across 3 SIPs." Users want to see their investment as a positive number (savings directed toward wealth creation), not buried in a list of debits marked INVESTMENT.

### Need 05 — Recurring Expenses

"Your regular monthly expenses: Airtel ₹799, Netflix ₹649, Spotify ₹119, TNEB electricity ₹1,200." Recurring expenses are predictable and the user should see them as a fixed overhead, not mixed with discretionary spending.

### Need 06 — Income Clarity

"You received ₹95,000 salary on 1 July." Simple, clear, verified. Not "Total credits: ₹1,45,000" which includes internal transfers and refunds alongside salary.

### Need 07 — Household Visibility

Currently only Pradeep's accounts are tracked. Shobana's bank accounts, her credit card payments, her salary — all invisible. For V2, the financial picture should represent the household, not just one member.

---

## Recommendations for V2 Financial Intelligence

| Area | V1 State | V2 Recommendation |
|------|----------|-------------------|
| Transaction capture | Bank SMS only | Continue; be honest about gaps |
| Category classification | Working | Expand NACH/SIP patterns |
| Internal transfer detection | Working locally | Deploy missing Supabase tables |
| Salary detection | Works for keyword matches | Bootstrap registry from historical data |
| Refund handling | Works for exact matches | Extend window and add tolerance |
| Wallet spend | Invisible | Label top-ups explicitly; surface as known gap |
| Credit card detail | Invisible | Request statement; label as gap |
| Investment tracking | Debit only (no portfolio) | SIP debit tracking only for V2 |
| Household visibility | Single user | V2 must include spouse accounts |
| Brief financial summary | Monthly rollup | Show income, lifestyle spend, top 3 categories, investments |

---

*Document: 06_FINANCIAL_INTELLIGENCE_AUDIT.md*  
*Part of Jarvis V1 Migration Knowledge Base*
