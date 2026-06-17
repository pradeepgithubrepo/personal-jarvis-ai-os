from datetime import datetime

from sqlalchemy import (
    String,
    DateTime,
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from storage.db.database import Base


class Task(Base):

    __tablename__ = "tasks"

    id: Mapped[int] = (
        mapped_column(
            primary_key=True
        )
    )

    title: Mapped[str] = (
        mapped_column(
            String(500)
        )
    )

    category: Mapped[str] = (
        mapped_column(
            String(100)
        )
    )

    priority: Mapped[str] = (
        mapped_column(
            String(50)
        )
    )

    source: Mapped[str] = (
        mapped_column(
            String(50)
        )
    )

    status: Mapped[str] = (
        mapped_column(
            String(50),
            default="pending"
        )
    )

    due_date: Mapped[str] = (
        mapped_column(
            String(100),
            nullable=True
        )
    )

    created_at: Mapped[
        datetime
    ] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )