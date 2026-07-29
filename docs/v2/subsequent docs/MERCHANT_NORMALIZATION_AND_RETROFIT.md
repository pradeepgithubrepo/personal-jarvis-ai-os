# Merchant Normalization & Manual Retrofit Framework

## 1. Two-Stage Normalization Approach

To solve the poor merchant quality and high variation in raw transaction text (e.g. `SWIGGY`, `SWIGGY LTD`, `SWIGGY*BANGALORE`), the system uses a sequential two-stage normalization engine:

```
Raw Narration ➔ Stage 1: Deterministic Mapping ➔ Stage 2: LLM Recommendation ➔ User Validation ➔ Cached Mapping
```

---

## 2. Stage 1: Deterministic Normalization
The engine first checks a local synonym lookup table. If the raw string contains a known keyword, it immediately maps it without calling the LLM.

### Example Rules:
- `SWIGGY*` / `SWIGGY LTD` / `SWIGGY` ➔ **Swiggy**
- `AMAZON PAY` / `AMAZON MX` / `AMZN` ➔ **Amazon**
- `APOLLO PHARMACY` / `APOLLO PHAR` ➔ **Apollo Pharmacy**
- `ZOMATO*` / `ZOMATOLTD` ➔ **Zomato**

---

## 3. Stage 2: LLM Recommendation & Human-in-the-Loop
If the raw merchant is not found in the deterministic lookup table:
1. The transaction is routed to the LLM (Gemini) with a prompt requesting a normalized merchant name and a recommended category.
2. The LLM returns a proposal (e.g., `SWIGGYBANGALORE` ➔ `Swiggy`, Category: `Food`).
3. The transaction is marked as `is_override = False` and added to a pending approval queue for the user.

---

## 4. Manual Retrofit Database Schema

To support manual correction capability and ensure the system learns from user overrides, we define a mapping memory table:

```sql
CREATE TABLE merchant_normalization_rules (
    rule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_merchant VARCHAR(150) UNIQUE NOT NULL,      -- The exact raw string extracted
    normalized_merchant VARCHAR(100) NOT NULL,       -- User-approved clean name
    category_override VARCHAR(30),                   -- User-approved category
    is_self_transfer_override BOOLEAN DEFAULT false,  -- User-approved transfer flag
    approved_by_user BOOLEAN DEFAULT false,          -- True if verified by user
    created_at TIMESTAMPTZ DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ DEFAULT clock_timestamp()
);

-- Index for high-speed queries during transaction ingestion
CREATE INDEX idx_raw_merchant ON merchant_normalization_rules(raw_merchant);
```

---

## 5. How Mappings Evolve Over Time

When the user modifies a transaction's category or merchant name in the UI:
1. **Insert/Update Rule**: A record is written to `merchant_normalization_rules` with the `raw_merchant`, the new `normalized_merchant` / `category_override`, and `approved_by_user = True`.
2. **Ledger Update (Retrofit)**: The system runs a historical update query to find all past transactions matching that `raw_merchant` and updates their ledger fields to match the user's override.
3. **Inheritance**: Any future transaction carrying the same `raw_merchant` will hit the deterministic mapping first, bypassing the LLM and instantly inheriting the approved correction.
