# streamlit_app_v2/pages/todos.py

import streamlit as st
from streamlit_app_v2.services.supabase_service import SupabaseService
from streamlit_app_v2.components.todo_card import render_todo_card

def render():
    st.title("✅ Action Obligations (Todos)")
    st.write("---")

    filter_type = st.selectbox(
        "Filter Category",
        ["All", "Open", "Completed", "High Priority", "Financial", "Family"]
    )

    tasks = SupabaseService.fetch_tasks(filter_type)
    if not tasks:
        st.info(f"No task obligations found matching filter: {filter_type}")
        return

    # Render task cards
    for t in tasks:
        render_todo_card(t)
        st.write("")
