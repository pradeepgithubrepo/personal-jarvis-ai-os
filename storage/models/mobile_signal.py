from datetime import datetime

from sqlalchemy import (
    String,
    DateTime,
    Text,
    Boolean
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column
)

from storage.models.base import Base


class MobileSignal(Base):

    __tablename__ = "mobile_signals"

    id: Mapped[int] = (
        mapped_column(
            primary_key=True
        )
    )

    device_id: Mapped[str] = (
        mapped_column(
            String(100)
        )
    )

    source: Mapped[str] = (
        mapped_column(
            String(50)
        )
    )

    sender: Mapped[str] = (
        mapped_column(
            String(500)
        )
    )

    message: Mapped[str] = (
        mapped_column(
            Text
        )
    )

    mobile_timestamp: Mapped[str] = (
        mapped_column(
            String(100)
        )
    )

    processed: Mapped[bool] = (
        mapped_column(
            Boolean,
            default=False
        )
    )

    created_at: Mapped[
        datetime
    ] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )