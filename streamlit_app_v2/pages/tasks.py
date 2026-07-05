# streamlit_app_v2/pages/tasks.py

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import streamlit as st
import pandas as pd
from streamlit_app_v2.services.supabase_service import SupabaseService
from streamlit_app_v2.components.task_actions import render_task_row_actions
from streamlit_app_v2.utils.formatting import format_timestamp

def render():
    st.title("📋 Task Management")
    st.write("---")

    # 1. Selection filter
    filter_type = st.selectbox(
        "Filter Tasks",
        ["All", "Open", "Completed", "High Priority", "Financial", "Family"]
    )

    # 2. Fetch tasks
    tasks = SupabaseService.fetch_tasks(filter_type)

    if not tasks:
        st.info(f"No tasks match the filter: {filter_type}")
        return

    # 3. Render list with actions
    st.subheader(f"{filter_type} Tasks ({len(tasks)})")
    
    for t in tasks:
        # Styled Task Card
        with st.container():
            col1, col2, col3 = st.columns([4, 2, 2])
            with col1:
                st.markdown(f"### {t['title']}")
                st.write(t.get("description") or "No description provided.")
                st.caption(f"Category: `{t['category']}` | Created: {format_timestamp(t.get('created_at'))}")
            with col2:
                # Meta Indicators
                st.markdown(f"**Priority:** `{t['priority']}`")
                st.markdown(f"**Status:** `{t['status']}`")
                due = t.get('due_date')
                st.write(f"Due: {format_timestamp(due) if due else 'No due date'}")
            with col3:
                # Row Interactive Actions
                render_task_row_actions(t["todo_id"], t["status"])
            st.markdown("---")

if __name__ == "__main__":
    st.set_page_config(layout="wide")
    render()
