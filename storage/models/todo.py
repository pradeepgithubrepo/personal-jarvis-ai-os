# storage/models/todo.py

from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from storage.models.base import Base


class Todo(Base):
    __tablename__ = "todos"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )
    
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )
    
    due_date: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )
    
    source_signal_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("signals.id", ondelete="CASCADE"),
        nullable=False
    )
    
    priority: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
