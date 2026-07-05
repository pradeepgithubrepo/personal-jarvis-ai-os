# src/agents/daily_brief/context_builder.py

from datetime import datetime, timedelta, time, date
from sqlalchemy import select, and_, or_
from loguru import logger
from storage.models.todo_item import TodoItem
from storage.models.fyi_event import FyiEvent
from storage.models.fact import Fact
from src.agents.daily_brief.prioritizer import DailyBriefPrioritizer

class DailyBriefContextBuilder:
    """
    Assembles structured life state context from SQLite for LLM consumption.
    """

    @staticmethod
    def build_context(db_session, target_date: datetime = None) -> dict:
        if not target_date:
            target_date = datetime.utcnow()
            
        today_start = datetime.combine(target_date.date(), time.min)
        today_end = datetime.combine(target_date.date(), time.max)
        seven_days_later = today_end + timedelta(days=7)

        # 1. Gather TODOs
        stmt_all_todos = select(TodoItem).where(
            or_(
                TodoItem.status == "OPEN",
                TodoItem.status == "IN_PROGRESS"
            )
        )
        all_todos = list(db_session.scalars(stmt_all_todos).all())
        all_todos = DailyBriefPrioritizer.sort_by_importance(all_todos)

        overdue_tasks = []
        today_tasks = []
        upcoming_events = []

        for t in all_todos:
            t_data = {
                "todo_id": t.todo_id,
                "title": t.title,
                "description": t.description,
                "category": t.category,
                "priority": t.priority,
                "due_date": t.due_date.strftime("%Y-%m-%d") if t.due_date else None
            }
            if t.due_date:
                if t.due_date < today_start:
                    overdue_tasks.append(t_data)
                elif today_start <= t.due_date <= today_end:
                    today_tasks.append(t_data)
                elif today_end < t.due_date <= seven_days_later:
                    upcoming_events.append(t_data)
            else:
                today_tasks.append(t_data) # Treat tasks without due date as open for today

        # 2. Gather New Facts created/modified today
        stmt_facts = select(Fact).where(
            or_(
                Fact.first_seen >= today_start,
                Fact.created_at >= today_start
            )
        )
        facts = list(db_session.scalars(stmt_facts).all())
        new_facts = [{
            "fact_id": f.fact_id,
            "fact_type": f.fact_type,
            "fact_value": f.fact_value,
            "confidence": f.confidence,
            "status": f.status
        } for f in facts]

        # 3. Gather New FYIs received today (filter out read/archived and low importance items)
        stmt_fyis = select(FyiEvent).where(
            and_(
                FyiEvent.created_at >= today_start,
                FyiEvent.status == "UNREAD",
                or_(FyiEvent.importance == "HIGH", FyiEvent.importance == "MEDIUM")
            )
        )
        fyis = list(db_session.scalars(stmt_fyis).all())
        new_fyis = [{
            "event_id": f.event_id,
            "event_type": f.event_type,
            "category": f.category,
            "title": f.title,
            "description": f.description,
            "importance": f.importance,
            "status": f.status
        } for f in fyis]

        # 4. Gather Financial Activity today
        financial_activity = []
        try:
            from storage.models.financial_fact import FinancialFact
            stmt_fin_facts = select(FinancialFact).where(
                and_(
                    FinancialFact.fact_type == "EXPENSE_EVENT",
                    FinancialFact.created_at >= today_start
                )
            )
            fin_facts = list(db_session.scalars(stmt_fin_facts).all())
            for ff in fin_facts:
                val = ff.fact_value or {}
                financial_activity.append({
                    "merchant": val.get("merchant_name", "Unknown"),
                    "amount": val.get("amount", 0.0),
                    "currency": val.get("currency", "INR"),
                    "category": val.get("category", "GENERAL")
                })
        except Exception:
            pass

        # 5. ENHANCEMENT: Financial Summary (Yesterday Spend, Biggest Expense, Category Summary)
        yesterday_date = target_date.date() - timedelta(days=1)
        yesterday_spend = 0.0
        biggest_expense = None
        spending_category_summary = {}

        try:
            from storage.models.financial_fact import FinancialFact
            stmt_yesterday_fin = select(FinancialFact).where(
                and_(
                    FinancialFact.fact_type == "EXPENSE_EVENT",
                    FinancialFact.event_date == yesterday_date
                )
            )
            yesterday_facts = list(db_session.scalars(stmt_yesterday_fin).all())
            for yf in yesterday_facts:
                amount = yf.amount
                merchant = yf.merchant_canonical or yf.merchant_raw or "Unknown"
                category = yf.category or "GENERAL"
                
                yesterday_spend += amount
                spending_category_summary[category] = spending_category_summary.get(category, 0.0) + amount
                
                if biggest_expense is None or amount > biggest_expense["amount"]:
                    biggest_expense = {
                        "merchant": merchant,
                        "amount": amount
                    }
        except Exception as e:
            logger.error(f"Failed to gather yesterday's financial summary: {e}")

        financial_summary = {
            "yesterday_spend": yesterday_spend,
            "biggest_expense": biggest_expense,
            "spending_category_summary": spending_category_summary
        }

        # 6. ENHANCEMENT: Priority Extraction (Top 3 Priorities for the day)
        top_priorities = []
        # Priority Order: 1. Overdue tasks
        for ot in overdue_tasks:
            if len(top_priorities) >= 3:
                break
            top_priorities.append({
                "priority_type": "OVERDUE_TASK",
                "title": ot["title"],
                "identifier": ot["todo_id"]
            })
        # 2. Due today tasks
        for tt in today_tasks:
            if len(top_priorities) >= 3:
                break
            top_priorities.append({
                "priority_type": "DUE_TODAY_TASK",
                "title": tt["title"],
                "identifier": tt["todo_id"]
            })
        # 3. High-priority FYI
        for f in new_fyis:
            if len(top_priorities) >= 3:
                break
            if f["importance"] == "HIGH":
                top_priorities.append({
                    "priority_type": "HIGH_PRIORITY_FYI",
                    "title": f["title"],
                    "identifier": f["event_id"]
                })
        # 4. Upcoming events
        for ue in upcoming_events:
            if len(top_priorities) >= 3:
                break
            top_priorities.append({
                "priority_type": "UPCOMING_EVENT",
                "title": ue["title"],
                "identifier": ue["todo_id"]
            })

        return {
            "target_date": target_date.strftime("%Y-%m-%d"),
            "overdue_task_count": len(overdue_tasks),
            "overdue_tasks": overdue_tasks,
            "today_tasks": today_tasks,
            "upcoming_events": upcoming_events,
            "new_facts": new_facts,
            "new_fyis": new_fyis,
            "financial_activity": financial_activity,
            "financial_summary": financial_summary,
            "top_priorities": top_priorities
        }
