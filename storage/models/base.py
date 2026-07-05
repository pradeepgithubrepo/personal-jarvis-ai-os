# storage/models/base.py

from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Boolean, DateTime

class Base(DeclarativeBase):
    pass

class LineageMixin:
    batch_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sync_status: Mapped[str | None] = mapped_column(String(50), default="SYNCED", nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)