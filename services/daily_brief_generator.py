# services/daily_brief_generator.py

import json
from datetime import datetime, timedelta
from loguru import logger
from storage.db.database import SessionLocal
from storage.models.todo import Todo
from storage.models.financial_event import FinancialEvent
from storage.models.fyi_event import FyiEvent
from storage.models.daily_brief import DailyBrief


class DailyBriefGenerator:
    """
    Milestone 5 - Daily Brief Generator
    Generates a daily intelligence summary from structured tables.
    """

    @classmethod
    def generate_brief_for_date(cls, date_str: str) -> dict:
        """
        Compiles all structured data for a given date_str (YYYY-MM-DD),
        saves the compiled JSON into the daily_briefs table, and returns the dict.
        """
        logger.info(f"Generating Daily Brief for date: {date_str}")
        
        try:
            # Parse target date range
            target_date = datetime.strptime(date_str, "%Y-%m-%d")
        except Exception as e:
            logger.error(f"Invalid date format: {date_str}. Must be YYYY-MM-DD. Error: {e}")
            raise e

        db = SessionLocal()
        try:
            # 1. Gather TODOs (due on target date or overdue)
            # Find todos due on target date or overdue
            todos = db.query(Todo).all()
            today_todos = []
            for t in todos:
                if t.due_date:
                    try:
                        due_dt = datetime.strptime(t.due_date, "%Y-%m-%d")
                        # Include if due on this day or overdue (before this day)
                        if due_dt <= target_date:
                            today_todos.append({
                                "id": t.id,
                                "title": t.title,
                                "due_date": t.due_date,
                                "priority": t.priority,
                                "source_signal_id": t.source_signal_id
                            })
                    except Exception:
                        # If due date parsing fails, check text
                        if t.due_date == date_str:
                            today_todos.append({
                                "id": t.id,
                                "title": t.title,
                                "due_date": t.due_date,
                                "priority": t.priority,
                                "source_signal_id": t.source_signal_id
                            })

            # 2. Gather Financial Events recorded on target date
            fin_events = db.query(FinancialEvent).all()
            today_fin_events = []
            total_debit = 0.0
            total_credit = 0.0
            
            for f in fin_events:
                # Check if event was created or happened on target date
                ref_dt = f.event_date if f.event_date else f.created_at
                if ref_dt and ref_dt.date() == target_date.date():
                    event_data = {
                        "id": f.id,
                        "title": f.title,
                        "amount": f.amount,
                        "currency": f.currency,
                        "type": f.transaction_type,
                        "payment_channel": f.payment_channel,
                        "paid_to": f.paid_to,
                        "paid_from": f.paid_from,
                        "transaction_id": f.transaction_id
                    }
                    today_fin_events.append(event_data)
                    
                    if f.amount:
                        if f.transaction_type == "debit":
                            total_debit += f.amount
                        elif f.transaction_type == "credit":
                            total_credit += f.amount

            # 3. Gather FYI Events recorded on target date
            fyi_events = db.query(FyiEvent).all()
            today_fyi_events = []
            for f in fyi_events:
                ref_dt = f.created_at
                if ref_dt and ref_dt.date() == target_date.date():
                    today_fyi_events.append({
                        "id": f.id,
                        "title": f.title,
                        "fyi_type": f.fyi_type,
                        "content": f.content
                    })

            # 4. Compile Important Items
            important_items = []

            # 4.1 High-priority TODOs (due today or overdue)
            for t in today_todos:
                if t["priority"] == "high":
                    important_items.append({
                        "type": "high_priority_todo",
                        "title": t["title"],
                        "due_date": t["due_date"]
                    })

            # 4.2 Upcoming insurance renewals (event_date is in next 7 days from target date)
            seven_days_later = target_date + timedelta(days=7)
            for f in fin_events:
                if f.transaction_type == "renewal" and f.event_date:
                    # check if event_date is between target_date and seven_days_later
                    if target_date.date() <= f.event_date.date() <= seven_days_later.date():
                        important_items.append({
                            "type": "insurance_renewal",
                            "title": f.title,
                            "due_date": f.event_date.strftime("%Y-%m-%d"),
                            "amount": f.amount,
                            "currency": f.currency
                        })

            # 4.3 High value or failed transaction alerts on target date
            for f in fin_events:
                ref_dt = f.event_date if f.event_date else f.created_at
                if ref_dt and ref_dt.date() == target_date.date():
                    # High value debits (e.g. >= 10,000 INR)
                    if f.amount and f.transaction_type == "debit" and f.amount >= 10000.0:
                        important_items.append({
                            "type": "high_value_expense",
                            "title": f.title,
                            "amount": f.amount,
                            "currency": f.currency
                        })
                    # Failed/disputed transaction indications in title
                    summary_lower = (f.title or "").lower()
                    if "fail" in summary_lower or "dispute" in summary_lower or "unauthorized" in summary_lower:
                        important_items.append({
                            "type": "transaction_alert",
                            "title": f.title,
                            "amount": f.amount,
                            "currency": f.currency
                        })

            # Construct Daily Brief payload
            brief_data = {
                "todos": today_todos,
                "financial": {
                    "total_debit": total_debit,
                    "total_credit": total_credit,
                    "events": today_fin_events
                },
                "fyi": today_fyi_events,
                "important_items": important_items
            }

            # Persist to database (upsert/merge brief by date)
            brief_obj = DailyBrief(
                date=date_str,
                content_json=json.dumps(brief_data)
            )
            
            # Look for existing brief by date to override
            existing_brief = db.query(DailyBrief).filter(DailyBrief.date == date_str).first()
            if existing_brief:
                existing_brief.content_json = brief_obj.content_json
                existing_brief.created_at = datetime.utcnow()
            else:
                db.add(brief_obj)
                
            db.commit()
            logger.success(f"Successfully generated and saved daily brief for {date_str}.")
            
            # Sync back to Supabase (Feedback Loop)
            try:
                from services.supabase_sync_service import SupabaseSyncService
                SupabaseSyncService.sync_brief_for_date(date_str)
            except Exception as sync_err:
                logger.warning(f"Failed to sync daily brief for {date_str} to Supabase: {sync_err}")

            return brief_data

        except Exception as e:
            logger.exception(f"Failed to generate daily brief: {e}")
            db.rollback()
            raise e
        finally:
            db.close()
