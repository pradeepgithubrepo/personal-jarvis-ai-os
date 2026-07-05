# streamlit_app_v2/app.py

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st

st.set_page_config(
    page_title="Jarvis OS V1 Dashboard",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject custom CSS
css_path = os.path.join(os.path.dirname(__file__), "styles", "theme.css")
if os.path.exists(css_path):
    with open(css_path, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.sidebar.title("💬 Jarvis OS")
st.sidebar.write("Personal Intelligence Platform")
st.sidebar.write("---")

# Navigation buttons
if "page" not in st.session_state:
    st.session_state.page = "Home"

# Main sidebar navigation
if st.sidebar.button("🏠 Home", use_container_width=True):
    st.session_state.page = "Home"
if st.sidebar.button("📋 Daily Brief", use_container_width=True):
    st.session_state.page = "Daily Brief"
if st.sidebar.button("✅ Todos", use_container_width=True):
    st.session_state.page = "Todos"
if st.sidebar.button("ℹ️ FYI", use_container_width=True):
    st.session_state.page = "FYI"
if st.sidebar.button("🧠 Facts", use_container_width=True):
    st.session_state.page = "Facts"
if st.sidebar.button("💰 Finance", use_container_width=True):
    st.session_state.page = "Finance"
if st.sidebar.button("⚙️ Diagnostics", use_container_width=True):
    st.session_state.page = "Diagnostics"

# Router
page = st.session_state.page

if page == "Home":
    from streamlit_app_v2.pages import dashboard
    dashboard.render()
elif page == "Daily Brief":
    from streamlit_app_v2.pages import daily_brief
    daily_brief.render()
elif page == "Todos":
    from streamlit_app_v2.pages import todos
    todos.render()
elif page == "FYI":
    from streamlit_app_v2.pages import fyi
    fyi.render()
elif page == "Facts":
    from streamlit_app_v2.pages import memory
    memory.render()
elif page == "Finance":
    from streamlit_app_v2.pages import finance_summary
    finance_summary.render()
elif page == "Diagnostics":
    from streamlit_app_v2.pages import diagnostics
    diagnostics.render()
