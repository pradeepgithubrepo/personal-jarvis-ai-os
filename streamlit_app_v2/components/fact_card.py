# streamlit_app_v2/components/fact_card.py

import streamlit as st

def render_fact_card(title: str, value: str, fact_type: str, border_class="border-primary"):
    """
    Renders a fact entity card.
    """
    st.markdown(
        f"""
        <div class="jarvis-card {border_class}">
            <h4 style="margin:0 0 0.5rem 0; color:#F3F4F6;">{title}</h4>
            <div style="font-size:0.875rem; color:#9CA3AF; margin-bottom:0.5rem;">
                <strong>Type:</strong> {fact_type}
            </div>
            <div style="font-size:0.95rem; color:#E5E7EB; line-height:1.4;">
                {value}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
