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
    from storage.models.signal_classification import SignalClassification
    from storage.models.todo import Todo
    from storage.models.financial_event import FinancialEvent
    from storage.models.fyi_event import FyiEvent
    from storage.models.daily_brief import DailyBrief
    from storage.models.category_correction import CategoryCorrection

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

        # Check existing columns in financial_events
        result_fin = conn.execute(text("PRAGMA table_info(financial_events)"))
        columns_fin = [row[1] for row in result_fin.fetchall()]
        if "category" not in columns_fin:
            logger.info("Migrating database: adding category to financial_events")
            conn.execute(text("ALTER TABLE financial_events ADD COLUMN category VARCHAR(100)"))
            conn.commit()

        # Clear old entries from signals table to ensure clean slate as per user feedback (Moved to onetime_load.py)
        # logger.info("Clearing old entries from signals table for a clean slate...")
        # conn.execute(text("DELETE FROM signals"))
        # conn.commit()

    logger.success("SQLite connected successfully")