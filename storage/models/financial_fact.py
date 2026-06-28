# storage/models/financial_fact.py

import uuid
from datetime import datetime, date
from sqlalchemy import String, Float, Boolean, DateTime, Date, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from storage.models.base import Base


class FinancialFact(Base):
    """
    The Financial Agent's typed fact ledger.

    Every monetary event that passes through the Financial Agent produces one FinancialFact.
    Full signal lineage is preserved: fact → financial_event → understood_signal →
    qualified_signal → raw_signal.

    fact_type values:
        EXPENSE_EVENT       — classified debit (lifestyle or fixed cost)
        INCOME_SALARY       — detected salary credit
        INCOME_OTHER        — other confirmed income (non-salary, non-transfer)
        INTERNAL_TRANSFER   — leg of an internal transfer (debit or credit)
        REFUND_EVENT        — confirmed refund; offsets a prior EXPENSE_EVENT
        INSURANCE_PAYMENT   — insurance premium paid
        INVESTMENT_EVENT    — SIP, mutual fund, stock purchase
        BILL_PAYMENT        — utility or credit card payment
    """
    __tablename__ = "financial_facts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # --- Fact type ---
    fact_type: Mapped[str] = mapped_column(
        String(30), nullable=False,
        comment="EXPENSE_EVENT | INCOME_SALARY | INCOME_OTHER | INTERNAL_TRANSFER | "
                "REFUND_EVENT | INSURANCE_PAYMENT | INVESTMENT_EVENT | BILL_PAYMENT"
    )

    # --- Lineage (full chain preserved) ---
    financial_event_id: Mapped[int] = mapped_column(
        ForeignKey("financial_events.id", ondelete="CASCADE"), nullable=False
    )
    understood_signal_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True,
        comment="UUID of the understood_signal that produced this fact"
    )
    qualified_signal_id: Mapped[int | None] = mapped_column(
        ForeignKey("qualified_signals.id", ondelete="SET NULL"), nullable=True
    )

    # --- Amount ---
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="INR")

    # --- Merchant ---
    merchant_raw: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
        comment="Raw merchant string from SUA contract"
    )
    merchant_canonical: Mapped[str | None] = mapped_column(
        String(200), nullable=True,
        comment="Resolved canonical merchant name"
    )
    merchant_id: Mapped[str | None] = mapped_column(
        ForeignKey("merchants.id", ondelete="SET NULL"), nullable=True
    )

    # --- Expense classification ---
    category: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
        comment="e.g. FOOD_DINING, GROCERIES, INTERNAL_TRANSFER"
    )
    classification_confidence: Mapped[float] = mapped_column(
        Float, nullable=False, default=1.0
    )
    classification_method: Mapped[str | None] = mapped_column(
        String(30), nullable=True,
        comment="keyword | merchant_registry | llm | manual"
    )

    # --- Temporal ---
    event_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    month: Mapped[date | None] = mapped_column(
        Date, nullable=True,
        comment="First day of the month this fact belongs to (for aggregation)"
    )

    # --- Aggregation control ---
    is_excluded_from_accounting_spend: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="True for INTERNAL_TRANSFER legs"
    )
    is_excluded_from_lifestyle_spend: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="True for INVESTMENT, INSURANCE_PAYMENT, BILL_PAYMENT (CC)"
    )
    exclusion_reason: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )

    # --- Refund linkage ---
    refund_of_fact_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True,
        comment="For REFUND_EVENT: UUID of the original EXPENSE_EVENT fact this offsets"
    )
    is_refunded: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="True on an EXPENSE_EVENT that has been offset by a REFUND_EVENT"
    )
    refund_applied_to_month: Mapped[date | None] = mapped_column(
        Date, nullable=True,
        comment="Month where the refund offset was applied (may differ from refund month)"
    )

    # --- Salary linkage ---
    salary_source_id: Mapped[str | None] = mapped_column(
        ForeignKey("salary_sources.id", ondelete="SET NULL"), nullable=True,
        comment="Set for INCOME_SALARY facts matched to a registered salary source"
    )

    # --- Transfer linkage ---
    transfer_pair_id: Mapped[str | None] = mapped_column(
        ForeignKey("transfer_pairs.id", ondelete="SET NULL"), nullable=True,
        comment="Set for INTERNAL_TRANSFER facts"
    )

    # --- Audit ---
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
