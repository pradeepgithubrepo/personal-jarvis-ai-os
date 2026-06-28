# tests/test_fyi_agent.py

import sys
import os
import json
from unittest.mock import patch, MagicMock
from loguru import logger

# Add root folder to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import initialize_database, SessionLocal
from storage.models.fyi_event import FyiEvent
from storage.models.understood_signal import UnderstoodSignal
from services.fyi_agent import FyiAgent


def run_fyi_agent_tests():
    logger.info("Initializing database for FYI Agent tests...")
    initialize_database()

    db = SessionLocal()
    try:
        # Clear old events
        db.query(FyiEvent).delete()
        db.query(UnderstoodSignal).delete()
        db.commit()

        # Mock Supabase Repo writes to avoid network requests during agent tests
        mock_supabase_repo = MagicMock()
        mock_supabase_repo.store_fyi_event.return_value = True

        with patch("src.agents.fyi.repository.SupabaseRepo", mock_supabase_repo):

            # Test Case 1: Salary Credited (FYI Created, category FINANCIAL, importance MEDIUM)
            logger.info("Test Case 1: Ingesting salary credit signal...")
            mock_contract_salary = {
                "classes": ["INFORMATION"],
                "domains": ["FINANCE"],
                "entities": {}
            }
            sig_salary = UnderstoodSignal(
                id="sig-salary-01",
                qualified_signal_id=1,
                raw_signal_id="raw-1",
                signal_type="general",
                importance="MEDIUM",
                confidence=1.0,
                summary="Salary credited INR 2,00,000 to account HDFC",
                processing_path="RULE_ENGINE",
                llm_model_used="none",
                contract_json=json.dumps(mock_contract_salary)
            )
            db.add(sig_salary)
            db.commit()

            metrics = FyiAgent.process_all_understood_signals(db)
            assert metrics["fyi_created"] == 1
            
            fyi_salary = db.query(FyiEvent).filter(FyiEvent.event_type == "SALARY_CREDITED").first()
            assert fyi_salary is not None
            assert fyi_salary.category == "FINANCIAL"
            assert fyi_salary.importance == "MEDIUM"
            logger.success("Test Case 1: Passed.")

            # Test Case 2: Credit Card Due (No FYI, ACTION class excluded)
            logger.info("Test Case 2: Verifying action items (Credit Card Due) are ignored...")
            # Clean database first for isolation
            db.query(FyiEvent).delete()
            db.query(UnderstoodSignal).delete()
            db.commit()

            mock_contract_cc = {
                "classes": ["ACTION"],
                "domains": ["FINANCE"],
                "entities": {}
            }
            sig_cc = UnderstoodSignal(
                id="sig-cc-02",
                qualified_signal_id=2,
                raw_signal_id="raw-2",
                signal_type="general",
                importance="HIGH",
                confidence=1.0,
                summary="Credit card payment due tomorrow",
                processing_path="RULE_ENGINE",
                llm_model_used="none",
                contract_json=json.dumps(mock_contract_cc)
            )
            db.add(sig_cc)
            db.commit()

            FyiAgent.process_all_understood_signals(db)
            cc_events = db.query(FyiEvent).filter(FyiEvent.source_signal_id == "sig-cc-02").all()
            assert len(cc_events) == 0, "Actionable tasks should be excluded from FYI"
            logger.success("Test Case 2: Passed.")

            # Test Case 3: Duplicate Salary SMS
            logger.info("Test Case 3: Ingesting duplicate salary SMS to verify deduplication...")
            db.query(FyiEvent).delete()
            db.query(UnderstoodSignal).delete()
            db.commit()

            sig_salary_1 = UnderstoodSignal(
                id="sig-salary-10",
                qualified_signal_id=10,
                raw_signal_id="raw-10",
                signal_type="general",
                importance="MEDIUM",
                confidence=1.0,
                summary="Salary credited INR 2,00,000 to account HDFC",
                processing_path="RULE_ENGINE",
                llm_model_used="none",
                contract_json=json.dumps(mock_contract_salary)
            )
            sig_salary_2 = UnderstoodSignal(
                id="sig-salary-11",
                qualified_signal_id=11,
                raw_signal_id="raw-11",
                signal_type="general",
                importance="MEDIUM",
                confidence=1.0,
                summary="Salary credited INR 2,00,000 to account HDFC",
                processing_path="RULE_ENGINE",
                llm_model_used="none",
                contract_json=json.dumps(mock_contract_salary)
            )
            db.add(sig_salary_1)
            db.add(sig_salary_2)
            db.commit()

            FyiAgent.process_all_understood_signals(db)
            
            events = db.query(FyiEvent).all()
            assert len(events) == 1, f"Expected 1 FYI event due to deduplication, got {len(events)}"
            assert events[0].duplicate_count == 2, f"Expected duplicate count to be 2, got: {events[0].duplicate_count}"
            logger.success("Test Case 3: Passed.")

            # Test Case 4: School Notice (PTM meeting: Category = FAMILY, Importance = HIGH)
            logger.info("Test Case 4: Ingesting PTM school notice signal...")
            db.query(FyiEvent).delete()
            db.query(UnderstoodSignal).delete()
            db.commit()

            mock_contract_school = {
                "classes": ["INFORMATION"],
                "domains": ["EDUCATION"],
                "entities": {}
            }
            sig_school = UnderstoodSignal(
                id="sig-school-04",
                qualified_signal_id=4,
                raw_signal_id="raw-4",
                signal_type="general",
                importance="HIGH",
                confidence=1.0,
                summary="Parent meeting scheduled Friday at Science school",
                processing_path="RULE_ENGINE",
                llm_model_used="none",
                contract_json=json.dumps(mock_contract_school)
            )
            db.add(sig_school)
            db.commit()

            FyiAgent.process_all_understood_signals(db)
            fyi_school = db.query(FyiEvent).filter(FyiEvent.event_type == "SCHOOL_NOTICE").first()
            assert fyi_school is not None
            assert fyi_school.category == "FAMILY"
            assert fyi_school.importance == "HIGH"
            logger.success("Test Case 4: Passed.")

        logger.success("ALL LOCAL FYI AGENT TESTS PASSED SUCCESSFULLY!")

    finally:
        # Cleanup
        db.query(FyiEvent).delete()
        db.query(UnderstoodSignal).delete()
        db.commit()
        db.close()


if __name__ == "__main__":
    run_fyi_agent_tests()
