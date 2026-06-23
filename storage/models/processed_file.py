# storage/models/processed_file.py

from datetime import datetime
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from storage.models.base import Base


class ProcessedFile(Base):
    __tablename__ = "processed_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    file_name: Mapped[str] = mapped_column(String(255))
    bucket_name: Mapped[str] = mapped_column(String(100))
    file_path: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    file_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(50))  # PROCESSED, FAILED, SKIPPED
    processed_timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
