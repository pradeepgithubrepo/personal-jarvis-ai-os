# FINANCIAL_SUMMARY_PHASE1_VALIDATION

This report validates the monthly aggregates produced by Phase 1 of the Financial Summary Agent.

## Months Processed Summary

| Month | Total Income | Total Expense | Total Transfers | Net Cashflow | Transaction Count |
|---|---|---|---|---|---|
| 2026-06 | ₹615,510.66 | ₹863,762.79 | ₹636,113.00 | ₹-248,252.13 | 234 |
| 2026-07 | ₹143.00 | ₹147,860.89 | ₹4,340.00 | ₹-147,717.89 | 42 |

## Top Categories per Month

### Category Spending - 2026-06

| Category | Amount | Transaction Count |
|---|---|---|
| Other | ₹682,558.38 | 95 |
| Shopping | ₹106,056.00 | 25 |
| Investment | ₹60,000.00 | 3 |
| Housing | ₹5,795.00 | 8 |
| Food | ₹5,023.00 | 29 |
| Utilities | ₹2,668.00 | 5 |
| Medical | ₹1,662.41 | 6 |

### Category Spending - 2026-07

| Category | Amount | Transaction Count |
|---|---|---|
| Other | ₹112,324.02 | 12 |
| Investment | ₹25,000.00 | 5 |
| Education | ₹4,980.00 | 2 |
| Utilities | ₹2,550.00 | 2 |
| Food | ₹1,526.00 | 2 |
| Medical | ₹936.87 | 2 |
| Shopping | ₹544.00 | 3 |

## Top Merchants per Month

### Top Merchants - 2026-06

| Merchant | Amount | Transaction Count |
|---|---|---|
| Bank Account | ₹172,000.00 | 1 |
| Axis Bank | ₹168,521.36 | 3 |
| Unknown Merchant | ₹141,500.00 | 6 |
| Flipkart | ₹72,749.00 | 5 |
| ET Money | ₹60,000.00 | 3 |
| *And 89 other merchants* | | |

### Top Merchants - 2026-07

| Merchant | Amount | Transaction Count |
|---|---|---|
| Indian Clearing Corporation | ₹100,000.00 | 1 |
| ET Money | ₹20,000.00 | 4 |
| HDFC Bank | ₹6,500.00 | 1 |
| ICICI Mutual Funds | ₹5,000.00 | 1 |
| Nellai Child Care | ₹4,980.00 | 2 |
| *And 19 other merchants* | | |

## Top Income Sources per Month

### Income Sources - 2026-06

| Source | Amount | Transaction Count |
|---|---|---|
| Salary Payment | ₹234,859.00 | 1 |
| Eyglodelserindll | ₹234,859.00 | 1 |
| HDFC Bank | ₹124,413.00 | 4 |
| Flipkart | ₹7,791.00 | 1 |
| TMB Bank | ₹5,222.33 | 1 |
| NPS Trust | ₹5,222.33 | 1 |
| SBI | ₹3,141.00 | 1 |
| Google | ₹3.00 | 2 |

### Income Sources - 2026-07

| Source | Amount | Transaction Count |
|---|---|---|
| Vilvah | ₹100.00 | 1 |
| Jeevan Jose | ₹30.00 | 1 |
| Interest Payment | ₹12.00 | 1 |
| Indian Clearing Corp | ₹1.00 | 1 |

## Reconciliation & Validation Results

> [!NOTE]
> All monthly datasets successfully validated against the ledger assertions:
> 1. **Rule 1**: Sum of Category Spending matches the Total Expense exactly.
> 2. **Rule 2**: Sum of Merchant Spending matches the Total Expense exactly.
> 3. **Rule 3**: Income minus Expense matches the Net Cashflow exactly.
> 4. **Rule 4**: Transfers are verified to be excluded from spending aggregates.

### Status: **PASSED ✅**