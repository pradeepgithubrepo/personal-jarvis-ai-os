# verify_daily_brief.py
import sys
import os
import json
from datetime import datetime
from unittest.mock import patch, MagicMock
from loguru import logger

# Add root folder to python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import dotenv
dotenv.load_dotenv()

from storage.db.database import initialize_database, SessionLocal
from storage.models.todo_item import TodoItem
from storage.models.fyi_event import FyiEvent
from storage.models.fact import Fact
from storage.models.daily_brief import DailyBrief
from services.daily_brief_agent import DailyBriefAgent

def verify():
    logger.info("Initializing database...")
    initialize_database()

    db = SessionLocal()
    try:
        from storage.models.financial_event import FinancialEvent
        from storage.models.financial_fact import FinancialFact
        from datetime import timedelta

        # Clear test data
        db.query(TodoItem).delete()
        db.query(FyiEvent).delete()
        db.query(Fact).delete()
        db.query(DailyBrief).delete()
        db.query(FinancialFact).delete()
        db.query(FinancialEvent).delete()
        db.commit()

        # Insert Mock Data
        # Overdue todo
        overdue_todo = TodoItem(
            title="Overdue Test Todo",
            category="GENERAL",
            priority="HIGH",
            status="OPEN",
            due_date=datetime.utcnow() - timedelta(days=2),
            source_agent="Verifier"
        )
        # Due today todo
        today_todo = TodoItem(
            title="Today Test Todo",
            category="GENERAL",
            priority="HIGH",
            status="OPEN",
            due_date=datetime.utcnow(),
            source_agent="Verifier"
        )
        # Upcoming todo
        upcoming_todo = TodoItem(
            title="Upcoming Test Todo",
            category="GENERAL",
            priority="MEDIUM",
            status="OPEN",
            due_date=datetime.utcnow() + timedelta(days=3),
            source_agent="Verifier"
        )

        fyi = FyiEvent(event_type="TEST_FYI", category="SYSTEM", title="Test Verification FYI", importance="HIGH", status="UNREAD")
        fact = Fact(fact_type="TEST_FACT", fact_value={"key": "val"}, status="VERIFIED", confidence=1.0, source_agent="Verifier")
        
        # Financial Event & Fact yesterday
        yesterday_date = (datetime.utcnow() - timedelta(days=1)).date()
        fin_event = FinancialEvent(id=999, title="Mock Coffee", amount=150.0, transaction_type="debit", source_signal_id="sig_test")
        fin_fact = FinancialFact(
            id="fact-999",
            financial_event_id=999,
            fact_type="EXPENSE_EVENT",
            amount=150.0,
            event_date=yesterday_date,
            category="FOOD_DINING"
        )

        db.add_all([overdue_todo, today_todo, upcoming_todo, fyi, fact, fin_event, fin_fact])
        db.commit()

        # Mock Supabase
        mock_supabase_repo = MagicMock()
        mock_supabase_repo.store_daily_brief.return_value = True

        with patch("src.agents.daily_brief.repository.SupabaseRepo", mock_supabase_repo):
            # 1. Generate Morning Brief (which saves to SQLite and mirrors to Supabase)
            logger.info("Generating Morning Brief...")
            brief_ids = DailyBriefAgent.generate_briefs(db)
            morning_id = brief_ids["morning_brief_id"]

            # 2. Read back from SQLite
            brief = db.get(DailyBrief, morning_id)
            if not brief:
                logger.error("Failed to read brief back from SQLite database.")
                print("FAIL")
                sys.exit(1)

            # 3. Validate counts and properties
            logger.info(f"Loaded generated brief content:\n{brief.content}")
            logger.info(f"SQLite Todo Count: {brief.todo_count}, FYI Count: {brief.fyi_count}, Fact Count: {brief.fact_count}")

            # Verify SQLite values
            # todo_count in morning_brief: len(context["today_tasks"]) + len(context["overdue_tasks"])
            assert brief.todo_count == 2, f"Expected todo count 2, got {brief.todo_count}"
            assert brief.fyi_count == 1, f"Expected fyi count 1, got {brief.fyi_count}"
            assert brief.fact_count == 1, f"Expected fact count 1, got {brief.fact_count}"

            # Verify payload_json contains structured context
            assert brief.payload_json is not None, "Expected payload_json to be stored."
            payload = json.loads(brief.payload_json)
            
            # Verify Enriched V2 keys
            assert "overdue_tasks" in payload, "Expected overdue_tasks in payload"
            assert "today_tasks" in payload, "Expected today_tasks in payload"
            assert "upcoming_events" in payload, "Expected upcoming_events in payload"
            assert "financial_summary" in payload, "Expected financial_summary in payload"
            assert "top_priorities" in payload, "Expected top_priorities in payload"
            assert "generation_time_ms" in payload, "Expected generation_time_ms in payload"
            assert "context_version" in payload, "Expected context_version in payload"
            
            # Verify financial summary details
            fin_sum = payload["financial_summary"]
            assert fin_sum["yesterday_spend"] == 150.0, f"Expected yesterday_spend 150.0, got {fin_sum['yesterday_spend']}"
            assert fin_sum["biggest_expense"]["merchant"] == "Unknown", f"Expected biggest_expense merchant Unknown, got {fin_sum['biggest_expense']}"
            
            # Verify top priorities
            priorities = payload["top_priorities"]
            assert len(priorities) > 0, "Expected at least one priority extracted"
            assert priorities[0]["priority_type"] == "OVERDUE_TASK", f"Expected first priority type to be OVERDUE_TASK, got {priorities[0]['priority_type']}"

            logger.info("payload_json V2 structured context successfully verified.")

            # 4. Verify Supabase save call
            mock_supabase_repo.store_daily_brief.assert_called()
            logger.info("Supabase storage sync call successfully verified.")

        logger.success("All checks passed successfully!")
        print("PASS")
        sys.exit(0)

    except Exception as e:
        logger.error(f"Verification failed: {e}")
        print("FAIL")
        sys.exit(1)
    finally:
        # Cleanup
        db.query(TodoItem).delete()
        db.query(FyiEvent).delete()
        db.query(Fact).delete()
        db.query(DailyBrief).delete()
        db.query(FinancialFact).delete()
        db.query(FinancialEvent).delete()
        db.commit()
        db.close()

if __name__ == "__main__":
    verify()
