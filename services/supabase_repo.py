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
    def create_todo(cls, todo_id: uuid.UUID, title: str, description: str, priority: str, status: str, due_date: datetime, source_signal_id: uuid.UUID, created_at: datetime = None) -> bool:
        data = {
            "todo_id": str(todo_id),
            "title": title,
            "description": description,
            "priority": priority,
            "status": status,
            "due_date": due_date.isoformat() if hasattr(due_date, "isoformat") else str(due_date) if due_date else None,
            "source_signal_id": str(source_signal_id) if source_signal_id else None,
            "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at) if created_at else datetime.utcnow().isoformat(),
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
    def create_financial_event(cls, event_id: uuid.UUID, merchant: str, amount: float, currency: str, category: str, status: str, event_timestamp: datetime, source_signal_id: uuid.UUID, created_at: datetime = None) -> bool:
        data = {
            "financial_event_id": str(event_id),
            "merchant": merchant,
            "amount": float(amount) if amount is not None else 0.0,
            "currency": currency,
            "category": category,
            "status": status,
            "event_timestamp": event_timestamp.isoformat() if hasattr(event_timestamp, "isoformat") else str(event_timestamp) if event_timestamp else None,
            "source_signal_id": str(source_signal_id) if source_signal_id else None,
            "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at) if created_at else datetime.utcnow().isoformat(),
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
    def create_fyi_event(cls, event_id: uuid.UUID, title: str, summary: str, category: str, read_flag: bool, source_signal_id: uuid.UUID, created_at: datetime = None) -> bool:
        data = {
            "fyi_event_id": str(event_id),
            "title": title,
            "summary": summary,
            "category": category,
            "read_flag": read_flag,
            "source_signal_id": str(source_signal_id) if source_signal_id else None,
            "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at) if created_at else datetime.utcnow().isoformat(),
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
    def store_fact(
        cls,
        fact_id,
        fact_type: str = None,
        fact_value: dict = None,
        confidence: float = 0.5,
        status: str = "UNCONFIRMED",
        owner_agent: str = None,
        source_agent: str = None,
        source_type: str = "OBSERVED",
        first_seen: datetime = None,
        last_seen: datetime = None,
        evidence: dict = None,
        created_at: datetime = None,
        updated_at: datetime = None,
        # Legacy compatibility arguments
        entity: str = None,
        fact: str = None,
        source_signal_id = None
    ) -> bool:
        # Backward compatibility layer
        if fact_type is None:
            data = {
                "fact_id": str(fact_id),
                "entity": entity,
                "fact": fact,
                "confidence": float(confidence) if confidence is not None else 1.0,
                "source_signal_id": str(source_signal_id) if source_signal_id else None,
                "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at) if created_at else datetime.utcnow().isoformat()
            }
        else:
            data = {
                "fact_id": str(fact_id),
                "fact_type": fact_type,
                "fact_value": fact_value,
                "confidence": float(confidence),
                "status": status,
                "owner_agent": owner_agent,
                "source_agent": source_agent,
                "source_type": source_type,
                "first_seen": first_seen.isoformat() if hasattr(first_seen, "isoformat") else str(first_seen) if first_seen else datetime.utcnow().isoformat(),
                "last_seen": last_seen.isoformat() if hasattr(last_seen, "isoformat") else str(last_seen) if last_seen else datetime.utcnow().isoformat(),
                "evidence": evidence,
                "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at) if created_at else datetime.utcnow().isoformat(),
                "updated_at": updated_at.isoformat() if hasattr(updated_at, "isoformat") else str(updated_at) if updated_at else datetime.utcnow().isoformat()
            }
        return cls._execute(lambda: supabase.table("facts").upsert(data).execute())

    @classmethod
    def store_fact_relationship(
        cls,
        rel_id: int,
        subject_id: str,
        predicate: str,
        object_id: str,
        confidence: float,
        created_at: datetime = None,
        updated_at: datetime = None
    ) -> bool:
        data = {
            "id": int(rel_id),
            "subject_id": str(subject_id),
            "predicate": predicate,
            "object_id": str(object_id),
            "confidence": float(confidence),
            "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at) if created_at else datetime.utcnow().isoformat(),
            "updated_at": updated_at.isoformat() if hasattr(updated_at, "isoformat") else str(updated_at) if updated_at else datetime.utcnow().isoformat()
        }
        return cls._execute(lambda: supabase.table("fact_relationships").upsert(data).execute())

    @classmethod
    def attempt_fact_tables_creation(cls) -> bool:
        """
        Verifies if facts and fact_relationships tables are present and writable on Supabase.
        """
        try:
            supabase.table("facts").select("fact_id").limit(1).execute()
            supabase.table("fact_relationships").select("id").limit(1).execute()
            return True
        except Exception as e:
            logger.warning(f"Supabase tables check failed: {e}")
            return False

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
        """Legacy single-total save — kept for backward compatibility."""
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
    def save_monthly_spending_summary_v2(
        cls,
        summary_id: uuid.UUID,
        month_key: str,
        accounting_spend: float,
        lifestyle_spend: float,
        total_income: float,
        net_cash_flow: float,
        internal_transfers: float,
        insurance_premiums: float,
        investments: float,
        refund_offsets: float,
        transaction_count: int,
        total_debits: float | None = None,
        total_credits: float | None = None,
    ) -> bool:
        """
        Financial Agent V2 — extended monthly summary with split spend views.

        accounting_spend: all debits excl. internal transfers
        lifestyle_spend:  accounting_spend − investments − insurance − cc_payments
        net_cash_flow:    total_income − accounting_spend
        """
        data = {
            "summary_id": str(summary_id),
            "month_key": month_key,
            # Keep total_spend for backward-compat consumers
            "total_spend": float(accounting_spend),
            "total_debits": float(total_debits if total_debits is not None else accounting_spend),
            "total_credits": float(total_credits if total_credits is not None else total_income),
            "accounting_spend": float(accounting_spend),
            "lifestyle_spend": float(lifestyle_spend),
            "total_income": float(total_income),
            "net_cash_flow": float(net_cash_flow),
            "internal_transfers": float(internal_transfers),
            "insurance_premiums": float(insurance_premiums),
            "investments": float(investments),
            "refund_offsets": float(refund_offsets),
            "transaction_count": int(transaction_count),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
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

    @classmethod
    def create_pipeline_run(cls, run_id: uuid.UUID, run_type: str, started_at: datetime, status: str) -> bool:
        data = {
            "run_id": str(run_id),
            "run_type": run_type,
            "started_at": started_at.isoformat() if hasattr(started_at, "isoformat") else str(started_at),
            "status": status
        }
        return cls._execute(lambda: supabase.table("pipeline_runs").insert(data).execute())

    @classmethod
    def update_pipeline_run(cls, run_id: uuid.UUID, status: str, completed_at: datetime, files_processed: int, signals_processed: int, todos_generated: int, financial_events_generated: int, fyi_generated: int, facts_generated: int, llm_calls: int, duration_seconds: float, error_message: str = None, error_type: str = None) -> bool:
        data = {
            "status": status,
            "completed_at": completed_at.isoformat() if hasattr(completed_at, "isoformat") else str(completed_at) if completed_at else None,
            "files_processed": files_processed,
            "signals_processed": signals_processed,
            "todos_generated": todos_generated,
            "financial_events_generated": financial_events_generated,
            "fyi_generated": fyi_generated,
            "facts_generated": facts_generated,
            "llm_calls": llm_calls,
            "duration_seconds": float(duration_seconds),
            "error_message": error_message,
            "error_type": error_type
        }
        return cls._execute(lambda: supabase.table("pipeline_runs").update(data).eq("run_id", str(run_id)).execute())

    @classmethod
    def upsert_system_status(cls, current_status: str, last_successful_refresh: datetime = None, current_run_id: uuid.UUID = None, signals_processed: int = 0, todos_generated: int = 0, financial_events_generated: int = 0, fyi_generated: int = 0) -> bool:
        data = {
            "system_name": "jarvis_system",
            "current_status": current_status,
            "last_successful_refresh": last_successful_refresh.isoformat() if hasattr(last_successful_refresh, "isoformat") else str(last_successful_refresh) if last_successful_refresh else None,
            "current_run_id": str(current_run_id) if current_run_id else None,
            "signals_processed": signals_processed,
            "todos_generated": todos_generated,
            "financial_events_generated": financial_events_generated,
            "fyi_generated": fyi_generated,
            "updated_at": datetime.utcnow().isoformat()
        }
        return cls._execute(lambda: supabase.table("system_status").upsert(data).execute())

    @classmethod
    def fetch_system_status(cls) -> list[dict]:
        try:
            res = supabase.table("system_status").select("*").eq("system_name", "jarvis_system").execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Failed to fetch system status: {e}")
            return []

    @classmethod
    def fetch_pipeline_runs(cls, limit: int = 10) -> list[dict]:
        try:
            res = supabase.table("pipeline_runs").select("*").order("started_at", desc=True).limit(limit).execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Failed to fetch pipeline runs: {e}")
            return []

    @classmethod
    def create_qualified_signal(cls, signal_id: str, source: str, sender: str, message: str, timestamp: datetime, qualification_score: int, qualification_status: str, qualification_reason: str = None) -> bool:
        data = {
            "signal_id": str(signal_id),
            "source": source,
            "sender": sender,
            "message": message,
            "timestamp": timestamp.isoformat() if hasattr(timestamp, "isoformat") else str(timestamp),
            "qualification_score": int(qualification_score),
            "qualification_status": qualification_status,
            "qualification_reason": qualification_reason
        }
        return cls._execute(lambda: supabase.table("qualified_signals").insert(data).execute())

    @classmethod
    def fetch_qualified_signals(cls, limit: int = 50) -> list[dict]:
        try:
            res = supabase.table("qualified_signals").select("*").order("created_at", desc=True).limit(limit).execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Failed to fetch qualified signals: {e}")
            return []

    @classmethod
    def save_understood_signal(
        cls,
        understood_id: uuid.UUID,
        qualified_signal_id: int,
        raw_signal_id: str,
        signal_type: str,
        importance: str,
        confidence: float,
        summary: str,
        reason: str | None,
        processing_path: str,
        llm_model_used: str,
        contract_json: dict,
        is_verified: bool,
        created_at: datetime = None
    ) -> bool:
        data = {
            "id": str(understood_id),
            "qualified_signal_id": qualified_signal_id,
            "raw_signal_id": raw_signal_id,
            "signal_type": signal_type,
            "importance": importance,
            "confidence": float(confidence),
            "summary": summary,
            "reason": reason,
            "processing_path": processing_path,
            "llm_model_used": llm_model_used,
            "contract_json": contract_json,
            "is_verified": is_verified,
            "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at) if created_at else datetime.utcnow().isoformat()
        }
        return cls._execute(lambda: supabase.table("understood_signals").insert(data).execute())

    # =========================================================================
    # Financial Agent V2 — New methods
    # =========================================================================


    @classmethod
    def save_transfer_pair(
        cls,
        pair_id: uuid.UUID,
        debit_event_id: str,
        credit_event_id: str,
        amount: float,
        currency: str,
        transfer_type: str,
        confidence: float,
        window_used_seconds: int,
    ) -> bool:
        """
        Persists a detected internal transfer pair record.
        Gracefully no-ops if the transfer_pairs table does not exist in Supabase yet.
        """
        data = {
            "pair_id": str(pair_id),
            "debit_event_id": str(debit_event_id),
            "credit_event_id": str(credit_event_id),
            "amount": float(amount),
            "currency": currency or "INR",
            "transfer_type": transfer_type,
            "confidence": float(confidence),
            "window_used_seconds": int(window_used_seconds),
            "detected_at": datetime.utcnow().isoformat(),
        }
        return cls._execute(lambda: supabase.table("transfer_pairs").upsert(data).execute())

    @classmethod
    def fetch_financial_events_by_month(cls, month_key: str) -> list[dict]:
        """
        Fetches all financial events for a given month (YYYY-MM).
        Filters by event_timestamp prefix match.
        """
        try:
            start = f"{month_key}-01T00:00:00"
            # Compute end: increment month
            year, month = int(month_key[:4]), int(month_key[5:7])
            if month == 12:
                end_year, end_month = year + 1, 1
            else:
                end_year, end_month = year, month + 1
            end = f"{end_year:04d}-{end_month:02d}-01T00:00:00"

            res = (
                supabase.table("financial_events")
                .select("*")
                .gte("event_timestamp", start)
                .lt("event_timestamp", end)
                .execute()
            )
            return res.data or []
        except Exception as e:
            logger.error(f"Failed to fetch financial events for month '{month_key}': {e}")
            return []

    @classmethod
    def fetch_financial_events_by_subtype(cls, subtype: str) -> list[dict]:
        """
        Fetches financial events filtered by transaction_subtype field.
        Used for salary event and refund event lookups.
        Gracefully returns empty list if column does not exist yet.
        """
        try:
            res = (
                supabase.table("financial_events")
                .select("*")
                .eq("transaction_subtype", subtype)
                .execute()
            )
            return res.data or []
        except Exception as e:
            logger.warning(f"fetch_financial_events_by_subtype('{subtype}') failed (column may not exist): {e}")
            return []

    @classmethod
    def update_monthly_category_spend_with_refund(
        cls, month_key: str, category_name: str, refund_amount: float
    ) -> bool:
        """
        Reduces a category's monthly spend by refund_amount (refund offset).
        Fetches current amount and upserts the corrected value.
        """
        try:
            res = (
                supabase.table("monthly_category_spend")
                .select("entry_id, amount")
                .eq("month_key", month_key)
                .eq("category_name", category_name)
                .execute()
            )
            rows = res.data or []
            if not rows:
                logger.warning(
                    f"No category spend row found for month={month_key} category={category_name}; "
                    "refund offset not applied."
                )
                return False

            row = rows[0]
            current_amount = float(row.get("amount") or 0.0)
            adjusted = max(0.0, current_amount - float(refund_amount))

            update_data = {
                "amount": adjusted,
                "updated_at": datetime.utcnow().isoformat(),
            }
            return cls._execute(
                lambda: supabase.table("monthly_category_spend")
                .update(update_data)
                .eq("entry_id", row["entry_id"])
                .execute()
            )
        except Exception as e:
            logger.error(f"Failed to apply refund offset to category spend: {e}")
            return False

    @classmethod
    def store_todo_item(
        cls,
        todo_id,
        title: str,
        description: str,
        category: str,
        priority: str,
        status: str,
        due_date: datetime,
        source_agent: str,
        source_reference: dict,
        confidence: float,
        created_at: datetime = None,
        updated_at: datetime = None
    ) -> bool:
        data = {
            "todo_id": str(todo_id),
            "title": title,
            "description": description,
            "category": category,
            "priority": priority,
            "status": status,
            "due_date": due_date.isoformat() if hasattr(due_date, "isoformat") else str(due_date) if due_date else None,
            "source_agent": source_agent,
            "source_reference": source_reference,
            "confidence": float(confidence),
            "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at) if created_at else datetime.utcnow().isoformat(),
            "updated_at": updated_at.isoformat() if hasattr(updated_at, "isoformat") else str(updated_at) if updated_at else datetime.utcnow().isoformat()
        }
        return cls._execute(lambda: supabase.table("todo_items").upsert(data).execute())

    @classmethod
    def attempt_todo_tables_creation(cls) -> bool:
        """
        Verifies if the todo_items table is present and writable on Supabase.
        """
        try:
            supabase.table("todo_items").select("todo_id").limit(1).execute()
            return True
        except Exception as e:
            logger.warning(f"Supabase todo table check failed: {e}")
            return False

    @classmethod
    def store_fyi_event(
        cls,
        event_id,
        event_type: str,
        category: str,
        title: str,
        description: str,
        importance: str,
        status: str,
        source_signal_id,
        duplicate_count: int,
        created_at: datetime = None,
        updated_at: datetime = None
    ) -> bool:
        data = {
            "event_id": str(event_id),
            "event_type": event_type,
            "category": category,
            "title": title,
            "description": description,
            "importance": importance,
            "status": status,
            "source_signal_id": str(source_signal_id) if source_signal_id else None,
            "duplicate_count": int(duplicate_count),
            "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at) if created_at else datetime.utcnow().isoformat(),
            "updated_at": updated_at.isoformat() if hasattr(updated_at, "isoformat") else str(updated_at) if updated_at else datetime.utcnow().isoformat()
        }
        return cls._execute(lambda: supabase.table("fyi_events").upsert(data).execute())

    @classmethod
    def attempt_fyi_tables_creation(cls) -> bool:
        """
        Verifies if the fyi_events table is present and writable on Supabase.
        """
        try:
            supabase.table("fyi_events").select("event_id").limit(1).execute()
            return True
        except Exception as e:
            logger.warning(f"Supabase fyi table check failed: {e}")
            return False

    @classmethod
    def store_daily_brief(
        cls,
        brief_id,
        brief_type: str,
        generated_at: datetime,
        content: str,
        todo_count: int,
        fyi_count: int,
        fact_count: int
    ) -> bool:
        data = {
            "brief_id": str(brief_id),
            "brief_type": brief_type,
            "generated_at": generated_at.isoformat() if hasattr(generated_at, "isoformat") else str(generated_at) if generated_at else datetime.utcnow().isoformat(),
            "content": content,
            "todo_count": int(todo_count),
            "fyi_count": int(fyi_count),
            "fact_count": int(fact_count)
        }
        return cls._execute(lambda: supabase.table("daily_briefs").upsert(data).execute())

    @classmethod
    def attempt_brief_tables_creation(cls) -> bool:
        """
        Verifies if the daily_briefs table is present and writable on Supabase.
        """
        try:
            supabase.table("daily_briefs").select("brief_id").limit(1).execute()
            return True
        except Exception as e:
            logger.warning(f"Supabase daily briefs check failed: {e}")
            return False
