# storage/models/bank_account.py

import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from storage.models.base import Base


class BankAccount(Base):
    """
    Registry of the user's known bank accounts.
    Both legs of an internal transfer must resolve to rows in this table.
    """
    __tablename__ = "bank_accounts"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    bank_name: Mapped[str] = mapped_column(String(100), nullable=False)
    ifsc_prefix: Mapped[str | None] = mapped_column(String(10), nullable=True)
    account_number_masked: Mapped[str | None] = mapped_column(
        String(20), nullable=True,  # e.g. "xx3221"
        comment="Masked account number as it appears in SMS"
    )
    account_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="savings",
        comment="savings | current | credit"
    )
    # Sender IDs seen in SMS (e.g. ["JM-HDFCBK-S", "CP-HDFCBK-S", "HDFCBK"])
    sender_aliases: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list,
        comment="SMS sender strings that identify the debit leg"
    )
    # Strings seen in message body that identify this account as receiver
    receiver_aliases: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list,
        comment="Message body strings that identify the credit leg"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
