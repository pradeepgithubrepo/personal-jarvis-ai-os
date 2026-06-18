from datetime import datetime

from sqlalchemy import (
    String,
    DateTime,
    Text,
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from storage.models.base import Base


class Signal(Base):

    __tablename__ = "signals"

    id: Mapped[int] = (
        mapped_column(
            primary_key=True
        )
    )

    source: Mapped[str] = (
        mapped_column(
            String(50)
        )
    )

    signal_type: Mapped[str] = (
        mapped_column(
            String(100)
        )
    )

    category: Mapped[str] = (
        mapped_column(
            String(100)
        )
    )

    importance: Mapped[str] = (
        mapped_column(
            String(50)
        )
    )

    summary: Mapped[str] = (
        mapped_column(
            String(1000)
        )
    )

    raw_json: Mapped[str] = (
        mapped_column(
            Text,
            nullable=True
        )
    )

    created_at: Mapped[
        datetime
    ] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )