import os
import sys
import json
import shutil
from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add root folder to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import initialize_database
from storage.models.base import Base

# Preload all models to avoid ForeignKey referencing errors
from storage.models.qualified_signal import QualifiedSignal
from storage.models.understood_signal import UnderstoodSignal
from storage.models.financial_event import FinancialEvent
from storage.models.financial_fact import FinancialFact
from storage.models.transfer_pair import TransferPair
from storage.models.salary_event import SalaryEvent
from storage.models.salary_source import SalarySource
from storage.models.merchant_profile import MerchantProfile
from storage.models.merchant import Merchant
from storage.models.bank_account import BankAccount
from storage.models.signal import Signal
from storage.models.signal_classification import SignalClassification

from services.financial_agent import FinancialAgent

def main():
    db_path = "/home/prad/petprojects/ai/jarvis/storage/db/sqlite/jarvis.db"
    temp_db_path = "/tmp/jarvis_module4_validation.db"
    
    # Copy DB
    if os.path.exists(temp_db_path):
        os.remove(temp_db_path)
    shutil.copy(db_path, temp_db_path)
    logger.info(f"Copied {db_path} to {temp_db_path}")
    
    # Create engine and session for temp db
    engine = create_engine(f"sqlite:///{temp_db_path}")
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = Session()
    
    try:
        # Clear tables
        db.query(FinancialFact).delete()
        db.query(FinancialEvent).delete()
        db.query(TransferPair).delete()
        db.query(SalaryEvent).delete()
        db.query(MerchantProfile).delete()
        db.commit()
        logger.info("Cleared all financial tables in test database.")
        
        rows = db.query(UnderstoodSignal).all()
        logger.info(f"Loaded {len(rows)} understood signals.")
        
        processed = 0
        skipped = 0
        failed = 0
        
        # Instantiate FinancialAgent with our custom session
        agent = FinancialAgent(db=db)
        
        for row in rows:
            try:
                contract = json.loads(row.contract_json)
            except Exception as exc:
                skipped += 1
                continue

            if "FINANCIAL" not in contract.get("classes", []):
                continue

            try:
                fact = agent.process_contract(contract)
                if fact is None:
                    skipped += 1
                else:
                    processed += 1
            except Exception as exc:
                failed += 1
                logger.error(f"FAIL: Signal ID {contract.get('signal_id')} ({contract.get('summary')}) -> {exc}")
                import traceback
                logger.error(traceback.format_exc())

        finalization = agent.finalize_batch()
        logger.info(f"Finalization metrics: {finalization}")
        logger.info(f"Processed: {processed}, Skipped: {skipped}, Failed: {failed}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
