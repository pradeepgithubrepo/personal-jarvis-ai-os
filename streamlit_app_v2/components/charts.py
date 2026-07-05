# streamlit_app_v2/components/charts.py

import plotly.express as px
import pandas as pd
import streamlit as st

def render_expense_distribution(categories_data):
    """Renders a pie chart of expense distributions."""
    if not categories_data:
        st.info("No expense data available for distribution.")
        return
        
    df = pd.DataFrame(categories_data)
    # expected columns: category_name, amount
    if "category_name" in df.columns and "amount" in df.columns:
        # Group by category
        grouped = df.groupby("category_name")["amount"].sum().reset_index()
        fig = px.pie(
            grouped,
            values="amount",
            names="category_name",
            title="Expenses by Category",
            color_discrete_sequence=px.colors.sequential.RdBu,
            hole=0.4
        )
        fig.update_layout(margin=dict(t=40, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Category data schema format invalid.")

def render_spending_trend(spending_data):
    """Renders spending trends over months."""
    if not spending_data:
        st.info("No spending trends historical records found.")
        return
        
    df = pd.DataFrame(spending_data)
    # expected columns: month_key, total_spend
    if "month_key" in df.columns and "total_spend" in df.columns:
        df = df.sort_values("month_key")
        fig = px.bar(
            df,
            x="month_key",
            y="total_spend",
            title="Monthly Spending Trend",
            labels={"month_key": "Month", "total_spend": "Total Spend (₹)"},
            color_discrete_sequence=["#1f77b4"]
        )
        fig.update_layout(margin=dict(t=40, b=20, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)

def render_signals_chart(signals_data, date_col="created_at", title="Signals Received Last 7 Days"):
    """Renders counts of signals received grouped by day."""
    if not signals_data:
        st.info("No signal records available for trend plots.")
        return
        
    df = pd.DataFrame(signals_data)
    if date_col in df.columns:
        # Parse dates to YYYY-MM-DD
        df["date"] = pd.to_datetime(df[date_col]).dt.date
        counts = df.groupby("date").size().reset_index(name="Count")
        fig = px.line(
            counts,
            x="date",
            y="Count",
            title=title,
            labels={"date": "Date", "Count": "Signals count"},
            markers=True
        )
        fig.update_layout(margin=dict(t=40, b=20, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)
