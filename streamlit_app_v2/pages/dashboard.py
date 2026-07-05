# streamlit_app_v2/pages/dashboard.py

import streamlit as st
from streamlit_app_v2.services.supabase_service import SupabaseService
from streamlit_app_v2.components.kpi_cards import render_kpi_card

def render():
    st.markdown("<h1 style='color:#F3F4F6; margin-bottom:0.1rem;'>Jarvis AI OS</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#9CA3AF; font-size:1.1rem; margin-top:0;'>Personal Intelligence Platform</p>", unsafe_allow_html=True)
    st.write("---")

    # Fetch summaries
    summary = SupabaseService.fetch_dashboard_summary()
    facts_data = SupabaseService.fetch_memory_facts()
    facts_count = len(facts_data.get("facts") or [])
    
    # Financial aggregate position
    fin_data = SupabaseService.fetch_financial_summaries()
    total_debit = 0.0
    if fin_data.get("spending"):
        total_debit = sum(s.get("total_debit", 0.0) for s in fin_data["spending"])
        
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_kpi_card("Facts", f"{facts_count}", "border-primary")
    with col2:
        render_kpi_card("Todos", f"{summary['open_tasks']}", "border-danger")
    with col3:
        render_kpi_card("FYI", f"{summary['unread_fyi']}", "border-warning")
    with col4:
        render_kpi_card("Finance (Total Spending)", f"₹{total_debit:,.2f}", "border-success")

    st.write("---")
    
    # Grid Navigation Cards
    st.subheader("Explore Modules")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            """
            <div class="jarvis-card border-primary" style="text-align:center;">
                <h4 style="margin:0; color:#F3F4F6;">Synthesis</h4>
                <p style="font-size:0.875rem; color:#9CA3AF;">Morning & Evening summaries.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("Open Daily Brief", key="nav_brief", use_container_width=True):
            st.session_state.page = "Daily Brief"
            st.rerun()
            
    with c2:
        st.markdown(
            """
            <div class="jarvis-card border-success" style="text-align:center;">
                <h4 style="margin:0; color:#F3F4F6;">Memory facts</h4>
                <p style="font-size:0.875rem; color:#9CA3AF;">Knowledge store graph.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("Open Family Memory", key="nav_facts", use_container_width=True):
            st.session_state.page = "Facts"
            st.rerun()
            
    with c3:
        st.markdown(
            """
            <div class="jarvis-card border-warning" style="text-align:center;">
                <h4 style="margin:0; color:#F3F4F6;">Finance summary</h4>
                <p style="font-size:0.875rem; color:#9CA3AF;">Spending rollups & drilldowns.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("Open Finance", key="nav_finance", use_container_width=True):
            st.session_state.page = "Finance"
            st.rerun()
            
    with c4:
        st.markdown(
            """
            <div class="jarvis-card border-danger" style="text-align:center;">
                <h4 style="margin:0; color:#F3F4F6;">Diagnostics</h4>
                <p style="font-size:0.875rem; color:#9CA3AF;">Pipeline health & rules status.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("Open Diagnostics", key="nav_diag", use_container_width=True):
            st.session_state.page = "Diagnostics"
            st.rerun()
