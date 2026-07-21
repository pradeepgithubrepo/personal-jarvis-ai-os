from typing import TypedDict, Optional

class MonthlySpendingSummary(TypedDict):
    month_key: str
    total_income: float
    total_expense: float
    total_transfers: float
    net_cashflow: float
    transaction_count: int

class MonthlyCategorySpend(TypedDict):
    month_key: str
    category: str
    amount: float
    transaction_count: int

class MonthlyMerchantSpend(TypedDict):
    month_key: str
    merchant_name: str
    amount: float
    transaction_count: int

class MonthlyIncomeSources(TypedDict):
    month_key: str
    source_name: str
    amount: float
    transaction_count: int

class MonthlyTopTransactions(TypedDict):
    month_key: str
    transaction_id: str
    amount: float
    merchant: Optional[str]
    category: Optional[str]
    rank: int
