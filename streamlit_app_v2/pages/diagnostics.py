# streamlit_app_v2/pages/diagnostics.py

import streamlit as st
import pandas as pd
from streamlit_app_v2.services.supabase_service import SupabaseService
from streamlit_app_v2.utils.formatting import format_timestamp
from streamlit_app_v2.components.kpi_cards import render_kpi_card

def render():
    st.title("⚙️ Operations Diagnostics & Troubleshooting")
    st.write("---")

    # Fetch diagnostics
    diag = SupabaseService.fetch_diagnostics()
    status = diag["status"]
    runs = diag["runs"]

    # System Status Card Group
    st.subheader("System Health State")
    if status:
        col1, col2, col3 = st.columns(3)
        with col1:
            state = status.get("current_status", "UNKNOWN").upper()
            border = "border-success" if state in ("HEALTHY", "ONLINE", "ACTIVE") else "border-warning"
            render_kpi_card("Current Status", state, border)
        with col2:
            render_kpi_card("Last Successful Refresh", format_timestamp(status.get("last_successful_refresh")) or "N/A", "border-primary")
        with col3:
            render_kpi_card("Active Run ID", str(status.get("current_run_id", "None"))[:8], "border-primary")
    else:
        st.info("No active system status record found.")

    st.write("---")

    # Pipeline Runs History
    st.subheader("Recent Pipeline Orchestrations")
    if runs:
        df_runs = pd.DataFrame(runs)
        st.dataframe(
            df_runs[[
                "run_id", "status", "started_at", "completed_at", "duration_seconds", 
                "signals_processed", "todos_generated", "fyi_generated", "error_message"
            ]],
            use_container_width=True
        )
    else:
        st.info("No recorded pipeline run metrics archived.")
