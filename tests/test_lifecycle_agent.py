import datetime
import unittest
from unittest.mock import MagicMock, patch

from src.agents.lifecycle.lifecycle_agent import LifecycleAgent


class TestLifecycleAgent(unittest.TestCase):
    def setUp(self):
        self.agent = LifecycleAgent()
        self.mock_client = MagicMock()

    @patch("src.agents.lifecycle.lifecycle_agent.TodoAgent")
    def test_promotion_logic_and_rescheduling(self, mock_todo_agent_class):
        # Setup mocks
        mock_todo_agent = mock_todo_agent_class.return_value
        mock_todo_agent._reflect_on_created_task.return_value = {"status": "SUCCESS"}

        today = datetime.date(2026, 7, 19)

        # Mock active items:
        # 1. Health checkup due today, offset 0 -> promote, recurring 365 days
        # 2. Dental checkup due tomorrow, offset 1 -> promote, one-time (ONCE)
        # 3. Vaccine due next week, offset 0 -> do NOT promote
        # 4. Cholesterol due today but already promoted today -> do NOT promote
        active_items = [
            {
                "id": "item-1",
                "domain": "HEALTH_PLANNER",
                "title": "Annual health check-up",
                "description": "Yearly health screening",
                "schedule_type": "RECURRING_DAYS",
                "interval_days": 365,
                "next_occurrence_date": "2026-07-19",
                "reminder_offset_days": 0,
                "last_promoted_date": None,
                "status": "ACTIVE",
            },
            {
                "id": "item-2",
                "domain": "HEALTH_PLANNER",
                "title": "Dental cleaning",
                "description": "Routine dental clean",
                "schedule_type": "ONCE",
                "interval_days": None,
                "next_occurrence_date": "2026-07-20",
                "reminder_offset_days": 1,
                "last_promoted_date": None,
                "status": "ACTIVE",
            },
            {
                "id": "item-3",
                "domain": "HEALTH_PLANNER",
                "title": "Cholesterol consult",
                "description": "Doctor checkup",
                "schedule_type": "ONCE",
                "interval_days": None,
                "next_occurrence_date": "2026-07-26",
                "reminder_offset_days": 0,
                "last_promoted_date": None,
                "status": "ACTIVE",
            },
            {
                "id": "item-4",
                "domain": "HEALTH_PLANNER",
                "title": "Charan vaccination",
                "description": "Flu shot",
                "schedule_type": "RECURRING_DAYS",
                "interval_days": 180,
                "next_occurrence_date": "2026-07-19",
                "reminder_offset_days": 0,
                "last_promoted_date": "2026-07-19",
                "status": "ACTIVE",
            },
        ]

        # Mock select query returning active items
        select_mock = self.mock_client.table.return_value.select.return_value.eq.return_value.execute
        select_mock.return_value.data = active_items

        # Mock task insert query
        inserted_tasks = []

        def mock_insert(task_row):
            task_id = f"task-for-{task_row['lifecycle_item_id']}"
            created_task = {"id": task_id, **task_row}
            inserted_tasks.append(created_task)
            
            # Return a mock executing pipeline
            exec_mock = MagicMock()
            exec_mock.execute.return_value.data = [created_task]
            return exec_mock

        self.mock_client.table.return_value.insert.side_effect = mock_insert

        # Mock update query for lifecycle_items updates
        updated_items = {}

        def mock_update(updates):
            # Capture updates for assertions
            eq_mock = MagicMock()
            
            def mock_eq(col, val):
                updated_items[val] = updates
                return MagicMock()
                
            eq_mock.eq.side_effect = mock_eq
            return eq_mock

        self.mock_client.table.return_value.update.side_effect = mock_update

        # Execute
        result = self.agent.process_active_items(self.mock_client, today=today)

        # Assertions
        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["promoted_count"], 2)  # item-1 and item-2 should be promoted

        # Verify inserted tasks
        self.assertEqual(len(inserted_tasks), 2)
        task_1 = next(t for t in inserted_tasks if t["lifecycle_item_id"] == "item-1")
        self.assertEqual(task_1["title"], "Annual health check-up")
        self.assertEqual(task_1["priority"], "HIGH")
        self.assertEqual(task_1["due_datetime"], "2026-07-19T00:00:00+00:00")

        task_2 = next(t for t in inserted_tasks if t["lifecycle_item_id"] == "item-2")
        self.assertEqual(task_2["title"], "Dental cleaning")
        self.assertEqual(task_2["priority"], "HIGH")
        self.assertEqual(task_2["due_datetime"], "2026-07-20T00:00:00+00:00")

        # Verify lifecycle item updates
        self.assertIn("item-1", updated_items)
        up_1 = updated_items["item-1"]
        self.assertEqual(up_1["last_promoted_date"], "2026-07-19")
        self.assertEqual(up_1["next_occurrence_date"], "2027-07-19")  # 2026-07-19 + 365 days
        self.assertEqual(up_1["last_todo_id"], "task-for-item-1")

        self.assertIn("item-2", updated_items)
        up_2 = updated_items["item-2"]
        self.assertEqual(up_2["last_promoted_date"], "2026-07-19")
        self.assertEqual(up_2["status"], "COMPLETED")
        self.assertEqual(up_2["last_todo_id"], "task-for-item-2")

        # Ensure item-3 and item-4 were NOT updated or promoted
        self.assertNotIn("item-3", updated_items)
        self.assertNotIn("item-4", updated_items)


if __name__ == "__main__":
    unittest.main()
