# services/todo_agent.py

import json
from datetime import datetime, timedelta
from loguru import logger
from sqlalchemy import select, and_, or_
from storage.models.todo_item import TodoItem
from storage.models.fact import Fact
from storage.models.financial_fact import FinancialFact
from services.supabase_repo import SupabaseRepo

VALID_CATEGORIES = {
    "FINANCIAL",
    "MEDICAL",
    "EDUCATION",
    "TRAVEL",
    "HOUSEHOLD",
    "WORK",
    "SUBSCRIPTION",
    "INSURANCE",
    "VEHICLE",
    "GENERAL",
}


class TodoAgent:
    """
    The Action Layer agent. Responsible for identifying, prioritizing,
    deduplicating, enriching, and completing user tasks.
    """

    @classmethod
    def ingest_candidate(cls, candidate: dict, db_session) -> str:
        """
        Ingests a new task candidate, enriches it from FactAgent memory,
        evaluates its priority, checks for duplicates, and persists it.
        """
        title = candidate.get("title")
        category = candidate.get("category", "GENERAL").upper()
        if category not in VALID_CATEGORIES:
            category = "GENERAL"

        if not title:
            raise ValueError("Task title is required.")

        # 1. Memory Enrichment from FactAgent
        cls.enrich_from_memory(candidate, db_session)

        # 2. Priority Evaluation
        priority = cls.evaluate_priority(candidate)

        # 3. Deduplication Check
        due_date_str = candidate.get("due_date")
        due_date = None
        if due_date_str:
            if isinstance(due_date_str, str):
                try:
                    due_date = datetime.fromisoformat(due_date_str)
                except ValueError:
                    due_date = None
            else:
                due_date = due_date_str

        existing_todo = cls.deduplicate(category, candidate.get("title"), due_date, db_session)
        if existing_todo:
            logger.info(f"TodoAgent: Found duplicate task {existing_todo.todo_id}. Merging...")
            # Merge description
            new_desc = candidate.get("description", "")
            if new_desc and new_desc not in (existing_todo.description or ""):
                existing_todo.description = f"{existing_todo.description or ''}\n{new_desc}".strip()
            
            existing_todo.confidence = max(existing_todo.confidence, candidate.get("confidence", 1.0))
            
            # Escalate priority on repeated observation
            if existing_todo.priority == "LOW" and priority in ("MEDIUM", "HIGH", "CRITICAL"):
                existing_todo.priority = priority
            elif existing_todo.priority == "MEDIUM" and priority in ("HIGH", "CRITICAL"):
                existing_todo.priority = priority
            elif existing_todo.priority == "HIGH" and priority == "CRITICAL":
                existing_todo.priority = "CRITICAL"

            existing_todo.updated_at = datetime.utcnow()
            db_session.commit()
            
            # Sync update to Supabase
            SupabaseRepo.store_todo_item(
                todo_id=existing_todo.todo_id,
                title=existing_todo.title,
                description=existing_todo.description,
                category=existing_todo.category,
                priority=existing_todo.priority,
                status=existing_todo.status,
                due_date=existing_todo.due_date,
                source_agent=existing_todo.source_agent,
                source_reference=existing_todo.source_reference,
                confidence=existing_todo.confidence,
            )
            return existing_todo.todo_id

        # 4. Create new TodoItem
        new_todo = TodoItem(
            title=candidate.get("title"),
            description=candidate.get("description"),
            category=category,
            priority=priority,
            status=candidate.get("status", "OPEN"),
            due_date=due_date,
            source_agent=candidate.get("source_agent", "Unknown"),
            source_reference=candidate.get("source_reference"),
            confidence=candidate.get("confidence", 1.0)
        )
        db_session.add(new_todo)
        db_session.commit()

        # Sync to Supabase
        SupabaseRepo.store_todo_item(
            todo_id=new_todo.todo_id,
            title=new_todo.title,
            description=new_todo.description,
            category=new_todo.category,
            priority=new_todo.priority,
            status=new_todo.status,
            due_date=new_todo.due_date,
            source_agent=new_todo.source_agent,
            source_reference=new_todo.source_reference,
            confidence=new_todo.confidence,
        )
        return new_todo.todo_id

    @classmethod
    def enrich_from_memory(cls, candidate: dict, db_session):
        """
        Enriches task candidates using context from the Fact Agent ledger.
        """
        category = candidate.get("category", "").upper()
        title = candidate.get("title", "")
        description = candidate.get("description", "") or ""

        # 1. Insurance Enrichment
        if category == "INSURANCE" or "insurance" in title.lower():
            stmt = select(Fact).where(Fact.fact_type == "INSURANCE_POLICY")
            policies = db_session.scalars(stmt).all()
            if policies:
                # Use first policy as reference
                policy = policies[0]
                provider = policy.fact_value.get("provider", "Unknown Insurer")
                policy_num = policy.fact_value.get("policy_number", "")
                
                candidate["title"] = f"Renew {provider} insurance policy"
                if policy_num:
                    candidate["description"] = f"{description}\nPolicy Number: {policy_num}".strip()

        # 2. Vehicle Enrichment
        elif category == "VEHICLE" or "car" in title.lower() or "bike" in title.lower():
            stmt = select(Fact).where(Fact.fact_type == "VEHICLE")
            vehicles = db_session.scalars(stmt).all()
            if vehicles:
                vehicle = vehicles[0]
                make = vehicle.fact_value.get("make", "")
                model = vehicle.fact_value.get("model", "")
                plate = vehicle.fact_value.get("license_plate", "")
                
                candidate["title"] = f"Service vehicle: {make} {model}".strip()
                if plate:
                    candidate["description"] = f"{description}\nLicense Plate: {plate}".strip()

        # 3. School / Education Enrichment
        elif category == "EDUCATION" or "school" in title.lower():
            stmt = select(Fact).where(Fact.fact_type == "CHILD")
            children = db_session.scalars(stmt).all()
            if children:
                child_names = ", ".join([c.fact_value.get("name", "") for c in children])
                candidate["description"] = f"{description}\nAssociated Child/ren: {child_names}".strip()

    @classmethod
    def evaluate_priority(cls, candidate: dict) -> str:
        """
        Assigns CRITICAL, HIGH, MEDIUM, or LOW priority based on urgency and risk factors.
        """
        title_lower = candidate.get("title", "").lower()
        desc_lower = (candidate.get("description", "") or "").lower()
        category = candidate.get("category", "GENERAL").upper()
        due_date_str = candidate.get("due_date")

        # 1. Financial/Risk defaults
        if category == "FINANCIAL":
            if "fail" in title_lower or "bounce" in title_lower or "default" in title_lower:
                return "CRITICAL"
            if "emi" in title_lower or "due" in title_lower:
                return "HIGH"

        if category == "INSURANCE" and ("expiry" in title_lower or "expire" in title_lower):
            return "CRITICAL"

        # 2. Time proximity
        if due_date_str:
            due_date = None
            try:
                if isinstance(due_date_str, str):
                    due_date = datetime.fromisoformat(due_date_str)
                else:
                    due_date = due_date_str
            except ValueError:
                pass

            if due_date:
                now = datetime.utcnow()
                diff = due_date - now
                if diff <= timedelta(hours=24):
                    return "CRITICAL"
                elif diff <= timedelta(days=3):
                    return "HIGH"
                elif diff <= timedelta(days=7):
                    return "MEDIUM"

        return candidate.get("priority", "MEDIUM").upper()

    @classmethod
    def deduplicate(cls, category: str, title: str, due_date, db_session) -> TodoItem | None:
        """
        Looks for open tasks that match this candidate's title keywords and due date.
        """
        stmt = select(TodoItem).where(
            and_(
                TodoItem.category == category,
                TodoItem.status == "OPEN"
            )
        )
        open_todos = db_session.scalars(stmt).all()

        title_words = set(title.lower().split())
        for todo in open_todos:
            # Semantic keyword overlap
            todo_words = set(todo.title.lower().split())
            common_words = title_words.intersection(todo_words)
            
            # If 50% of the words overlap, we check due date
            if len(common_words) >= min(len(title_words), len(todo_words)) * 0.5:
                if not due_date or not todo.due_date:
                    return todo
                # Due date is within 24 hours
                if abs((todo.due_date - due_date).total_seconds()) <= 86400:
                    return todo

        return None

    @classmethod
    def auto_complete_tasks(cls, db_session) -> int:
        """
        Scans for paid financial facts matching open todo items and auto-closes them.
        """
        stmt = select(TodoItem).where(TodoItem.status == "OPEN")
        open_todos = db_session.scalars(stmt).all()

        completed_count = 0
        for todo in open_todos:
            # 1. Financial check
            if todo.category in ("FINANCIAL", "INSURANCE", "SUBSCRIPTION"):
                # Fetch recent payments
                stmt_facts = select(FinancialFact).where(
                    and_(
                        FinancialFact.fact_type == "EXPENSE_EVENT",
                        FinancialFact.created_at >= todo.created_at - timedelta(days=7)
                    )
                )
                facts = db_session.scalars(stmt_facts).all()
                for fact in facts:
                    # Match merchant name or keywords in todo title
                    merchant = (fact.merchant_canonical or "").lower()
                    if merchant and merchant in todo.title.lower():
                        logger.info(f"TodoAgent: Auto-completing task '{todo.title}' due to matching payment to {fact.merchant_canonical}")
                        todo.status = "COMPLETED"
                        todo.updated_at = datetime.utcnow()
                        completed_count += 1
                        
                        # Sync update to Supabase
                        SupabaseRepo.store_todo_item(
                            todo_id=todo.todo_id,
                            title=todo.title,
                            description=todo.description,
                            category=todo.category,
                            priority=todo.priority,
                            status=todo.status,
                            due_date=todo.due_date,
                            source_agent=todo.source_agent,
                            source_reference=todo.source_reference,
                            confidence=todo.confidence,
                        )
                        break

        db_session.commit()
        return completed_count

    @classmethod
    def process_all_understood_signals(cls, db_session) -> dict:
        """
        Pipeline integration step: queries understood signals,
        identifies action-class events, and ingests them.
        """
        from storage.models.understood_signal import UnderstoodSignal

        logger.info("TodoAgent: processing understood signals for action items...")
        stmt = select(UnderstoodSignal)
        signals = db_session.scalars(stmt).all()

        metrics = {
            "processed": 0,
            "todos_created": 0,
            "auto_completed": 0,
            "failed": 0
        }

        for signal in signals:
            try:
                metrics["processed"] += 1
                contract = {}
                if signal.contract_json:
                    try:
                        contract = json.loads(signal.contract_json)
                    except Exception:
                        contract = signal.contract_json if isinstance(signal.contract_json, dict) else {}

                classes = contract.get("classes", [])
                
                # We ingest if classes contain ACTION
                if "ACTION" in classes:
                    # Map category
                    domain = "GENERAL"
                    domains = contract.get("domains", [])
                    if domains:
                        domain = domains[0]

                    category = "GENERAL"
                    if domain == "FINANCE":
                        category = "FINANCIAL"
                    elif domain == "INSURANCE":
                        category = "INSURANCE"
                    elif domain == "EDUCATION":
                        category = "EDUCATION"
                    elif domain == "TRAVEL":
                        category = "TRAVEL"

                    due_date_val = None
                    deadlines = contract.get("entities", {}).get("deadlines", [])
                    if deadlines:
                        due_date_val = deadlines[0].get("date")

                    candidate = {
                        "title": signal.summary,
                        "description": signal.reason,
                        "category": category,
                        "priority": "MEDIUM",
                        "due_date": due_date_val,
                        "source_agent": "SignalUnderstandingAgent",
                        "source_reference": {"signal_id": signal.id},
                        "confidence": signal.confidence
                    }
                    
                    todo_id = cls.ingest_candidate(candidate, db_session)
                    if todo_id:
                        metrics["todos_created"] += 1

            except Exception as e:
                logger.error(f"TodoAgent: Failed to process signal {signal.id}: {e}")
                metrics["failed"] += 1

        # Run auto completion detection after ingesting
        auto_completed = cls.auto_complete_tasks(db_session)
        metrics["auto_completed"] = auto_completed

        return metrics
