# tests/test_daily_brief_agent.py

import sys
import os
from unittest.mock import patch, MagicMock
from loguru import logger

# Add root folder to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.db.database import initialize_database, SessionLocal
from storage.models.todo_item import TodoItem
from storage.models.fyi_event import FyiEvent
from storage.models.fact import Fact
from storage.models.daily_brief import DailyBrief
from services.daily_brief_agent import DailyBriefAgent


def run_daily_brief_agent_tests():
    logger.info("Initializing database for Daily Brief Agent tests...")
    initialize_database()

    db = SessionLocal()
    try:
        # Clear old events
        db.query(TodoItem).delete()
        db.query(FyiEvent).delete()
        db.query(Fact).delete()
        db.query(DailyBrief).delete()
        db.commit()

        # Mock Supabase Repo writes to avoid network requests during agent tests
        mock_supabase_repo = MagicMock()
        mock_supabase_repo.store_daily_brief.return_value = True

        with patch("src.agents.daily_brief.repository.SupabaseRepo", mock_supabase_repo):

            # Scenario 1: Brief has Actions, Financial, and Family sections
            logger.info("Scenario 1: Testing structured Morning Brief rendering...")
            todo_1 = TodoItem(title="Pay credit card", category="FINANCIAL", priority="HIGH", status="OPEN", source_agent="Test")
            todo_2 = TodoItem(title="Submit KYC", category="GENERAL", priority="MEDIUM", status="OPEN", source_agent="Test")
            fyi_salary = FyiEvent(event_type="SALARY_CREDITED", category="FINANCIAL", title="Salary credited", importance="MEDIUM", status="UNREAD")
            fyi_school = FyiEvent(event_type="SCHOOL_NOTICE", category="FAMILY", title="PTM Meeting scheduled", importance="HIGH", status="UNREAD")
            
            db.add_all([todo_1, todo_2, fyi_salary, fyi_school])
            db.commit()

            morning_id = DailyBriefAgent.generate_briefs(db)["morning_brief_id"]
            brief = db.get(DailyBrief, morning_id)
            assert brief is not None
            assert "## Critical Actions" in brief.content
            assert "## Financial Updates" in brief.content
            assert "## Family Updates" in brief.content
            assert "Salary credited" in brief.content
            assert "PTM Meeting scheduled" in brief.content
            logger.success("Scenario 1: Passed.")

            # Scenario 2: No Todos displays "No pending actions."
            logger.info("Scenario 2: Testing brief rendering with no open todos...")
            db.query(TodoItem).delete()
            db.commit()
            
            morning_id_2 = DailyBriefAgent.generate_briefs(db)["morning_brief_id"]
            brief_2 = db.get(DailyBrief, morning_id_2)
            assert "No pending actions." in brief_2.content, "Expected 'No pending actions.' indicator"
            logger.success("Scenario 2: Passed.")

            # Scenario 3: Highest priority items appear first
            logger.info("Scenario 3: Testing todo importance sorting...")
            todo_med = TodoItem(title="Medium Task", category="GENERAL", priority="MEDIUM", status="OPEN", source_agent="Test")
            todo_high = TodoItem(title="High Task", category="GENERAL", priority="HIGH", status="OPEN", source_agent="Test")
            db.add_all([todo_med, todo_high])
            db.commit()

            morning_id_3 = DailyBriefAgent.generate_briefs(db)["morning_brief_id"]
            brief_3 = db.get(DailyBrief, morning_id_3)
            # Find indices in content
            idx_high = brief_3.content.index("High Task")
            idx_med = brief_3.content.index("Medium Task")
            assert idx_high < idx_med, "Expected High Task to appear before Medium Task in brief output"
            logger.success("Scenario 3: Passed.")

            # Scenario 4: Archived FYIs excluded
            logger.info("Scenario 4: Testing exclusion of archived items...")
            db.query(FyiEvent).delete()
            fyi_archived = FyiEvent(event_type="SCHOOL_NOTICE", category="FAMILY", title="Old circular", importance="HIGH", status="ARCHIVED")
            db.add(fyi_archived)
            db.commit()

            morning_id_4 = DailyBriefAgent.generate_briefs(db)["morning_brief_id"]
            brief_4 = db.get(DailyBrief, morning_id_4)
            assert "Old circular" not in brief_4.content, "Expected archived FYI to be excluded from morning brief"
            logger.success("Scenario 4: Passed.")

        logger.success("ALL LOCAL DAILY BRIEF AGENT TESTS PASSED SUCCESSFULLY!")

    finally:
        # Cleanup
        db.query(TodoItem).delete()
        db.query(FyiEvent).delete()
        db.query(Fact).delete()
        db.query(DailyBrief).delete()
        db.commit()
        db.close()


if __name__ == "__main__":
    run_daily_brief_agent_tests()
