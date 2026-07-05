# streamlit_app_v2/components/todo_card.py

import streamlit as st
from streamlit_app_v2.services.supabase_service import SupabaseService

def render_todo_card(t: dict):
    """
    Renders an individual Todo card with active Complete/Delete buttons.
    """
    prio = t.get("priority", "MEDIUM").upper()
    border_class = "border-primary"
    if prio == "CRITICAL":
        border_class = "border-danger"
    elif prio == "HIGH":
        border_class = "border-warning"
    elif prio == "LOW":
        border_class = "border-success"

    due = t.get("due_date")
    due_str = due[:10] if isinstance(due, str) else due.strftime("%d-%b-%Y") if due else "No Due Date"

    st.markdown(
        f"""
        <div class="jarvis-card {border_class}">
            <h4 style="margin:0 0 0.5rem 0; color:#F3F4F6;">{t.get('title')}</h4>
            <p style="margin:0; font-size:0.875rem; color:#9CA3AF;">
                <strong>Category:</strong> {t.get('category')} | 
                <strong>Priority:</strong> {prio} | 
                <strong>Due:</strong> {due_str}
            </p>
            <p style="margin:0.5rem 0 0.2rem 0; font-size:0.875rem; color:#D1D5DB;">
                <em>{t.get('description') or ''}</em>
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Actions in columns below the HTML content
    c1, c2, _ = st.columns([1.2, 1.2, 4])
    todo_id = t["todo_id"]
    with c1:
        if t.get("status") != "COMPLETED":
            if st.button("Complete ✅", key=f"comp_{todo_id}"):
                if SupabaseService.complete_task(todo_id):
                    st.success("Task completed!")
                    st.rerun()
    with c2:
        if st.button("Delete 🗑️", key=f"del_{todo_id}"):
            if SupabaseService.delete_task(todo_id):
                st.success("Task deleted!")
                st.rerun()
