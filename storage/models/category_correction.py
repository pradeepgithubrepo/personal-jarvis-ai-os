# storage/models/category_correction.py

from datetime import datetime
from sqlalchemy import Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from storage.models.base import Base


class CategoryCorrection(Base):
    __tablename__ = "category_corrections"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )
    
    merchant: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )
    
    new_category: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    
    correction_count: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
