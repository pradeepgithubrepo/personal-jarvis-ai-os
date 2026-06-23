# services/supabase_repo.py

import uuid
from datetime import datetime
from loguru import logger
from configs.settings import settings
from supabase import create_client, Client
from supabase.client import ClientOptions

# Initialize Supabase client targeting 'jarvis_insights_schema'
url = settings.supabase_url
key = settings.supabase_secret_key or settings.supabase_key

opts = ClientOptions(schema="jarvis_insights_schema")
supabase: Client = create_client(url, key, options=opts)

class SupabaseRepo:
    @staticmethod
    def _execute(func):
        """Helper to run API calls safely and log exceptions."""
        try:
            res = func()
            # If request returns data, we can verify it succeeded
            return True
        except Exception as e:
            logger.error(f"Supabase API request failed: {e}")
            return False

    @classmethod
    def save_signal(cls, signal_id: uuid.UUID, source: str, sender: str, message: str, signal_timestamp: datetime, created_at: datetime, raw_signal_id: str, metadata: dict) -> bool:
        data = {
            "signal_id": str(signal_id),
            "source": source,
            "sender": sender,
            "message": message,
            "signal_timestamp": signal_timestamp.isoformat() if hasattr(signal_timestamp, "isoformat") else str(signal_timestamp),
            "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at),
            "raw_signal_id": raw_signal_id,
            "metadata": metadata
        }
        return cls._execute(lambda: supabase.table("signals").upsert(data).execute())

    @classmethod
    def create_todo(cls, todo_id: uuid.UUID, title: str, description: str, priority: str, status: str, due_date: datetime, source_signal_id: uuid.UUID) -> bool:
        data = {
            "todo_id": str(todo_id),
            "title": title,
            "description": description,
            "priority": priority,
            "status": status,
            "due_date": due_date.isoformat() if hasattr(due_date, "isoformat") else str(due_date) if due_date else None,
            "source_signal_id": str(source_signal_id) if source_signal_id else None,
            "updated_at": datetime.utcnow().isoformat()
        }
        return cls._execute(lambda: supabase.table("todos").upsert(data).execute())

    @classmethod
    def update_todo_status(cls, todo_id: uuid.UUID, status: str) -> bool:
        if status not in ("OPEN", "COMPLETED", "SNOOZED", "DISMISSED"):
            raise ValueError(f"Invalid status value: {status}")
        data = {
            "status": status,
            "updated_at": datetime.utcnow().isoformat()
        }
        return cls._execute(lambda: supabase.table("todos").update(data).eq("todo_id", str(todo_id)).execute())

    @classmethod
    def create_financial_event(cls, event_id: uuid.UUID, merchant: str, amount: float, currency: str, category: str, status: str, event_timestamp: datetime, source_signal_id: uuid.UUID) -> bool:
        data = {
            "financial_event_id": str(event_id),
            "merchant": merchant,
            "amount": float(amount) if amount is not None else 0.0,
            "currency": currency,
            "category": category,
            "status": status,
            "event_timestamp": event_timestamp.isoformat() if hasattr(event_timestamp, "isoformat") else str(event_timestamp) if event_timestamp else None,
            "source_signal_id": str(source_signal_id) if source_signal_id else None,
            "updated_at": datetime.utcnow().isoformat()
        }
        return cls._execute(lambda: supabase.table("financial_events").upsert(data).execute())

    @classmethod
    def reclassify_financial_event(cls, event_id: uuid.UUID, category: str) -> bool:
        data = {
            "category": category,
            "updated_at": datetime.utcnow().isoformat()
        }
        return cls._execute(lambda: supabase.table("financial_events").update(data).eq("financial_event_id", str(event_id)).execute())

    @classmethod
    def create_fyi_event(cls, event_id: uuid.UUID, title: str, summary: str, category: str, read_flag: bool, source_signal_id: uuid.UUID) -> bool:
        data = {
            "fyi_event_id": str(event_id),
            "title": title,
            "summary": summary,
            "category": category,
            "read_flag": read_flag,
            "source_signal_id": str(source_signal_id) if source_signal_id else None,
            "updated_at": datetime.utcnow().isoformat()
        }
        return cls._execute(lambda: supabase.table("fyi_events").upsert(data).execute())

    @classmethod
    def mark_fyi_read(cls, event_id: uuid.UUID, read_flag: bool = True) -> bool:
        data = {
            "read_flag": read_flag,
            "updated_at": datetime.utcnow().isoformat()
        }
        return cls._execute(lambda: supabase.table("fyi_events").update(data).eq("fyi_event_id", str(event_id)).execute())

    @classmethod
    def store_fact(cls, fact_id: uuid.UUID, entity: str, fact: str, confidence: float, source_signal_id: uuid.UUID) -> bool:
        data = {
            "fact_id": str(fact_id),
            "entity": entity,
            "fact": fact,
            "confidence": float(confidence) if confidence is not None else 1.0,
            "source_signal_id": str(source_signal_id) if source_signal_id else None,
            "created_at": datetime.utcnow().isoformat()
        }
        return cls._execute(lambda: supabase.table("facts").insert(data).execute())

    @classmethod
    def store_preference(cls, key: str, value: str) -> bool:
        data = {
            "preference_key": key,
            "preference_value": value,
            "updated_at": datetime.utcnow().isoformat()
        }
        return cls._execute(lambda: supabase.table("user_preferences").upsert(data).execute())

    @classmethod
    def store_user_action(cls, action_id: uuid.UUID, entity_type: str, entity_id: str, action: str, metadata: dict) -> bool:
        data = {
            "action_id": str(action_id),
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "action": action,
            "action_timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata
        }
        return cls._execute(lambda: supabase.table("user_actions").insert(data).execute())

    @classmethod
    def fetch_todos(cls) -> list[dict]:
        try:
            res = supabase.table("todos").select("*").order("due_date", nullsfirst=False).order("created_at", desc=True).execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Failed to fetch todos: {e}")
            return []

    @classmethod
    def fetch_financial_events(cls) -> list[dict]:
        try:
            res = supabase.table("financial_events").select("*").order("event_timestamp", desc=True).execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Failed to fetch financial events: {e}")
            return []

    @classmethod
    def fetch_fyi_events(cls, category: str = None) -> list[dict]:
        try:
            q = supabase.table("fyi_events").select("*")
            if category:
                q = q.eq("category", category)
            res = q.order("created_at", desc=True).execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Failed to fetch FYI events: {e}")
            return []

    @classmethod
    def save_salary_cycle(cls, cycle_id: uuid.UUID, salary_date: datetime, salary_amount: float, cycle_start: datetime, cycle_end: datetime) -> bool:
        data = {
            "salary_cycle_id": str(cycle_id),
            "salary_date": salary_date.isoformat() if hasattr(salary_date, "isoformat") else str(salary_date),
            "salary_amount": float(salary_amount),
            "cycle_start": cycle_start.isoformat() if hasattr(cycle_start, "isoformat") else str(cycle_start),
            "cycle_end": cycle_end.isoformat() if hasattr(cycle_end, "isoformat") else str(cycle_end),
            "created_at": datetime.utcnow().isoformat()
        }
        return cls._execute(lambda: supabase.table("salary_cycles").upsert(data).execute())

    @classmethod
    def save_monthly_spending_summary(cls, summary_id: uuid.UUID, month_key: str, total_spend: float, transaction_count: int) -> bool:
        data = {
            "summary_id": str(summary_id),
            "month_key": month_key,
            "total_spend": float(total_spend),
            "transaction_count": int(transaction_count),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        return cls._execute(lambda: supabase.table("monthly_spending_summary").upsert(data).execute())

    @classmethod
    def save_monthly_financial_summary(cls, summary_id: uuid.UUID, salary_cycle_id: uuid.UUID, salary_amount: float, total_credit: float, total_debit: float, net_savings: float) -> bool:
        # Legacy support
        data = {
            "summary_id": str(summary_id),
            "salary_cycle_id": str(salary_cycle_id),
            "salary_amount": float(salary_amount),
            "total_credit": float(total_credit),
            "total_debit": float(total_debit),
            "net_savings": float(net_savings),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        return cls._execute(lambda: supabase.table("monthly_financial_summary").upsert(data).execute())

    @classmethod
    def save_monthly_category_spend(cls, entry_id: uuid.UUID, month_key: str, category_name: str, amount: float, transaction_count: int) -> bool:
        data = {
            "entry_id": str(entry_id),
            "month_key": month_key,
            "category_name": category_name,
            "amount": float(amount),
            "transaction_count": int(transaction_count),
            "created_at": datetime.utcnow().isoformat()
        }
        return cls._execute(lambda: supabase.table("monthly_category_spend").upsert(data).execute())

    @classmethod
    def save_monthly_category_trend(cls, trend_id: uuid.UUID, month_key: str, category_name: str, current_amount: float, previous_amount: float, change_percentage: float) -> bool:
        data = {
            "trend_id": str(trend_id),
            "month_key": month_key,
            "category_name": category_name,
            "current_amount": float(current_amount),
            "previous_amount": float(previous_amount),
            "change_percentage": float(change_percentage),
            "created_at": datetime.utcnow().isoformat()
        }
        return cls._execute(lambda: supabase.table("monthly_category_trends").upsert(data).execute())

    @classmethod
    def save_transaction_classification(cls, classification_id: uuid.UUID, financial_event_id: uuid.UUID, classification: str, confidence: float) -> bool:
        data = {
            "transaction_id": str(classification_id),
            "financial_event_id": str(financial_event_id),
            "classification": classification,
            "confidence": float(confidence),
            "created_at": datetime.utcnow().isoformat()
        }
        return cls._execute(lambda: supabase.table("financial_transaction_classification").upsert(data).execute())

    @classmethod
    def fetch_salary_cycles(cls) -> list[dict]:
        try:
            res = supabase.table("salary_cycles").select("*").order("cycle_start", desc=True).execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Failed to fetch salary cycles: {e}")
            return []

    @classmethod
    def fetch_monthly_spending_summaries(cls) -> list[dict]:
        try:
            res = supabase.table("monthly_spending_summary").select("*").order("month_key", desc=True).execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Failed to fetch spending summaries: {e}")
            return []

    @classmethod
    def fetch_monthly_financial_summaries(cls) -> list[dict]:
        # Backward compatibility mapping
        try:
            res = supabase.table("monthly_spending_summary").select("*").order("month_key", desc=True).execute()
            mapped = []
            for item in (res.data or []):
                mapped.append({
                    "summary_id": item.get("summary_id"),
                    "salary_cycle_id": item.get("summary_id"),
                    "salary_amount": 0.0,
                    "total_credit": 0.0,
                    "total_debit": float(item.get("total_spend") or 0.0),
                    "net_savings": 0.0,
                    "created_at": item.get("created_at"),
                    "updated_at": item.get("updated_at"),
                    "month_key": item.get("month_key")
                })
            return mapped
        except Exception as e:
            logger.error(f"Failed to fetch financial summaries: {e}")
            return []

    @classmethod
    def fetch_monthly_category_spends(cls, month_key: str = None) -> list[dict]:
        try:
            q = supabase.table("monthly_category_spend").select("*")
            if month_key:
                q = q.eq("month_key", str(month_key))
            res = q.execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Failed to fetch category spends: {e}")
            return []

    @classmethod
    def fetch_monthly_category_trends(cls, month_key: str = None) -> list[dict]:
        try:
            q = supabase.table("monthly_category_trends").select("*")
            if month_key:
                q = q.eq("month_key", str(month_key))
            res = q.execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Failed to fetch category trends: {e}")
            return []

    @classmethod
    def clear_summary_tables(cls) -> bool:
        """Clears all summary tables in Supabase to allow clean backfills/recomputations."""
        try:
            supabase.table("monthly_category_trends").delete().neq("trend_id", "00000000-0000-0000-0000-000000000000").execute()
            supabase.table("monthly_category_spend").delete().neq("entry_id", "00000000-0000-0000-0000-000000000000").execute()
            supabase.table("monthly_spending_summary").delete().neq("summary_id", "00000000-0000-0000-0000-000000000000").execute()
            # Also delete classification table entries
            supabase.table("financial_transaction_classification").delete().neq("transaction_id", "00000000-0000-0000-0000-000000000000").execute()
            return True
        except Exception as e:
            logger.error(f"Failed to clear summary tables: {e}")
            return False

    @classmethod
    def register_processed_file(cls, file_name: str, bucket_name: str, file_path: str, file_hash: str, status: str) -> bool:
        data = {
            "file_name": file_name,
            "bucket_name": bucket_name,
            "file_path": file_path,
            "file_hash": file_hash,
            "status": status,
            "processed_timestamp": datetime.utcnow().isoformat()
        }
        return cls._execute(lambda: supabase.table("processed_files").upsert(data).execute())

