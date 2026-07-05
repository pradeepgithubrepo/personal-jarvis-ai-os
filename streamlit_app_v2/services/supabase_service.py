# streamlit_app_v2/services/supabase_service.py

import sys
import os
import streamlit as st

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from services.supabase_repo import supabase

class SupabaseService:

    @staticmethod
    @st.cache_data(ttl=60)
    def fetch_dashboard_summary():
        """Fetches card metric summaries."""
        try:
            tasks_res = supabase.table("todo_items").select("status, priority").execute()
            tasks = tasks_res.data or []
            open_tasks = [t for t in tasks if t["status"] != "COMPLETED"]
            high_priority = [t for t in open_tasks if t["priority"].upper() == "HIGH"]

            fyi_res = supabase.table("fyi_events").select("status").execute()
            fyi = fyi_res.data or []
            unread_fyi = [f for f in fyi if f["status"].upper() == "UNREAD"]

            fin_res = supabase.table("financial_events").select("id").execute()
            fin_count = len(fin_res.data or [])

            sig_res = supabase.table("qualified_signals").select("id").execute()
            sig_count = len(sig_res.data or [])

            return {
                "open_tasks": len(open_tasks),
                "high_priority": len(high_priority),
                "unread_fyi": len(unread_fyi),
                "financial_events": fin_count,
                "new_signals_24h": sig_count
            }
        except Exception as e:
            st.error(f"Error fetching dashboard summary: {e}")
            return {"open_tasks": 0, "high_priority": 0, "unread_fyi": 0, "financial_events": 0, "new_signals_24h": 0}

    @staticmethod
    @st.cache_data(ttl=60)
    def fetch_daily_briefs():
        """Fetches the latest morning and evening briefs."""
        try:
            res = supabase.table("daily_briefs").select("*").order("generated_at", desc=True).limit(5).execute()
            return res.data or []
        except Exception as e:
            st.error(f"Error fetching briefs: {e}")
            return []

    @staticmethod
    def fetch_tasks(filter_type="All"):
        """Fetches tasks from Supabase with interactive updates (no caching to ensure fresh action states)."""
        try:
            res = supabase.table("todo_items").select("*").order("created_at", desc=True).execute()
            tasks = res.data or []
            
            # Filter
            if filter_type == "Open":
                return [t for t in tasks if t["status"] != "COMPLETED"]
            elif filter_type == "Completed":
                return [t for t in tasks if t["status"] == "COMPLETED"]
            elif filter_type == "High Priority":
                return [t for t in tasks if t["priority"].upper() == "HIGH"]
            elif filter_type == "Financial":
                return [t for t in tasks if t["category"].upper() == "FINANCIAL"]
            elif filter_type == "Family":
                return [t for t in tasks if t["category"].upper() == "FAMILY"]
            return tasks
        except Exception as e:
            st.error(f"Error fetching tasks: {e}")
            return []

    @staticmethod
    def complete_task(todo_id):
        """Updates task status to completed."""
        try:
            supabase.table("todo_items").update({
                "status": "COMPLETED",
                "updated_at": "now()"
            }).eq("todo_id", todo_id).execute()
            st.cache_data.clear()
            return True
        except Exception as e:
            st.error(f"Error completing task: {e}")
            return False

    @staticmethod
    def delete_task(todo_id):
        """Deletes task from Supabase."""
        try:
            supabase.table("todo_items").delete().eq("todo_id", todo_id).execute()
            st.cache_data.clear()
            return True
        except Exception as e:
            st.error(f"Error deleting task: {e}")
            return False

    @staticmethod
    @st.cache_data(ttl=60)
    def fetch_fyi_events():
        """Fetches FYI awareness notifications."""
        try:
            res = supabase.table("fyi_events").select("*").order("created_at", desc=True).execute()
            return res.data or []
        except Exception as e:
            st.error(f"Error fetching FYIs: {e}")
            return []

    @staticmethod
    def mark_fyi_read(event_id):
        """Marks FYI notification as read."""
        try:
            supabase.table("fyi_events").update({
                "status": "READ",
                "updated_at": "now()"
            }).eq("event_id", event_id).execute()
            st.cache_data.clear()
            return True
        except Exception as e:
            st.error(f"Error marking FYI as read: {e}")
            return False

    @staticmethod
    def delete_fyi(event_id):
        """Deletes FYI event from Supabase."""
        try:
            supabase.table("fyi_events").delete().eq("event_id", event_id).execute()
            st.cache_data.clear()
            return True
        except Exception as e:
            st.error(f"Error deleting FYI: {e}")
            return False

    @staticmethod
    @st.cache_data(ttl=60)
    def fetch_memory_facts():
        """Fetches user facts and relationships for knowledge graphs."""
        try:
            facts_res = supabase.table("facts").select("*").order("updated_at", desc=True).execute()
            rel_res = supabase.table("fact_relationships").select("*").execute()
            return {
                "facts": facts_res.data or [],
                "relationships": rel_res.data or []
            }
        except Exception as e:
            st.error(f"Error fetching memory facts: {e}")
            return {"facts": [], "relationships": []}

    @staticmethod
    @st.cache_data(ttl=60)
    def fetch_financial_summaries():
        """Fetches financial data summaries."""
        try:
            spending = supabase.table("monthly_spending_summary").select("*").order("month_key", desc=True).execute()
            categories = supabase.table("monthly_category_spend").select("*").execute()
            trends = supabase.table("monthly_category_trends").select("*").execute()
            events = supabase.table("financial_events").select("*").order("event_date", desc=True).execute()
            return {
                "spending": spending.data or [],
                "categories": categories.data or [],
                "trends": trends.data or [],
                "events": events.data or []
            }
        except Exception as e:
            st.error(f"Error fetching financial summaries: {e}")
            return {"spending": [], "categories": [], "trends": [], "events": []}

    @staticmethod
    @st.cache_data(ttl=60)
    def fetch_signals_metrics():
        """Fetches signal throughput metrics."""
        try:
            raw = supabase.table("signals").select("id, created_at, source").execute()
            qualified = supabase.table("qualified_signals").select("id, created_at, qualification_status").execute()
            understood = supabase.table("understood_signals").select("id, created_at, signal_type, processing_path").execute()
            return {
                "raw": raw.data or [],
                "qualified": qualified.data or [],
                "understood": understood.data or []
            }
        except Exception as e:
            st.error(f"Error fetching signals metrics: {e}")
            return {"raw": [], "qualified": [], "understood": []}

    @staticmethod
    @st.cache_data(ttl=10)
    def fetch_diagnostics():
        """Fetches troubleshooting metrics and throughput."""
        try:
            status_res = supabase.table("system_status").select("*").eq("system_name", "jarvis_system").execute()
            runs_res = supabase.table("pipeline_runs").select("*").order("started_at", desc=True).limit(10).execute()
            return {
                "status": status_res.data[0] if (status_res.data) else None,
                "runs": runs_res.data or []
            }
        except Exception as e:
            st.error(f"Error fetching diagnostics: {e}")
            return {"status": None, "runs": []}
