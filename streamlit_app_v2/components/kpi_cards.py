# streamlit_app_v2/components/kpi_cards.py

import streamlit as st

def render_kpi_card(title: str, value: str, border_class="border-primary"):
    """
    Renders a Power BI / Microsoft Fabric style glassmorphic metric card.
    """
    st.markdown(
        f"""
        <div class="jarvis-card {border_class}">
            <div class="kpi-title">{title}</div>
            <div class="kpi-val">{value}</div>
        </div>
        """,
        unsafe_allow_html=True
    )
