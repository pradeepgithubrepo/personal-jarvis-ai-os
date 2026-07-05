# services/todo_agent.py

import json
import re
from datetime import datetime, timedelta
from loguru import logger
from sqlalchemy import select, and_, or_
from storage.models.todo_item import TodoItem
from storage.models.fact import Fact
from storage.models.financial_fact import FinancialFact
from services.supabase_repo import SupabaseRepo

VALID_CATEGORIES = {
    "BILL",
    "FINANCIAL",
    "FAMILY",
    "PERSONAL",
    "WORK"
}

class TodoAgent:
    """
    The Action Layer agent. Responsible for identifying, prioritizing,
    deduplicating, enriching, and completing user tasks.
    """

    @classmethod
    def evaluate_actionability(cls, signal_summary: str, signal_reason: str, contract: dict) -> dict:
        text = f"{signal_summary} {signal_reason}".lower()
        
        # Default scores
        score = 0
        requires_action = False
        action_type = "FYI"
        reason = "No action required by default."
        confidence = contract.get("confidence", 1.0)
        
        # Hard rejection patterns
        rejection_words = [
            "credited", "received", "refund processed", "successfully completed",
            "successfully debited", "successfully credited", "payment successful",
            "transaction successful", "balance available", "statement generated",
            "cashback", "reward points", "otp"
        ]
        
        # Check rejection first
        has_rejection_word = any(rw in text for rw in rejection_words)
        
        # Deterministic rules for TODO creation:
        # Bills
        bill_words = ["payment due", "bill due", "minimum due", "outstanding amount", "card bill", "bill alert", "total amount due", "due date", "due on", "payable", "money due", "charges"]
        is_bill = any(bw in text for bw in bill_words)
        
        # Financial
        fin_words = ["emi due", "insurance renewal", "policy renewal", "kyc update", "tax payment", "fd maturity", "maturity", "renew", "reminder"]
        is_fin = any(fw in text for fw in fin_words) or ("maturity" in text and "proceeds" not in text)
        
        # Family
        fam_words = ["school fee", "parent meeting", "acknowledgement required", "child activity", "medical follow-up", "pop meeting", "homework", "parental update"]
        is_fam = any(faw in text for faw in fam_words)
        
        # Personal
        pers_words = ["appointment", "travel check-in", "subscription renewal", "document renewal"]
        is_pers = any(pw in text for pw in pers_words)
        
        # Work
        work_words = ["approval required", "document submission", "interview", "meeting requiring response"]
        is_work = any(ww in text for ww in work_words)
        
        # Determine score
        if is_bill or is_fin or is_fam or is_pers or is_work:
            if not has_rejection_word or "due" in text or "renew" in text:
                score = 90
                requires_action = True
                action_type = "TODO"
                reason = "Actionable deadline or requirement identified."
        
        # If it has feedback, survey, optional registration
        elif "feedback" in text or "survey" in text or "register" in text:
            score = 50
            requires_action = True
            action_type = "TODO"
            reason = "Optional action identified."
            
        if has_rejection_word and score >= 40:
            if not ("meeting" in text or "orientation" in text or "due" in text or "renew" in text):
                score = 20
                requires_action = False
                action_type = "FYI"
                reason = "Hard rejection pattern matched (informational/confirmation event)."

        return {
            "requires_user_action": requires_action,
            "actionability_score": score,
            "action_type": action_type,
            "reason": reason,
            "confidence": confidence
        }

    @classmethod
    def parse_remediated_due_date(cls, due_date_str: str, signal_dt: datetime) -> datetime | None:
        if not due_date_str:
            return None
        try:
            if due_date_str.endswith('Z'):
                due_date_str = due_date_str[:-1]
            
            if len(due_date_str) >= 10:
                parsed = datetime.fromisoformat(due_date_str)
                if parsed.year < signal_dt.year:
                    parsed = parsed.replace(year=signal_dt.year)
                return parsed
        except Exception:
            pass
            
        text = due_date_str.lower()
        if "today" in text:
            return signal_dt
        if "tomorrow" in text:
            return signal_dt + timedelta(days=1)
        if "24 hours" in text or "24h" in text:
            return signal_dt + timedelta(days=1)
        if "48 hours" in text or "48h" in text:
            return signal_dt + timedelta(days=2)
            
        match = re.search(r"(\d{1,2})[/-](\d{1,2})", due_date_str)
        if match:
            try:
                day = int(match.group(1))
                month = int(match.group(2))
                parsed = datetime(year=signal_dt.year, month=month, day=day)
                if parsed < signal_dt:
                    parsed = parsed.replace(year=signal_dt.year + 1)
                return parsed
            except Exception:
                pass
                
        match_str = re.search(r"(\d{1,2})[-/\s]([a-zA-Z]{3})", due_date_str)
        if match_str:
            try:
                day = int(match_str.group(1))
                month_str = match_str.group(2).lower()
                months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
                month = months.index(month_str[:3]) + 1
                parsed = datetime(year=signal_dt.year, month=month, day=day)
                if parsed < signal_dt:
                    parsed = parsed.replace(year=signal_dt.year + 1)
                return parsed
            except Exception:
                pass
                
        return None

    @classmethod
    def ingest_candidate(cls, candidate: dict, db_session) -> str:
        """
        Ingests a new task candidate, enriches it from FactAgent memory,
        evaluates its priority, checks for duplicates, and persists it.
        """
        title = candidate.get("title")
        category = candidate.get("category", "PERSONAL").upper()
        if category not in VALID_CATEGORIES:
            category = "PERSONAL"

        if not title:
            raise ValueError("Task title is required.")

        # 1. Memory Enrichment from FactAgent
        cls.enrich_from_memory(candidate, db_session)

        # 2. Priority Evaluation
        priority = cls.evaluate_priority(candidate)

        # 3. Deduplication Check
        due_date = candidate.get("due_date")
        if due_date and due_date.tzinfo is not None:
            due_date = due_date.replace(tzinfo=None)

        existing_todo = cls.deduplicate(category, candidate.get("title"), due_date, db_session)
        if existing_todo:
            logger.info(f"TodoAgent: Found duplicate task {existing_todo.todo_id}. Merging...")
            new_desc = candidate.get("description", "")
            if new_desc and new_desc not in (existing_todo.description or ""):
                existing_todo.description = f"{existing_todo.description or ''}\n{new_desc}".strip()
            
            existing_todo.confidence = max(existing_todo.confidence, candidate.get("confidence", 1.0))
            
            if existing_todo.priority == "LOW" and priority in ("MEDIUM", "HIGH", "CRITICAL"):
                existing_todo.priority = priority
            elif existing_todo.priority == "MEDIUM" and priority in ("HIGH", "CRITICAL"):
                existing_todo.priority = priority
            elif existing_todo.priority == "HIGH" and priority == "CRITICAL":
                existing_todo.priority = "CRITICAL"

            existing_todo.updated_at = datetime.utcnow()
            db_session.commit()
            
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

        # Get parent batch_id
        parent_batch_id = None
        source_ref = candidate.get("source_reference")
        if source_ref and "signal_id" in source_ref:
            from storage.models.understood_signal import UnderstoodSignal
            under_sig = db_session.query(UnderstoodSignal).filter(UnderstoodSignal.id == str(source_ref["signal_id"])).first()
            if under_sig:
                parent_batch_id = under_sig.batch_id

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
            confidence=candidate.get("confidence", 1.0),
            why_action_needed=candidate.get("why_action_needed"),
            consequence_if_ignored=candidate.get("consequence_if_ignored"),
            batch_id=parent_batch_id,
            sync_status='PENDING'
        )
        db_session.add(new_todo)
        db_session.commit()

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
        category = candidate.get("category", "").upper()
        title = candidate.get("title", "")
        description = candidate.get("description", "") or ""

        # Enrichment
        if category == "FINANCIAL" or "insurance" in title.lower():
            stmt = select(Fact).where(Fact.fact_type == "INSURANCE_POLICY")
            policies = db_session.scalars(stmt).all()
            if policies:
                policy = policies[0]
                provider = policy.fact_value.get("provider", "Unknown Insurer")
                policy_num = policy.fact_value.get("policy_number", "")
                candidate["title"] = f"Renew {provider} insurance policy"
                if policy_num:
                    candidate["description"] = f"{description}\nPolicy Number: {policy_num}".strip()
        elif category == "FAMILY" or "school" in title.lower():
            stmt = select(Fact).where(Fact.fact_type == "CHILD")
            children = db_session.scalars(stmt).all()
            if children:
                child_names = ", ".join([c.fact_value.get("name", "") for c in children])
                candidate["description"] = f"{description}\nAssociated Child/ren: {child_names}".strip()

    @classmethod
    def evaluate_priority(cls, candidate: dict) -> str:
        title_lower = candidate.get("title", "").lower()
        category = candidate.get("category", "PERSONAL").upper()
        due_date = candidate.get("due_date")

        if category == "BILL" or category == "FINANCIAL":
            if "fail" in title_lower or "bounce" in title_lower or "default" in title_lower:
                return "CRITICAL"
            if "emi" in title_lower or "due" in title_lower:
                return "HIGH"

        if due_date:
            if due_date.tzinfo is not None:
                due_date = due_date.replace(tzinfo=None)
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
        stmt = select(TodoItem).where(
            and_(
                TodoItem.category == category,
                TodoItem.status == "OPEN"
            )
        )
        open_todos = db_session.scalars(stmt).all()

        title_words = set(title.lower().split())
        for todo in open_todos:
            todo_words = set(todo.title.lower().split())
            common_words = title_words.intersection(todo_words)
            
            if len(common_words) >= min(len(title_words), len(todo_words)) * 0.5:
                if not due_date or not todo.due_date:
                    return todo
                if abs((todo.due_date - due_date).total_seconds()) <= 86400:
                    return todo

        return None

    @classmethod
    def auto_complete_tasks(cls, db_session) -> int:
        stmt = select(TodoItem).where(TodoItem.status == "OPEN")
        open_todos = db_session.scalars(stmt).all()

        completed_count = 0
        for todo in open_todos:
            if todo.category in ("BILL", "FINANCIAL"):
                stmt_facts = select(FinancialFact).where(
                    and_(
                        FinancialFact.fact_type == "EXPENSE_EVENT",
                        FinancialFact.created_at >= todo.created_at - timedelta(days=7)
                    )
                )
                facts = db_session.scalars(stmt_facts).all()
                for fact in facts:
                    merchant = (fact.merchant_canonical or "").lower()
                    if merchant and merchant in todo.title.lower():
                        logger.info(f"TodoAgent: Auto-completing task '{todo.title}' due to matching payment to {fact.merchant_canonical}")
                        todo.status = "COMPLETED"
                        todo.updated_at = datetime.utcnow()
                        completed_count += 1
                        
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
                if isinstance(contract, str):
                    try:
                        contract = json.loads(contract)
                    except Exception:
                        contract = {}

                # 1. Actionability Engine check
                act_result = cls.evaluate_actionability(signal.summary or "", signal.reason or "", contract)
                if not act_result.get("requires_user_action"):
                    continue

                # 2. Category Normalization
                category_input = contract.get("category", "GENERAL").upper()
                domains = contract.get("domains", [])
                domain = domains[0] if domains else ""
                
                category = "PERSONAL"
                if domain == "INSURANCE" or category_input == "INSURANCE":
                    category = "FINANCIAL"
                elif domain == "EDUCATION" or category_input == "EDUCATION":
                    category = "FAMILY"
                elif domain == "TRAVEL" or category_input == "TRAVEL":
                    category = "PERSONAL"
                elif domain == "WORK" or category_input == "WORK":
                    category = "WORK"
                elif domain == "FINANCE" or category_input == "FINANCIAL":
                    category = "FINANCIAL"
                elif domain == "FAMILY" or category_input == "FAMILY":
                    category = "FAMILY"
                elif domain == "BILL" or category_input == "BILL":
                    category = "BILL"
                else:
                    text = (signal.summary + " " + signal.reason).lower()
                    if "bill" in text or "due" in text or "payment" in text or "fee" in text or "electricity" in text:
                        category = "BILL"
                    elif "school" in text or "parent" in text or "meeting" in text or "compulsory" in text or "child" in text:
                        category = "FAMILY"
                    else:
                        category = "PERSONAL"

                # 3. Due Date Remediation
                raw_ts = contract.get("raw_context", {}).get("timestamp")
                signal_dt = None
                if raw_ts:
                    try:
                        signal_dt = datetime.fromisoformat(raw_ts)
                    except ValueError:
                        pass
                if not signal_dt:
                    signal_dt = datetime.utcnow()

                due_date_str = None
                deadlines = contract.get("entities", {}).get("deadlines", [])
                if deadlines:
                    due_date_str = deadlines[0].get("date") if isinstance(deadlines[0], dict) else deadlines[0]

                due_date_val = cls.parse_remediated_due_date(due_date_str, signal_dt)

                candidate = {
                    "title": signal.summary,
                    "description": signal.reason,
                    "category": category,
                    "priority": "MEDIUM",
                    "due_date": due_date_val,
                    "source_agent": "SignalUnderstandingAgent",
                    "source_reference": {"signal_id": signal.id},
                    "confidence": signal.confidence,
                    "why_action_needed": signal.reason,
                    "consequence_if_ignored": "Potential breach or missed obligation if ignored."
                }
                
                todo_id = cls.ingest_candidate(candidate, db_session)
                if todo_id:
                    metrics["todos_created"] += 1

            except Exception as e:
                logger.error(f"TodoAgent: Failed to process signal {signal.id}: {e}")
                metrics["failed"] += 1

        # Auto-complete detection
        auto_completed = cls.auto_complete_tasks(db_session)
        metrics["auto_completed"] = auto_completed

        return metrics
