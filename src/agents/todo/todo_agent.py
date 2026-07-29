"""
src/agents/todo/todo_agent.py

Real implementation of the To-Do Agent V1.
Utilizes the local LLM (via LLMClient) to perform:
- Task Identification (CREATE_TASK, IGNORE, MERGE_WITH_EXISTING)
- Semantic Deduplication against open tasks
- Text Rationalization (turning messy signals into clean tasks)
- Task Creation in the Supabase tasks table

Owner: To-Do Agent
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from loguru import logger

from src.agents.stubs.base_agent_stub import BaseAgentStub, AgentResult
from intelligence.llm_client import LLMClient


class TodoAgent(BaseAgentStub):
    """
    To-Do Agent V1 — Reasoning Agent.
    """

    def __init__(self, provider: str = None, model: str = None):
        self.provider = provider
        self.model = model
        self.llm_client = LLMClient(provider=self.provider, model=self.model)

    @property
    def agent_name(self) -> str:
        return "todo_agent"

    def process(self, contract: dict) -> AgentResult:
        """
        Synchronous processing stub required by BaseAgentStub interface.
        Note: The dispatch layer now writes PENDING pointers; the actual
        ingestion is executed asynchronously via process_pending_routes().
        """
        summary = contract.get("summary", "")
        logger.info(f"todo_agent: process() called for stub | summary={summary!r}")
        return AgentResult(
            agent_name=self.agent_name,
            status="STUB_ACCEPTED",
            message="To-Do Agent registered route decision. Awaiting pull processing.",
            output={"summary": summary},
        )
    def _determine_assignment(self, title: str, description: str, device_id: str | None) -> str:
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
            
        # Device Tracing
        if device_id:
            dev_lower = device_id.lower()
            if "shobana" in dev_lower:
                return "SHOBANA"
            elif "pradeep" in dev_lower:
                return "PRADEEP"
                
        return "PRADEEP"

    def process_pending_routes(self, supabase_client: Any) -> None:
        """
        Query PENDING routes for todo_agent in Supabase, reason over them
        using the local LLM, deduplicate, and write/merge tasks.
        """
        if supabase_client is None:
            logger.error("todo_agent: Supabase client is required for pull worker.")
            return

        logger.info("todo_agent: Fetching pending signal routes...")
        try:
            # 1. Fetch PENDING routes for todo_agent
            routes_res = (
                supabase_client
                .table("signal_routes")
                .select("id, understood_signal_id, route_reason, route_confidence")
                .eq("agent_name", "todo_agent")
                .eq("route_status", "PENDING")
                .execute()
            )
            pending_routes = routes_res.data or []
            logger.info(f"todo_agent: Found {len(pending_routes)} pending route(s).")
        except Exception as e:
            logger.error(f"todo_agent: Failed to fetch pending routes: {e}")
            return

        if not pending_routes:
            return

        # 2. Fetch all current OPEN or IN_PROGRESS tasks to support deduplication
        try:
            tasks_res = (
                supabase_client
                .table("tasks")
                .select("id, title, description")
                .in_("status", ["OPEN", "IN_PROGRESS"])
                .execute()
            )
            open_tasks = tasks_res.data or []
            logger.info(f"todo_agent: Loaded {len(open_tasks)} open tasks for deduplication.")
        except Exception as e:
            logger.warning(f"todo_agent: Failed to fetch open tasks (proceeding without deduplication context): {e}")
            open_tasks = []

        # 3. Process each pending route
        for route in pending_routes:
            route_id = route["id"]
            us_id = route["understood_signal_id"]

            logger.info(f"todo_agent: Processing route {route_id} (signal {us_id})...")

            # Fetch the parent understood signal and raw message details
            try:
                us_res = (
                    supabase_client
                    .table("understood_signals")
                    .select("summary, contract_json, device_id, qualified_signals(message)")
                    .eq("id", us_id)
                    .limit(1)
                    .execute()
                )
                if not us_res.data:
                    raise ValueError(f"Understood signal {us_id} not found.")

                us_record = us_res.data[0]
                contract = us_record.get("contract_json") or {}
                device_id = us_record.get("device_id")
                
                # Retrieve raw message from foreign key join to qualified_signals
                qs = us_record.get("qualified_signals") or {}
                raw_message = qs.get("message") or us_record.get("summary") or ""
            except Exception as e:
                logger.error(f"todo_agent: Failed to load context for route {route_id}: {e}")
                self._update_route_status(supabase_client, route_id, "FAILED", error_message=str(e))
                continue

            # Filter open tasks for this specific signal to prevent context leakage
            filtered_open_tasks = self._filter_candidate_tasks(raw_message, contract, open_tasks)

            # Reason and decide using Fallback LLM Hierarchy
            try:
                decision_data = self._reason_over_task(raw_message, contract, filtered_open_tasks)
                decision = decision_data.get("decision", "CREATE_TASK")
                rationale = decision_data.get("rationale", "")
                
                logger.info(f"todo_agent: LLM Decision={decision} | rationale={rationale!r}")

                if decision == "CREATE_TASK":
                    # Create a new clean task in tasks table
                    title_val = decision_data.get("title") or contract.get("summary") or "New Task"
                    desc_val = decision_data.get("description") or raw_message
                    task_row = {
                        "title": title_val,
                        "description": desc_val,
                        "status": "OPEN",
                        "priority": decision_data.get("priority") or "MEDIUM",
                        "due_datetime": decision_data.get("due_datetime") or contract.get("type_specific", {}).get("due_date"),
                        "notification_profile": decision_data.get("notification_profile") or "STANDARD",
                        "source_type": "AUTO_GENERATED",
                        "route_id": route_id,
                        "created_by": "JARVIS",
                        "assigned_to": self._determine_assignment(title_val, desc_val, device_id),
                    }
                    res = supabase_client.table("tasks").insert(task_row).execute()
                    logger.info(f"todo_agent: Created task: {task_row['title']!r}")
                    if res.data:
                        reflect_res = self._reflect_on_created_task(supabase_client, res.data[0])
                        if reflect_res.get("status") == "UPDATED":
                            open_tasks.append({
                                "id": res.data[0]["id"],
                                "title": reflect_res.get("title") or res.data[0]["title"],
                                "description": reflect_res.get("description") or res.data[0]["description"]
                            })
                        elif reflect_res.get("status") == "MERGED":
                            pass
                        else:
                            open_tasks.append({
                                "id": res.data[0]["id"],
                                "title": res.data[0]["title"],
                                "description": res.data[0]["description"]
                            })

                elif decision == "MERGE_WITH_EXISTING" and open_tasks:
                    matched_id = decision_data.get("matched_task_id")
                    # If matched_id is valid, merge signal into existing task
                    if matched_id and any(t["id"] == matched_id for t in open_tasks):
                        # Fetch current description to append new source notice
                        existing_task = next(t for t in open_tasks if t["id"] == matched_id)
                        old_desc = existing_task.get("description") or ""
                        append_txt = f"\n\n[System Update]: Semantic duplicate signal received. Merged route_id: {route_id}. Raw details: {raw_message}"
                        new_desc = old_desc + append_txt
                        
                        supabase_client.table("tasks").update({"description": new_desc, "updated_at": _now()}).eq("id", matched_id).execute()
                        logger.info(f"todo_agent: Merged route {route_id} into task {matched_id}")
                    else:
                        # Fallback to create task if matched_id is invalid
                        logger.warning(f"todo_agent: Matched task ID {matched_id} not found in open tasks. Falling back to CREATE_TASK.")
                        title_val = decision_data.get("title") or contract.get("summary") or "New Task"
                        desc_val = decision_data.get("description") or raw_message
                        task_row = {
                            "title": title_val,
                            "description": desc_val,
                            "status": "OPEN",
                            "priority": decision_data.get("priority") or "MEDIUM",
                            "due_datetime": decision_data.get("due_datetime") or contract.get("type_specific", {}).get("due_date"),
                            "notification_profile": decision_data.get("notification_profile") or "STANDARD",
                            "source_type": "AUTO_GENERATED",
                            "route_id": route_id,
                            "created_by": "JARVIS",
                            "assigned_to": self._determine_assignment(title_val, desc_val, device_id),
                        }
                        res = supabase_client.table("tasks").insert(task_row).execute()
                        logger.info(f"todo_agent: Created task (fallback): {task_row['title']!r}")
                        if res.data:
                            reflect_res = self._reflect_on_created_task(supabase_client, res.data[0])
                            if reflect_res.get("status") == "UPDATED":
                                open_tasks.append({
                                    "id": res.data[0]["id"],
                                    "title": reflect_res.get("title") or res.data[0]["title"],
                                    "description": reflect_res.get("description") or res.data[0]["description"]
                                })
                            elif reflect_res.get("status") == "MERGED":
                                pass
                            else:
                                open_tasks.append({
                                    "id": res.data[0]["id"],
                                    "title": res.data[0]["title"],
                                    "description": res.data[0]["description"]
                                })

                else:
                    logger.info(f"todo_agent: Signal route {route_id} classified as IGNORE.")

                # Mark route as successfully completed
                self._update_route_status(supabase_client, route_id, "COMPLETED")

            except Exception as e:
                logger.error(f"todo_agent: Failed to execute decision for route {route_id}: {e}")
                self._update_route_status(supabase_client, route_id, "FAILED", error_message=str(e))

    def _reflect_on_created_task(self, supabase_client: Any, task: dict) -> dict:
        """
        Runs a reflection prompt using Gemini/Mistral over a newly created task
        to sense check the title and description, update the title/description if needed,
        and perform deduplication/merging against other open/in-progress tasks.
        Returns the final state of the task (or None if it was deleted/merged).
        """
        task_id = task["id"]
        logger.info(f"todo_agent: Running reflection pattern for task {task_id}...")

        try:
            # Fetch all OTHER open tasks
            open_res = (
                supabase_client
                .table("tasks")
                .select("id, title, description")
                .in_("status", ["OPEN", "IN_PROGRESS"])
                .neq("id", task_id)
                .execute()
            )
            other_tasks = open_res.data or []
        except Exception as e:
            logger.warning(f"todo_agent: Reflection failed to fetch other open tasks: {e}")
            other_tasks = []

        prompt = f"""
You are the Todo Reflection Agent. Your job is to verify, clarify, and deduplicate a newly added task.

Newly Added Task:
- ID: {task_id}
- Title: "{task['title']}"
- Description: "{task['description']}"

Currently Open Tasks:
{json.dumps(other_tasks, indent=2)}

Instructions:
1. **Title Sense Check**:
   Ensure the title is concise, clear, and starts with a strong imperative action verb (e.g., "Pay Electricity Bill" instead of "Electricity charges due", or "Schedule Doctor Appointment" instead of "Doctor checkup"). If the title needs improvement, provide the "updated_title".
   If the description can be cleaned up or formatted better, provide "updated_description". Otherwise, keep the original description.

2. **Deduplication Check**:
   Compare the newly added task against the "Currently Open Tasks" list.
   If the newly added task is a duplicate or a follow-up about the same topic, action, policy renewal, or utility bill that is already covered by an existing open task in the list, you MUST flag it as a duplicate:
   - Set "is_duplicate" to true.
   - Set "matched_task_id" to the ID of the existing task from the list.
   - Provide a short "matched_rationale".
   If it is not a duplicate, set "is_duplicate" to false and "matched_task_id" to null.

You MUST return a raw JSON object ONLY, conforming EXACTLY to this schema (no surrounding markdown code blocks, no backticks, just raw JSON):
{{
  "is_duplicate": boolean,
  "matched_task_id": "string_or_null",
  "matched_rationale": "string_or_null",
  "updated_title": "string",
  "updated_description": "string"
}}
"""
        try:
            res_text = ""
            try:
                # Primary: Gemini
                res_text = self.llm_client.ask(prompt, provider="gemini")
            except Exception as gemini_err:
                logger.warning(f"todo_agent: Reflection Gemini call failed: {gemini_err}. Trying Mistral...")
                res_text = self.llm_client.ask(prompt, provider="mistral")

            # Clean JSON markers
            res_text = res_text.strip()
            if res_text.startswith("```json"):
                res_text = res_text[7:]
            if res_text.endswith("```"):
                res_text = res_text[:-3]
            res_text = res_text.strip()

            decision = json.loads(res_text)
            is_dup = decision.get("is_duplicate") or False
            matched_id = decision.get("matched_task_id")
            updated_title = decision.get("updated_title") or task["title"]
            updated_desc = decision.get("updated_description") or task["description"]

            if is_dup and matched_id and any(t["id"] == matched_id for t in other_tasks):
                # We found a duplicate! Delete the new task
                supabase_client.table("tasks").delete().eq("id", task_id).execute()
                logger.info(f"todo_agent: Reflection deleted duplicate task {task_id} (matched with {matched_id})")

                # Merge description into existing task
                existing = next(t for t in other_tasks if t["id"] == matched_id)
                old_desc = existing.get("description") or ""
                append_txt = f"\n\n[System Update - Reflection Deduplication]: Merged duplicate task. Original Details: {task.get('description')}"
                new_desc = old_desc + append_txt
                supabase_client.table("tasks").update({"description": new_desc, "updated_at": _now()}).eq("id", matched_id).execute()
                logger.info(f"todo_agent: Reflection merged description into task {matched_id}")
                return {"status": "MERGED", "matched_task_id": matched_id}
            else:
                # Update task with clean title/description
                updates = {}
                if updated_title != task["title"]:
                    updates["title"] = updated_title
                    logger.info(f"todo_agent: Reflection updating title: {task['title']!r} -> {updated_title!r}")
                if updated_desc != task["description"]:
                    updates["description"] = updated_desc

                if updates:
                    updates["updated_at"] = _now()
                    supabase_client.table("tasks").update(updates).eq("id", task_id).execute()
                return {"status": "UPDATED", "title": updated_title, "description": updated_desc}
        except Exception as e:
            logger.error(f"todo_agent: Reflection pattern failed for task {task_id}: {e}")
            return {"status": "ERROR", "error": str(e)}

    def _reason_over_task(self, raw_message: str, contract: dict, open_tasks: list[dict]) -> dict:
        """
        Invokes local LLM with prompt to decide task classification, rationalization,
        and deduplication. Returns parsed structured JSON.
        """
        # Format open tasks list for context
        open_tasks_str = json.dumps([{"id": t["id"], "title": t["title"], "description": t["description"]} for t in open_tasks], indent=2)

        prompt = f"""
Analyze the incoming signal and classify it into exactly one of three decisions:
1. "CREATE_TASK" - If the signal indicates a new actionable task for the user (e.g. bills due, homework assignments, expiring renewals).
2. "MERGE_WITH_EXISTING" - If the signal represents a semantic duplicate of an already existing open task.
3. "IGNORE" - If the signal is not actionable, is purely informational noise, or has no task potential.

Incoming Signal Text:
"{raw_message}"

Signal Context Contract:
{json.dumps(contract, indent=2)}

Currently Open Tasks:
{open_tasks_str}

CRITICAL DEDUPLICATION RULE:
- Check the "Currently Open Tasks" list very carefully.
- If the incoming signal is about the same policy renewal, the same utility bill, the same purifier complaint, the same service request ID, or the same chore/topic that is already listed in the open tasks, you MUST select "MERGE_WITH_EXISTING" and provide the "matched_task_id".
- Do NOT create a new task (CREATE_TASK) for a duplicate or follow-up notification of an existing task. This is vital to prevent task list clutter.

Instructions:
- If CREATE_TASK:
  * Rationalize the title. Turn messy inputs into clean, human-oriented, imperative task titles starting with a strong action verb (e.g., "Pay TNEB Electricity Bill" instead of "Electricity charges Rs.2527 due on 27-May", or "Renew Bike Insurance" instead of "Your insurance expires tomorrow").
  * Specify priority ("LOW", "MEDIUM", "HIGH", "URGENT").
  * Specify notification_profile ("NONE", "STANDARD", "IMPORTANT", "CRITICAL").
  * Parse due_datetime from due dates in ISO format.
- If MERGE_WITH_EXISTING:
  * Identify which existing task matches by providing its "matched_task_id" from the list of open tasks.
- If IGNORE:
  * Rationalize why it is ignored in the "rationale".

You MUST return a raw JSON object ONLY, conforming EXACTLY to this schema (no surrounding markdown code blocks, no backticks, just raw JSON):
{{
  "decision": "CREATE_TASK | IGNORE | MERGE_WITH_EXISTING",
  "rationale": "short explanation of your reasoning",
  "title": "Clean Task Title (only if CREATE_TASK)",
  "description": "Short summary description (only if CREATE_TASK)",
  "priority": "LOW | MEDIUM | HIGH | URGENT",
  "due_datetime": "ISO_TIMESTAMP or null",
  "notification_profile": "NONE | STANDARD | IMPORTANT | CRITICAL",
  "matched_task_id": "UUID_OF_MATCHED_TASK_IF_MERGE"
}}
"""
        try:
            raw_response = self.llm_client.ask(prompt)
            # Remove any markdown backticks code fences if generated by the LLM
            clean_res = raw_response.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(clean_res)
            return parsed
        except Exception as e:
            logger.warning(f"todo_agent: LLM reasoning failed: {e}. Falling back to deterministic transformation.")
            
            # Deterministic Fallback if LLM fails
            summary = contract.get("summary") or raw_message[:50]
            due_date = contract.get("type_specific", {}).get("due_date")
            priority = "HIGH" if contract.get("importance", 0.0) >= 0.8 else "MEDIUM"
            
            return {
                "decision": "CREATE_TASK",
                "rationale": "Fallback triggered due to parser error",
                "title": f"Review Alert: {summary}",
                "description": raw_message,
                "priority": priority,
                "due_datetime": due_date,
                "notification_profile": "STANDARD"
            }

    def _filter_candidate_tasks(self, raw_message: str, contract: dict, open_tasks: list[dict], max_candidates: int = 5) -> list[dict]:
        """
        Pre-filter open tasks to only include those that are semantically or keyword-wise
        related to the incoming signal. This prevents the LLM from getting distracted by
        hundreds of unrelated open tasks.
        """
        stop_words = {
            "the", "a", "an", "and", "or", "but", "if", "then", "else", "to", "for", "of", "in", "on", "at", "by", 
            "from", "with", "about", "against", "between", "into", "through", "during", "before", "after", "above", 
            "below", "up", "down", "out", "off", "over", "under", "again", "further", "once", "here", "there", 
            "when", "where", "why", "how", "all", "any", "both", "each", "few", "more", "most", "other", "some", 
            "such", "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very", "s", "t", "can", "will", 
            "just", "don", "should", "now", "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", 
            "your", "yours", "yourself", "yourselves", "he", "him", "his", "himself", "she", "her", "hers", 
            "herself", "it", "its", "itself", "they", "them", "their", "theirs", "themselves", "what", "which", 
            "who", "whom", "this", "that", "these", "those", "am", "is", "are", "was", "were", "be", "been", "being", 
            "have", "has", "had", "having", "do", "does", "did", "doing", "would", "should", "could", "ought",
            "please", "dear", "customer", "team", "your", "our", "us", "call"
        }
        
        # Tokenize incoming message
        msg_words = set([w.strip(".,!?\"'()[]{}") for w in raw_message.lower().split()])
        msg_words = msg_words - stop_words
        
        # Collect contract entities
        entities = [str(e).lower() for e in contract.get("entities", [])]
        
        scored_tasks = []
        for task in open_tasks:
            title = task.get("title", "") or ""
            desc = task.get("description", "") or ""
            text = (title + " " + desc).lower()
            
            # Tokenize task text
            task_words = set([w.strip(".,!?\"'()[]{}") for w in text.split()])
            task_words = task_words - stop_words
            
            # Count word overlaps
            overlap = msg_words.intersection(task_words)
            score = len(overlap)
            
            # Boost score if entities match
            for ent in entities:
                if ent in text:
                    score += 3
            
            if score > 0:
                scored_tasks.append((score, task))
                
        # Sort by score descending
        scored_tasks.sort(key=lambda x: x[0], reverse=True)
        
        # Return top N candidates
        return [task for score, task in scored_tasks[:max_candidates]]

    def _update_route_status(self, supabase_client: Any, route_id: str, status: str, error_message: str = None) -> None:
        """Helper to update signal_routes table row state."""
        update_data = {
            "route_status": status,
            "completed_at": _now()
        }
        if error_message:
            update_data["error_message"] = error_message[:1000]

        try:
            supabase_client.table("signal_routes").update(update_data).eq("id", route_id).execute()
            logger.info(f"todo_agent: Updated route {route_id} status to {status}")
        except Exception as e:
            logger.error(f"todo_agent: Failed to update route {route_id} to status {status}: {e}")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
