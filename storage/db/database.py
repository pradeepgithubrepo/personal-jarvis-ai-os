from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from configs.settings import settings

DATABASE_URL = f"sqlite:///{settings.sqlite_db_path}"

engine = create_engine(
    DATABASE_URL,
    echo=False,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def initialize_database():
    logger.info("Initializing SQLite database...")

    from storage.models.base import Base
    from storage.models.runtime_event import RuntimeEvent
    from storage.models.signal import Signal
    from storage.models.mobile_signal import MobileSignal
    from storage.models.task import Task

    Base.metadata.create_all(bind=engine)

    # Check and add message_hash column if it doesn't exist
    from sqlalchemy import text
    with engine.connect() as conn:
        # Check existing columns
        result = conn.execute(text("PRAGMA table_info(mobile_signals)"))
        columns = [row[1] for row in result.fetchall()]
        if "message_hash" not in columns:
            logger.info("Migrating database: adding message_hash to mobile_signals")
            conn.execute(text("ALTER TABLE mobile_signals ADD COLUMN message_hash VARCHAR(64)"))
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_mobile_signals_message_hash ON mobile_signals (message_hash)"))
            conn.commit()

        # Check existing columns in signals
        result_signals = conn.execute(text("PRAGMA table_info(signals)"))
        columns_signals = [row[1] for row in result_signals.fetchall()]
        if "message_id" not in columns_signals:
            logger.info("Migrating database: adding message_id to signals")
            conn.execute(text("ALTER TABLE signals ADD COLUMN message_id VARCHAR(255)"))
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_signals_message_id ON signals (message_id)"))
            conn.commit()

        # Clear old entries from signals table to ensure clean slate as per user feedback
        logger.info("Clearing old entries from signals table for a clean slate...")
        conn.execute(text("DELETE FROM signals"))
        conn.commit()

    logger.success("SQLite connected successfully")