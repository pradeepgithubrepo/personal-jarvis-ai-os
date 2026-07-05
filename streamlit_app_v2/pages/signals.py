# streamlit_app_v2/pages/signals.py

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import streamlit as st
import pandas as pd
from streamlit_app_v2.services.supabase_service import SupabaseService
from streamlit_app_v2.components.charts import render_signals_chart

def render():
    st.title("📊 Signals Pipeline Transparency")
    st.write("---")

    # 1. Fetch data
    metrics = SupabaseService.fetch_signals_metrics()
    raw = metrics["raw"]
    qualified = metrics["qualified"]
    understood = metrics["understood"]

    # 2. Metric indicators
    st.subheader("Signal Throughput")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Raw Ingested", len(raw))
    with col2:
        st.metric("Qualified Inflow", len(qualified))
    with col3:
        st.metric("Noise Filtered / Rejected", len([q for q in qualified if q.get("qualification_status") == "REJECTED"]))
    with col4:
        st.metric("Understood Contracts", len(understood))

    st.write("---")

    # 3. Ingestion Charts
    st.subheader("Signal Ingestion Analytics")
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        render_signals_chart(raw, date_col="created_at", title="Raw Ingestion Trend (Daily)")
    with col_chart2:
        # Group by source
        if raw:
            df_raw = pd.DataFrame(raw)
            if "source" in df_raw.columns:
                src_counts = df_raw["source"].value_counts().reset_index(name="Count")
                src_counts.columns = ["source", "Count"]
                import plotly.express as px
                fig = px.bar(src_counts, x="source", y="Count", title="Signals by Source Channel")
                st.plotly_chart(fig, use_container_width=True)

    st.write("---")

    # 4. Drill down table
    st.subheader("Raw Ingestion Drill-down")
    if raw:
        df_raw_full = pd.DataFrame(raw)
        st.dataframe(df_raw_full, use_container_width=True)
    else:
        st.info("No raw signal feeds logged.")

if __name__ == "__main__":
    st.set_page_config(layout="wide")
    render()
