# storage/models/classification_cache.py

from datetime import datetime
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from storage.models.base import Base

class ClassificationCache(Base):
    __tablename__ = "classification_cache"

    cache_key: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    result_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
