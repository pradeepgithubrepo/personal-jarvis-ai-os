# storage/models/fact_relationship.py

from datetime import datetime
from sqlalchemy import String, Float, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column
from storage.models.base import Base


class FactRelationship(Base):
    """
    Directional graph edge connecting two canonical Facts.
    """
    __tablename__ = "fact_relationships"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    subject_id: Mapped[str] = mapped_column(
        ForeignKey("facts.fact_id", ondelete="CASCADE"), nullable=False, index=True
    )

    predicate: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="spouse_of | parent_of | child_of | owned_by | belongs_to | member_of"
    )

    object_id: Mapped[str] = mapped_column(
        ForeignKey("facts.fact_id", ondelete="CASCADE"), nullable=False, index=True
    )

    confidence: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.5
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
