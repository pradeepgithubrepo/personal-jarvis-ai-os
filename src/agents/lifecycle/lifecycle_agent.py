import datetime
from typing import Any, Optional
from loguru import logger

from src.agents.stubs.base_agent_stub import BaseAgentStub, AgentResult
from src.agents.todo.todo_agent import TodoAgent


class LifecycleAgent(BaseAgentStub):
    """
    Lifecycle Agent — Engine to manage lifecycle events across domains (Health, Insurance, Warranty, etc.).
    Promotes qualifying items to ToDos using the existing ToDo creation and reflection pipeline.
    """

    @property
    def agent_name(self) -> str:
        return "lifecycle_agent"

    def process(self, contract: dict) -> AgentResult:
        """
        Synchronous processing stub required by BaseAgentStub interface.
        """
        logger.info("lifecycle_agent: process() called")
        return AgentResult(
            agent_name=self.agent_name,
            status="COMPLETED",
            message="Lifecycle agent execution complete.",
        )
    def _determine_assignment(self, title: str, description: str) -> str:
        text = (title + " " + (description or "")).lower()
        
        # School Keywords
        school_keywords = [
            "school", "preschool", "daycare", "parent meeting", "homework", 
            "school fees", "school events", "parent teacher meeting", "parent-teacher meeting"
        ]
        if any(k in text for k in school_keywords):
            return "BOTH"
            
        # Children / Kids Keywords
        kids_keywords = [
            "charan", "chainicka", "child", "kids", "children", "vaccination", 
            "medical appointment", "shopping for children", "child activities",
            "family activity", "family activities", "parent feedback"
        ]
        if any(k in text for k in kids_keywords):
            return "BOTH"
            
        return "PRADEEP"

    def process_active_items(self, supabase_client: Any, today: Optional[datetime.date] = None) -> dict:
        """
        Load all active lifecycle items, check reminder offsets, promote qualifying
        items to To-Dos, and update schedule offsets/status.
        """
        if today is None:
            today = datetime.date.today()

        logger.info(f"lifecycle_agent: Running execution for date={today}")

        try:
            # 1. Fetch all ACTIVE lifecycle items
            res = (
                supabase_client
                .table("lifecycle_items")
                .select("*")
                .eq("status", "ACTIVE")
                .execute()
            )
            items = res.data or []
            logger.info(f"lifecycle_agent: Found {len(items)} active lifecycle items.")
        except Exception as e:
            logger.error(f"lifecycle_agent: Failed to fetch active lifecycle items: {e}")
            return {"status": "FAILED", "error": str(e), "promoted_count": 0}

        promoted_count = 0
        todo_agent = TodoAgent()

        for item in items:
            item_id = item["id"]
            title = item["title"]
            domain = item["domain"]
            next_occ_str = item["next_occurrence_date"]
            offset_days = item.get("reminder_offset_days") or 0
            last_promoted_str = item.get("last_promoted_date")

            try:
                next_occ_date = datetime.datetime.strptime(next_occ_str, "%Y-%m-%d").date()
            except Exception as e:
                logger.error(f"lifecycle_agent: Invalid next_occurrence_date format for item {item_id}: {e}")
                continue

            # Idempotency check: Skip if already promoted today
            if last_promoted_str:
                try:
                    last_promoted_date = datetime.datetime.strptime(last_promoted_str, "%Y-%m-%d").date()
                    if last_promoted_date == today:
                        logger.info(f"lifecycle_agent: Item {item_id} ({title}) already promoted today. Skipping.")
                        continue
                except Exception as e:
                    logger.warning(f"lifecycle_agent: Invalid last_promoted_date format for item {item_id}: {e}")

            # Check if today is within the reminder window (today >= next_occurrence_date - offset_days)
            trigger_date = next_occ_date - datetime.timedelta(days=offset_days)
            if today >= trigger_date:
                logger.info(f"lifecycle_agent: Promoting item {item_id} ({title}) to ToDo...")
                
                # 2. Create ToDo task row
                due_datetime = datetime.datetime.combine(next_occ_date, datetime.time.min).replace(
                    tzinfo=datetime.timezone.utc
                ).isoformat()

                desc = item.get("description") or f"Automatically promoted from {domain} Lifecycle event."
                task_row = {
                    "title": title,
                    "description": desc,
                    "status": "OPEN",
                    "priority": "HIGH",
                    "due_datetime": due_datetime,
                    "notification_profile": "STANDARD",
                    "source_type": "AUTO_GENERATED",
                    "created_by": "JARVIS",
                    "assigned_to": self._determine_assignment(title, desc),
                    "lifecycle_item_id": item_id,
                }

                try:
                    # Insert task
                    task_res = supabase_client.table("tasks").insert(task_row).execute()
                    if not task_res.data:
                        raise ValueError("Failed to insert task.")
                    
                    created_task = task_res.data[0]
                    created_task_id = created_task["id"]
                    logger.info(f"lifecycle_agent: Created task {created_task_id} for item {item_id}")

                    # Run reflection pipeline on the task
                    try:
                        todo_agent._reflect_on_created_task(supabase_client, created_task)
                    except Exception as reflect_err:
                        logger.warning(f"lifecycle_agent: Reflection failed for task {created_task_id}: {reflect_err}")

                    # 3. Update Lifecycle Item state
                    updates = {
                        "last_promoted_date": today.isoformat(),
                        "last_todo_id": created_task_id,
                        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
                    }

                    if item["schedule_type"] == "RECURRING_DAYS":
                        interval = item.get("interval_days") or 365
                        new_next_occ = next_occ_date + datetime.timedelta(days=interval)
                        updates["next_occurrence_date"] = new_next_occ.isoformat()
                        logger.info(f"lifecycle_agent: Rescheduled item {item_id} to {new_next_occ}")
                    else:
                        updates["status"] = "COMPLETED"
                        logger.info(f"lifecycle_agent: Completed one-time item {item_id}")

                    supabase_client.table("lifecycle_items").update(updates).eq("id", item_id).execute()
                    promoted_count += 1

                except Exception as promote_err:
                    logger.error(f"lifecycle_agent: Error promoting item {item_id}: {promote_err}")
                    continue

        return {"status": "SUCCESS", "promoted_count": promoted_count}
