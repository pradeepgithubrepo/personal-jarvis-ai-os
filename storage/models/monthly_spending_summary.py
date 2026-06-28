# storage/models/monthly_spending_summary.py

import uuid
from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from storage.models.base import Base


class MonthlySpendingSummary(Base):
    """
    Monthly financial summary produced by the Aggregation Service.

    Two distinct spending views are maintained:

    accounting_spend  — all confirmed outflows (excl. internal transfers)
    lifestyle_spend   — day-to-day living cost (excl. investments + insurance premiums)

    net_cash_flow     = total_income − accounting_spend
    """
    __tablename__ = "monthly_spending_summary"

    summary_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    month_key: Mapped[str] = mapped_column(
        String(7), nullable=False, unique=True,
        comment="YYYY-MM format, e.g. '2026-05'"
    )
    total_spend: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
        comment="Legacy alias for accounting_spend"
    )

    # ── Core totals ───────────────────────────────────────────────────────────
    total_debits: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
        comment="Gross confirmed debit outflows before exclusions/offsets"
    )
    total_credits: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
        comment="Gross confirmed credit inflows before exclusions/offsets"
    )
    accounting_spend: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
        comment="All confirmed outflows excluding internal transfers"
    )
    lifestyle_spend: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
        comment="Day-to-day spend: accounting_spend minus investments, insurance, CC payments"
    )
    total_income: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
        comment="Salary + other confirmed income (not transfers, not refunds)"
    )
    net_cash_flow: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
        comment="total_income − accounting_spend"
    )

    # ── Separately tracked buckets ────────────────────────────────────────────
    internal_transfers: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
        comment="Total moved between user's own accounts (neutralised)"
    )
    insurance_premiums: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
        comment="Insurance premiums paid this month"
    )
    investments: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
        comment="SIP, mutual fund, stock purchases"
    )
    refund_offsets: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
        comment="Total refunds applied to expense categories (reduces gross spending)"
    )

    # ── Counts ────────────────────────────────────────────────────────────────
    transaction_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ── Audit ─────────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
