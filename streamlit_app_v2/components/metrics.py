# streamlit_app_v2/components/metrics.py

import streamlit as st

def render_metric_card(label, value, delta=None, delta_color="normal", help_text=None):
    """Renders a standard dashboard metric card."""
    st.metric(
        label=label,
        value=value,
        delta=delta,
        delta_color=delta_color,
        help=help_text
    )

def render_kpi_grid(metrics_dict):
    """Renders today's snapshot metric cards in a grid layout."""
    cols = st.columns(len(metrics_dict))
    for i, (label, val) in enumerate(metrics_dict.items()):
        with cols[i]:
            st.metric(label=label, value=val)
