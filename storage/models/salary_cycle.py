# storage/models/salary_cycle.py

import uuid
from datetime import datetime
from sqlalchemy import String, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from storage.models.base import Base


class SalaryCycle(Base):
    __tablename__ = "salary_cycles"

    salary_cycle_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    salary_date: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )
    salary_amount: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )
    cycle_start: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )
    cycle_end: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
