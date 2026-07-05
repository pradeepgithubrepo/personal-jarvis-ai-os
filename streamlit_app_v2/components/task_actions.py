# streamlit_app_v2/components/task_actions.py

import streamlit as st
from streamlit_app_v2.services.supabase_service import SupabaseService

def render_task_row_actions(todo_id, status):
    """Renders Complete and Delete buttons in task listings."""
    col1, col2 = st.columns(2)
    with col1:
        if status != "COMPLETED":
            if st.button("✓ Complete", key=f"comp_{todo_id}", use_container_width=True):
                if SupabaseService.complete_task(todo_id):
                    st.success("Task completed!")
                    st.rerun()
        else:
            st.write("Done")
    with col2:
        if st.button("🗑 Delete", key=f"del_{todo_id}", use_container_width=True):
            if SupabaseService.delete_task(todo_id):
                st.warning("Task deleted!")
                st.rerun()

def render_fyi_actions(event_id, status):
    """Renders Mark Read and Delete buttons in FYI listings."""
    col1, col2 = st.columns(2)
    with col1:
        if status == "UNREAD":
            if st.button("✓ Read", key=f"read_{event_id}", use_container_width=True):
                if SupabaseService.mark_fyi_read(event_id):
                    st.success("Marked as read.")
                    st.rerun()
        else:
            st.write("Read")
    with col2:
        if st.button("🗑 Delete", key=f"del_fyi_{event_id}", use_container_width=True):
            if SupabaseService.delete_fyi(event_id):
                st.warning("FYI notice deleted.")
                st.rerun()
