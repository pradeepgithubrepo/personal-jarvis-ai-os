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
    from storage.models.task import Task

    Base.metadata.create_all(bind=engine)

    logger.success("SQLite connected successfully")