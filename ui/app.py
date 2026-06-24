# ui/app.py

import os
import sys
from datetime import datetime, timedelta
import streamlit as st

# Add root folder to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ui.cache_manager import CacheManager
from ui.pages import (
    render_todos_page,
    render_financial_page,
    render_fyi_page,
    render_daily_brief_page,
    render_family_page,
    render_school_page,
    render_travel_page,
    render_health_page
)

# Page configuration
st.set_page_config(
    page_title="Jarvis Desktop Companion",
    page_icon="☀️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load CSS stylesheet
CSS_FILE = os.path.join(os.path.dirname(__file__), "styles.css")
if os.path.exists(CSS_FILE):
    with open(CSS_FILE, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# State initialization
if "current_page" not in st.session_state:
    st.session_state.current_page = "Landing Page"

from services.supabase_repo import SupabaseRepo

@st.cache_data(ttl=60)
def fetch_live_todos():
    db_todos = SupabaseRepo.fetch_todos()
    todos_list = []
    for t in db_todos:
        status_mapped = "completed" if t.get("status") == "COMPLETED" else "pending"
        due_dt_str = None
        if t.get("due_date"):
            try:
                due_dt_str = t.get("due_date").split("T")[0]
            except Exception:
                due_dt_str = str(t.get("due_date"))
        title_lower = (t.get("title") or "").lower()
        if "school" in title_lower or "class" in title_lower or "term" in title_lower:
            category = "School"
        elif "bill" in title_lower or "insurance" in title_lower or "pay" in title_lower or "credit card" in title_lower:
            category = "Financial"
        elif "pack" in title_lower or "travel" in title_lower or "mumbai" in title_lower or "flight" in title_lower:
            category = "Travel"
        elif "health" in title_lower or "dentist" in title_lower or "doctor" in title_lower or "appointment" in title_lower:
            category = "Health"
        else:
            category = "General"
            
        todos_list.append({
            "id": t.get("todo_id"),
            "title": t.get("title"),
            "status": status_mapped,
            "due_date": due_dt_str,
            "priority": t.get("priority", "low").lower(),
            "category": category
        })
    
    # Fallback to mock data if database returned no todos
    if not todos_list:
        mock_todos = CacheManager.load_insight("todos.json")
        todos_list = mock_todos.get("todos", [])
        
    return {"todos": todos_list, "last_updated": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")}

@st.cache_data(ttl=10)
def fetch_live_financial():
    from services.supabase_repo import SupabaseRepo

    try:
        summaries = SupabaseRepo.fetch_monthly_spending_summaries()
        category_spends = SupabaseRepo.fetch_monthly_category_spends()
        trends = SupabaseRepo.fetch_monthly_category_trends()

        months_data = []
        for summary in summaries:
            month_key = summary.get("month_key")
            try:
                dt = datetime.strptime(month_key, "%Y-%m")
                month_name = dt.strftime("%B %Y")
            except Exception:
                month_name = month_key

            month_spends = [cs for cs in category_spends if cs.get("month_key") == month_key]
            category_spend_map = {cs.get("category_name"): float(cs.get("amount") or 0) for cs in month_spends}
            
            summary_info = {
                "expenses": float(summary.get("total_spend") or 0.0),
                "transaction_count": int(summary.get("transaction_count") or 0)
            }
            
            months_data.append({
                "month_key": month_key,
                "month": month_name,
                "summary": summary_info,
                "spend_categories": category_spend_map
            })

        trends_data = []
        for t in trends:
            m_key = t.get("month_key")
            try:
                dt = datetime.strptime(m_key, "%Y-%m")
                month_name = dt.strftime("%B %Y")
            except Exception:
                month_name = m_key

            trends_data.append({
                "month": month_name,
                "month_key": m_key,
                "category_name": t.get("category_name"),
                "current_amount": float(t.get("current_amount") or 0),
                "previous_amount": float(t.get("previous_amount") or 0),
                "change_percentage": float(t.get("change_percentage") or 0)
            })

        return {
            "months": months_data,
            "trends": trends_data,
            "alerts": [],
            "last_updated": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        }
    except Exception as e:
        return {
            "months": [],
            "trends": [],
            "alerts": [],
            "last_updated": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        }

@st.cache_data(ttl=60)
def fetch_live_fyi():
    db_fyis = SupabaseRepo.fetch_fyi_events()
    updates = []
    for f in db_fyis:
        category = f.get("category", "general")
        if "school" in category:
            ui_cat = "school"
        elif "family" in category:
            ui_cat = "family"
        elif "delivery" in category:
            ui_cat = "delivery"
        else:
            ui_cat = "general"
            
        timestamp_str = f.get("created_at") or f.get("updated_at") or datetime.now().isoformat()
        
        updates.append({
            "title": f.get("title"),
            "category": ui_cat,
            "timestamp": timestamp_str,
            "content": f.get("summary") or f.get("title")
        })
        
    if not updates:
        mock_fyi = CacheManager.load_insight("fyi.json")
        updates = mock_fyi.get("updates", [])
        
    return {"updates": updates, "last_updated": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")}

# Fetch Live Data
todos_data = fetch_live_todos()
fin_data = fetch_live_financial()
fyi_data = fetch_live_fyi()

# Dynamically construct Daily Brief
@st.cache_data(ttl=60)
def fetch_live_daily_brief():
    priorities = [t.get("title") for t in todos_data.get("todos", []) if t.get("priority") == "high" and t.get("status") == "pending"]
    if not priorities:
        priorities = [t.get("title") for t in todos_data.get("todos", []) if t.get("status") == "pending"][:3]
    
    fin_alerts = fin_data.get("alerts", [])
    
    family_updates = [f.get("content") for f in fyi_data.get("updates", []) if f.get("category") == "family"][:3]
    if not family_updates:
        family_updates = ["No new family updates."]
        
    school_circulars = [f.get("content") for f in fyi_data.get("updates", []) if f.get("category") == "school"][:3]
    if not school_circulars:
        school_circulars = ["No new school circulars."]
        
    important_reminders = [t.get("title") for t in todos_data.get("todos", []) if t.get("priority") == "medium" and t.get("status") == "pending"]
    if not important_reminders:
        important_reminders = ["Car service due by end of this week.", "Annual health checkup appointment tomorrow at 10:00 AM."]
        
    return {
        "greeting": "Good Morning Pradeep",
        "priorities": priorities[:3] if priorities else ["No pending priorities."],
        "financial_alerts": fin_alerts,
        "family_updates": family_updates,
        "school_circulars": school_circulars,
        "important_reminders": important_reminders[:2],
        "last_updated": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    }

brief_data = fetch_live_daily_brief()

# Fallback JSON cache loaders for other categories
family_data = CacheManager.load_insight("family.json")
school_data = CacheManager.load_insight("school.json")
travel_data = CacheManager.load_insight("travel.json")
health_data = CacheManager.load_insight("health.json")

# Helper stats extraction for tiles and summary cards
pending_todos = [t for t in todos_data.get("todos", []) if t.get("status") == "pending"]
todo_count = len(pending_todos)
fin_alerts_count = len(fin_data.get("alerts", []))
fyi_count = len(fyi_data.get("updates", []))
last_refresh_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
last_storage_sync = CacheManager.get_last_refresh_time()

# Sidebar controls
st.sidebar.title("☀️ Jarvis Companion")
st.sidebar.markdown(f"**Last Sync (Postgres Live):** {last_refresh_time}")
st.sidebar.markdown(f"**Last Storage Sync:** {last_storage_sync}")

# Trigger Orchestrated Ingestion/LLM Pipeline
if st.sidebar.button("🔄 Trigger Refresh Pipeline", use_container_width=True):
    with st.spinner("Executing sequential pipeline run..."):
        from services.pipeline_orchestrator import PipelineOrchestrator
        res = PipelineOrchestrator.run_pipeline(run_type="ADHOC")
        st.cache_data.clear()
        if res.get("status") == "SUCCESS":
            st.sidebar.success("Pipeline executed successfully!")
        elif res.get("status") == "SKIPPED_LOCKED":
            st.sidebar.warning("Pipeline is already running!")
        else:
            st.sidebar.error(f"Pipeline failed: {res.get('message')}")
        st.rerun()

st.sidebar.markdown("---")

# Navigation Menu
nav_options = [
    "Landing Page",
    "Daily Brief",
    "Todos",
    "Financial",
    "FYI",
    "Family",
    "School",
    "Travel",
    "Health"
]

selected_page = st.sidebar.radio("Navigate", nav_options, index=nav_options.index(st.session_state.current_page))
if selected_page != st.session_state.current_page:
    st.session_state.current_page = selected_page
    st.rerun()

def fetch_system_status_from_db():
    from services.supabase_repo import SupabaseRepo
    from loguru import logger
    try:
        class DictObject:
            def __init__(self, d):
                self._d = d or {}
            def __getattr__(self, name):
                val = self._d.get(name)
                if name in ('last_successful_refresh', 'started_at', 'completed_at', 'updated_at') and isinstance(val, str):
                    try:
                        return datetime.fromisoformat(val.replace("Z", "+00:00")).replace(tzinfo=None)
                    except Exception:
                        pass
                return val

        status_list = SupabaseRepo.fetch_system_status()
        status_rec = DictObject(status_list[0]) if status_list else None
        
        runs_list = SupabaseRepo.fetch_pipeline_runs(limit=5)
        runs_rec = [DictObject(r) for r in runs_list]
        return status_rec, runs_rec
    except Exception as e:
        logger.error(f"Failed to fetch system status from Supabase: {e}")
        return None, []

# RENDER PAGES
if st.session_state.current_page == "Landing Page":
    # Header
    greeting = brief_data.get("greeting", "Good Morning Pradeep")
    st.title(greeting)
    st.markdown("Here is your desktop summary of Jarvis insights.")
    st.markdown("---")

    # Render Operational Health Status View
    status_rec, runs_rec = fetch_system_status_from_db()
    if status_rec:
        st.markdown(f"### ⚙️ System Status: **{status_rec.current_status}**")
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            st.metric("Last Successful Refresh", status_rec.last_successful_refresh.strftime("%Y-%m-%d %H:%M:%S") if status_rec.last_successful_refresh else "N/A")
        with col_s2:
            st.metric("Signals Processed (Last Run)", status_rec.signals_processed)
        with col_s3:
            st.metric("Todos / Fin Events / FYIs", f"{status_rec.todos_generated} / {status_rec.financial_events_generated} / {status_rec.fyi_generated}")
        
        if runs_rec:
            with st.expander("Recent Pipeline Execution History"):
                for r in runs_rec:
                    st.write(f"⏱️ **{r.started_at.strftime('%Y-%m-%d %H:%M')}** | Type: `{r.run_type}` | Status: `{r.status}` | Duration: `{r.duration_seconds:.1f}s` | LLM Calls: `{r.llm_calls}`" + (f" | Error: `{r.error_message}`" if r.status == "FAILED" else ""))
        st.markdown("---")
    
    # Summary Card
    st.markdown(
        f"""
        <div class="summary-container">
            <div class="summary-title">Dashboard Overview</div>
            <div style="display: flex; justify-content: space-between; flex-wrap: wrap; gap: 20px;">
                <div>
                    <div style="font-size: 0.9rem; color: #8b949e;">📋 Todo Count</div>
                    <div style="font-size: 2rem; font-weight: 700; color: #ffffff;">{todo_count} Pending</div>
                </div>
                <div>
                    <div style="font-size: 0.9rem; color: #8b949e;">⚠️ Financial Alerts</div>
                    <div style="font-size: 2rem; font-weight: 700; color: #ff7b72;">{fin_alerts_count} Active</div>
                </div>
                <div>
                    <div style="font-size: 0.9rem; color: #8b949e;">ℹ️ FYI Updates</div>
                    <div style="font-size: 2rem; font-weight: 700; color: #58a6ff;">{fyi_count} Updates</div>
                </div>
                <div>
                    <div style="font-size: 0.9rem; color: #8b949e;">🕒 Last Sync Time</div>
                    <div style="font-size: 2rem; font-weight: 700; color: #56d364;">{last_refresh_time.split()[-1] if ' ' in last_refresh_time else last_refresh_time}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    st.markdown("### Agent Tiles")
    
    # Grid of tiles
    col1, col2, col3, col4 = st.columns(4)
    
    # 1. Daily Brief Tile
    with col1:
        priorities_count = len(brief_data.get("priorities", []))
        st.markdown(
            f"""
            <div class="agent-tile">
                <div class="tile-header">
                    <span class="tile-title">☀️ Daily Brief</span>
                    <span class="tile-badge">{priorities_count}</span>
                </div>
                <div class="tile-status">Priorities: {brief_data.get('priorities', ['None'])[0]}...</div>
                <div class="tile-footer">Updated: {brief_data.get('last_updated', 'N/A')}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("Open Daily Brief", key="open_brief", use_container_width=True):
            st.session_state.current_page = "Daily Brief"
            st.rerun()

    # 2. Todos Tile
    with col2:
        due_today = sum(1 for t in todos_data.get("todos", []) if t.get("due_date") == "2026-06-22" and t.get("status") == "pending")
        st.markdown(
            f"""
            <div class="agent-tile">
                <div class="tile-header">
                    <span class="tile-title">📋 Todos</span>
                    <span class="tile-badge">{todo_count}</span>
                </div>
                <div class="tile-status">Due Today: {due_today} pending</div>
                <div class="tile-footer">Updated: {todos_data.get('last_updated', 'N/A')}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("Open Todos", key="open_todos", use_container_width=True):
            st.session_state.current_page = "Todos"
            st.rerun()

    # 3. Financial Tile
    with col3:
        bills_count = len(fin_data.get("upcoming_bills", []))
        st.markdown(
            f"""
            <div class="agent-tile">
                <div class="tile-header">
                    <span class="tile-title">💳 Financial</span>
                    <span class="tile-badge">{bills_count}</span>
                </div>
                <div class="tile-status">Alerts: {fin_alerts_count} active</div>
                <div class="tile-footer">Updated: {fin_data.get('last_updated', 'N/A')}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("Open Financial", key="open_financial", use_container_width=True):
            st.session_state.current_page = "Financial"
            st.rerun()

    # 4. FYI Tile
    with col4:
        st.markdown(
            f"""
            <div class="agent-tile">
                <div class="tile-header">
                    <span class="tile-title">ℹ️ FYI</span>
                    <span class="tile-badge">{fyi_count}</span>
                </div>
                <div class="tile-status">Latest: {fyi_data.get('updates', [{}])[0].get('title', 'None')}</div>
                <div class="tile-footer">Updated: {fyi_data.get('last_updated', 'N/A')}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("Open FYI", key="open_fyi", use_container_width=True):
            st.session_state.current_page = "FYI"
            st.rerun()

    # Second row of tiles
    col5, col6, col7, col8 = st.columns(4)
    
    # 5. Family Tile
    with col5:
        fam_items = len(family_data.get("messages", [])) + len(family_data.get("events", [])) + len(family_data.get("reminders", []))
        st.markdown(
            f"""
            <div class="agent-tile">
                <div class="tile-header">
                    <span class="tile-title">👨‍👩‍👧 Family</span>
                    <span class="tile-badge">{fam_items}</span>
                </div>
                <div class="tile-status">Messages: {len(family_data.get('messages', []))} inbox</div>
                <div class="tile-footer">Updated: {family_data.get('last_updated', 'N/A')}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("Open Family", key="open_family", use_container_width=True):
            st.session_state.current_page = "Family"
            st.rerun()

    # 6. School Tile
    with col6:
        school_items = len(school_data.get("circulars", [])) + len(school_data.get("homework", []))
        st.markdown(
            f"""
            <div class="agent-tile">
                <div class="tile-header">
                    <span class="tile-title">🏫 School</span>
                    <span class="tile-badge">{school_items}</span>
                </div>
                <div class="tile-status">Homework: {len(school_data.get('homework', []))} pending</div>
                <div class="tile-footer">Updated: {school_data.get('last_updated', 'N/A')}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("Open School", key="open_school", use_container_width=True):
            st.session_state.current_page = "School"
            st.rerun()

    # 7. Travel Tile
    with col7:
        bookings_count = len(travel_data.get("bookings", []))
        st.markdown(
            f"""
            <div class="agent-tile">
                <div class="tile-header">
                    <span class="tile-title">✈️ Travel</span>
                    <span class="tile-badge">{bookings_count}</span>
                </div>
                <div class="tile-status">Tickets: {len(travel_data.get('tickets', []))} booked</div>
                <div class="tile-footer">Updated: {travel_data.get('last_updated', 'N/A')}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("Open Travel", key="open_travel", use_container_width=True):
            st.session_state.current_page = "Travel"
            st.rerun()

    # 8. Health Tile
    with col8:
        meds_count = len(health_data.get("medical_reminders", []))
        st.markdown(
            f"""
            <div class="agent-tile">
                <div class="tile-header">
                    <span class="tile-title">🏥 Health</span>
                    <span class="tile-badge">{meds_count}</span>
                </div>
                <div class="tile-status">Appts: {len(health_data.get('appointments', []))} upcoming</div>
                <div class="tile-footer">Updated: {health_data.get('last_updated', 'N/A')}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("Open Health", key="open_health", use_container_width=True):
            st.session_state.current_page = "Health"
            st.rerun()

else:
    # Page routers
    if st.session_state.current_page == "Daily Brief":
        render_daily_brief_page(brief_data)
    elif st.session_state.current_page == "Todos":
        render_todos_page(todos_data)
    elif st.session_state.current_page == "Financial":
        render_financial_page(fin_data)
    elif st.session_state.current_page == "FYI":
        render_fyi_page(fyi_data)
    elif st.session_state.current_page == "Family":
        render_family_page(family_data)
    elif st.session_state.current_page == "School":
        render_school_page(school_data)
    elif st.session_state.current_page == "Travel":
        render_travel_page(travel_data)
    elif st.session_state.current_page == "Health":
        render_health_page(health_data)
        
    # Standard back button
    st.markdown("---")
    if st.button("🔙 Back to Landing Page"):
        st.session_state.current_page = "Landing Page"
        st.rerun()
