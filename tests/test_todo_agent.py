# tests/test_todo_agent.py

import sys
import os
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from loguru import logger

# Add root folder to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import initialize_database, SessionLocal
from storage.models.todo_item import TodoItem
from storage.models.fact import Fact
from storage.models.financial_fact import FinancialFact
from storage.models.understood_signal import UnderstoodSignal
from services.todo_agent import TodoAgent


def run_todo_agent_tests():
    logger.info("Initializing database for Todo Agent tests...")
    initialize_database()

    db = SessionLocal()
    try:
        # Clear old tables
        db.query(TodoItem).delete()
        db.query(Fact).delete()
        db.query(FinancialFact).delete()
        db.query(UnderstoodSignal).delete()
        db.commit()

        # Mock Supabase Repo writes to avoid network requests
        mock_supabase_repo = MagicMock()
        mock_supabase_repo.store_todo_item.return_value = True

        with patch("services.todo_agent.SupabaseRepo", mock_supabase_repo):

            # Test Case 1: Standard Ingestion
            logger.info("Test Case 1: Ingesting a general task...")
            candidate = {
                "title": "Buy groceries",
                "category": "GENERAL",
                "priority": "MEDIUM",
                "source_agent": "SignalUnderstandingAgent",
                "source_reference": {"signal_id": "sig-1"}
            }
            todo_id_1 = TodoAgent.ingest_candidate(candidate, db)
            assert todo_id_1 is not None, "Expected todo_id"
            
            todo_1 = db.get(TodoItem, todo_id_1)
            assert todo_1 is not None
            assert todo_1.title == "Buy groceries"
            assert todo_1.status == "OPEN"
            logger.success("Test Case 1: Passed.")

            # Test Case 2: Memory Enrichment
            logger.info("Test Case 2: Testing context enrichment from FactAgent memory...")
            # Seed a vehicle fact first
            veh_fact = Fact(
                fact_type="VEHICLE",
                fact_value={"make": "Maruti Suzuki", "model": "Swift", "license_plate": "KA-03-XX-9999"},
                confidence=1.0,
                status="MANUAL_LOCK",
                source_agent="Manual",
                source_type="USER_LOCKED"
            )
            db.add(veh_fact)
            db.commit()

            candidate_veh = {
                "title": "Car servicing",
                "category": "VEHICLE",
                "source_agent": "SignalUnderstandingAgent"
            }
            todo_id_2 = TodoAgent.ingest_candidate(candidate_veh, db)
            todo_2 = db.get(TodoItem, todo_id_2)
            assert "Maruti Suzuki Swift" in todo_2.title, f"Expected enriched title, got: {todo_2.title}"
            assert "KA-03-XX-9999" in todo_2.description, "Expected license plate in description"
            logger.success("Test Case 2: Passed.")

            # Test Case 3: Priority Scoring
            logger.info("Test Case 3: Testing priority assignment rules...")
            # Proximity check (<24h)
            near_due = datetime.utcnow() + timedelta(hours=12)
            cand_near = {
                "title": "Submit document",
                "category": "GENERAL",
                "due_date": near_due.isoformat(),
                "source_agent": "SignalUnderstandingAgent"
            }
            id_near = TodoAgent.ingest_candidate(cand_near, db)
            todo_near = db.get(TodoItem, id_near)
            assert todo_near.priority == "CRITICAL", f"Expected CRITICAL priority, got: {todo_near.priority}"

            # High Risk check
            cand_bounce = {
                "title": "Loan EMI payment default alert",
                "category": "FINANCIAL",
                "source_agent": "FinancialAgent"
            }
            id_bounce = TodoAgent.ingest_candidate(cand_bounce, db)
            todo_bounce = db.get(TodoItem, id_bounce)
            assert todo_bounce.priority == "CRITICAL"
            logger.success("Test Case 3: Passed.")

            # Test Case 4: Deduplication & Priority Escalation
            logger.info("Test Case 4: Testing task deduplication and priority escalation...")
            # Re-ingest the near_due task with identical details
            id_dup = TodoAgent.ingest_candidate(cand_near, db)
            assert id_dup == id_near, "Expected duplicate task to merge and reuse ID"
            logger.success("Test Case 4: Passed.")

            # Test Case 5: Auto-completion via FinancialFacts
            logger.info("Test Case 5: Testing auto-completion from financial payment facts...")
            cand_bill = {
                "title": "Renew Acko insurance",
                "category": "INSURANCE",
                "source_agent": "SignalUnderstandingAgent"
            }
            id_bill = TodoAgent.ingest_candidate(cand_bill, db)
            todo_bill = db.get(TodoItem, id_bill)
            assert todo_bill.status == "OPEN"

            # Create a mock payment fact to Acko
            mock_payment = FinancialFact(
                fact_type="EXPENSE_EVENT",
                amount=5200.0,
                currency="INR",
                merchant_canonical="Acko",
                category="INSURANCE",
                classification_confidence=1.0,
                financial_event_id=1,
                event_date=datetime.utcnow().date()
            )
            db.add(mock_payment)
            db.commit()

            autoclosed = TodoAgent.auto_complete_tasks(db)
            assert autoclosed > 0, "Expected task to be auto-completed"
            db.refresh(todo_bill)
            assert todo_bill.status == "COMPLETED", "Task status should transition to COMPLETED"
            logger.success("Test Case 5: Passed.")

            # Test Case 6: Understood Signal Extraction
            logger.info("Test Case 6: Testing task extraction from understood signal...")
            mock_contract = {
                "classes": ["ACTION"],
                "domains": ["INSURANCE"],
                "entities": {
                    "deadlines": [{"date": (datetime.utcnow() + timedelta(days=5)).isoformat()}]
                }
            }
            mock_sig = UnderstoodSignal(
                id="sig-todo-101",
                qualified_signal_id=25,
                raw_signal_id="raw-25",
                signal_type="general",
                importance="MEDIUM",
                confidence=1.0,
                summary="Please renew Acko policy before deadline",
                processing_path="RULE_ENGINE",
                llm_model_used="none",
                contract_json=json.dumps(mock_contract)
            )
            db.add(mock_sig)
            db.commit()

            metrics = TodoAgent.process_all_understood_signals(db)
            assert metrics["todos_created"] > 0
            
            # Verify the task was created
            todos = db.query(TodoItem).filter(TodoItem.source_reference == {"signal_id": "sig-todo-101"}).all()
            assert len(todos) == 1
            assert todos[0].category == "INSURANCE"
            logger.success("Test Case 6: Passed.")

        logger.success("ALL LOCAL TODO AGENT TESTS PASSED SUCCESSFULLY!")

    finally:
        # Cleanup
        db.query(TodoItem).delete()
        db.query(Fact).delete()
        db.query(FinancialFact).delete()
        db.query(UnderstoodSignal).delete()
        db.commit()
        db.close()


if __name__ == "__main__":
    run_todo_agent_tests()
