# storage/models/fact.py

import uuid
from datetime import datetime
from sqlalchemy import String, Float, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from storage.models.base import Base


class Fact(Base):
    """
    The canonical long-term memory ledger for Jarvis AI OS.
    Stores verified, stateful facts about the user's life, family, and assets.
    """
    __tablename__ = "facts"

    fact_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    fact_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True,
        comment="PERSON | SPOUSE | CHILD | BANK_ACCOUNT | INSURANCE_POLICY | VEHICLE | PROPERTY | SUBSCRIPTION | PREFERENCE | CONTACT"
    )

    fact_value: Mapped[dict] = mapped_column(
        JSON, nullable=False,
        comment="Structured payload specific to the fact_type"
    )

    confidence: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.5
    )

    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="UNCONFIRMED",
        comment="UNCONFIRMED | VERIFIED | MANUAL_LOCK | RETIRED | ARCHIVED"
    )

    owner_agent: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )

    source_agent: Mapped[str] = mapped_column(
        String(50), nullable=False
    )

    source_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default="OBSERVED"
    )

    first_seen: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    last_seen: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    evidence: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
