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
    from storage.models.spending_category import SpendingCategory
    from storage.models.monthly_category_spend import MonthlyCategorySpend
    from storage.models.monthly_category_trend import MonthlyCategoryTrend
    from storage.models.processed_file import ProcessedFile
    from storage.models.financial_transaction_classification import FinancialTransactionClassification
    from storage.models.monthly_spending_summary import MonthlySpendingSummary
    from storage.models.classification_cache import ClassificationCache
    from storage.models.pipeline_run import PipelineRun
    from storage.models.system_status import SystemStatus
    from storage.models.qualified_signal import QualifiedSignal
    from storage.models.understood_signal import UnderstoodSignal
    # Module 4 — Financial Agent models
    from storage.models.bank_account import BankAccount
    from storage.models.transfer_pair import TransferPair
    from storage.models.salary_source import SalarySource
    from storage.models.salary_event import SalaryEvent
    from storage.models.merchant import Merchant
    from storage.models.merchant_profile import MerchantProfile
    from storage.models.financial_fact import FinancialFact
    from storage.models.fact import Fact
    from storage.models.fact_relationship import FactRelationship
    from storage.models.todo_item import TodoItem

    # Drop legacy tables to recreate with updated schemas cleanly
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS daily_briefs"))
        conn.execute(text("DROP TABLE IF EXISTS fyi_events"))
        conn.execute(text("DROP TABLE IF EXISTS monthly_category_trends"))
        conn.execute(text("DROP TABLE IF EXISTS monthly_category_spend"))
        conn.execute(text("DROP TABLE IF EXISTS monthly_financial_summary"))
        conn.execute(text("DROP TABLE IF EXISTS salary_cycles"))
        conn.commit()

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

        # Module 4 V2 monthly rollup columns. Older local caches only have
        # total_spend/transaction_count; add the split financial view in place.
        result_summary = conn.execute(text("PRAGMA table_info(monthly_spending_summary)"))
        columns_summary = [row[1] for row in result_summary.fetchall()]
        monthly_summary_columns = {
            "total_debits": "FLOAT NOT NULL DEFAULT 0.0",
            "total_credits": "FLOAT NOT NULL DEFAULT 0.0",
            "accounting_spend": "FLOAT NOT NULL DEFAULT 0.0",
            "lifestyle_spend": "FLOAT NOT NULL DEFAULT 0.0",
            "total_income": "FLOAT NOT NULL DEFAULT 0.0",
            "net_cash_flow": "FLOAT NOT NULL DEFAULT 0.0",
            "internal_transfers": "FLOAT NOT NULL DEFAULT 0.0",
            "insurance_premiums": "FLOAT NOT NULL DEFAULT 0.0",
            "investments": "FLOAT NOT NULL DEFAULT 0.0",
            "refund_offsets": "FLOAT NOT NULL DEFAULT 0.0",
        }
        for column_name, column_type in monthly_summary_columns.items():
            if column_name not in columns_summary:
                logger.info(
                    f"Migrating database: adding {column_name} to monthly_spending_summary"
                )
                conn.execute(
                    text(
                        f"ALTER TABLE monthly_spending_summary "
                        f"ADD COLUMN {column_name} {column_type}"
                    )
                )
        conn.commit()

        # Clear old entries from signals table to ensure clean slate as per user feedback (Moved to onetime_load.py)
        # logger.info("Clearing old entries from signals table for a clean slate...")
        # conn.execute(text("DELETE FROM signals"))
        # conn.commit()

    logger.success("SQLite connected successfully")

    # Seed reference data — idempotent (skip rows that already exist)
    _seed_bank_accounts(engine)
    _seed_merchants(engine)


def _seed_bank_accounts(engine) -> None:
    """Seeds the bank_account table with the user's known accounts if not already present."""
    from sqlalchemy.orm import sessionmaker as sm
    from storage.models.bank_account import BankAccount
    from storage.seeds.bank_accounts_seed import BANK_ACCOUNTS_SEED

    Session = sm(bind=engine, autocommit=False, autoflush=False)
    db = Session()
    try:
        for entry in BANK_ACCOUNTS_SEED:
            existing = db.query(BankAccount).filter(
                BankAccount.bank_name == entry["bank_name"],
                BankAccount.account_number_masked == entry.get("account_number_masked")
            ).first()
            if not existing:
                db.add(BankAccount(**entry))
        db.commit()
        logger.info("Bank accounts seed complete.")
    except Exception as e:
        db.rollback()
        logger.warning(f"Bank accounts seed failed (non-fatal): {e}")
    finally:
        db.close()


def _seed_merchants(engine) -> None:
    """Seeds the merchant table with pre-built canonical entries if not already present."""
    from sqlalchemy.orm import sessionmaker as sm
    from storage.models.merchant import Merchant
    from storage.seeds.merchant_seed import MERCHANT_SEED

    Session = sm(bind=engine, autocommit=False, autoflush=False)
    db = Session()
    try:
        for entry in MERCHANT_SEED:
            existing = db.query(Merchant).filter(
                Merchant.canonical_name == entry["canonical_name"]
            ).first()
            if not existing:
                db.add(Merchant(
                    canonical_name=entry["canonical_name"],
                    category=entry["category"],
                    aliases=entry["aliases"],
                    is_trusted=entry.get("is_trusted", True),
                    is_seed=True,
                ))
        db.commit()
        logger.info("Merchant registry seed complete.")
    except Exception as e:
        db.rollback()
        logger.warning(f"Merchant seed failed (non-fatal): {e}")
    finally:
        db.close()
