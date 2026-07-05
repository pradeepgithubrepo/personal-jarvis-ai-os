# streamlit_app_v2/pages/finance_categories.py

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import streamlit as st
import pandas as pd
from streamlit_app_v2.services.supabase_service import SupabaseService
from streamlit_app_v2.utils.formatting import format_currency

def render():
    st.title("📊 Financial Categories Behavior")
    st.write("---")

    # 1. Fetch data
    fin_data = SupabaseService.fetch_financial_summaries()
    trends = fin_data["trends"]
    events = fin_data["events"]

    if not trends:
        st.info("No comparative category trend data available.")
        return

    # 2. Render Categories Cards Grid
    st.subheader("Category Spend & Monthly Variance")
    df_trends = pd.DataFrame(trends)
    
    # Render each trend in a card
    cols = st.columns(3)
    for idx, row in df_trends.iterrows():
        col_idx = idx % 3
        with cols[col_idx]:
            with st.container():
                st.markdown(f"### {row['category_name']}")
                current = row.get("current_amount", 0)
                previous = row.get("previous_amount", 0)
                change = row.get("change_percentage", 0)
                
                # Render metrics
                st.metric(
                    label="Current Month",
                    value=format_currency(current),
                    delta=f"{change:+.1f}% vs last month" if change else None,
                    delta_color="inverse"
                )
                st.caption(f"Previous month: {format_currency(previous)}")
                
                # Frequent merchants for this category
                cat_events = [e for e in events if e.get("category", "").lower() == row["category_name"].lower()]
                if cat_events:
                    merchants = {}
                    for e in cat_events:
                        m = e.get("paid_to") or e.get("title")
                        if m:
                            merchants[m] = merchants.get(m, 0) + 1
                    sorted_merch = sorted(merchants.items(), key=lambda x: x[1], reverse=True)
                    top_m_str = ", ".join([item[0] for item in sorted_merch[:3]])
                    st.write(f"Top Merchants: `{top_m_str}`")
                st.markdown("---")

    st.write("---")

    # 3. Dynamic Rankings
    st.subheader("Growth Analysis")
    col_grow, col_rec = st.columns(2)
    
    with col_grow:
        st.markdown("#### Fastest Growing Expense Areas")
        growing = df_trends[df_trends["change_percentage"] > 0].sort_values("change_percentage", ascending=False)
        if not growing.empty:
            for _, r in growing.iterrows():
                st.write(f"- **{r['category_name']}**: ↑ {r['change_percentage']:.1f}% increase (Spend: {format_currency(r['current_amount'])})")
        else:
            st.write("No growing categories this period.")

    with col_rec:
        st.markdown("#### Recurring/Subscription Estimates")
        # Identify merchants containing indicators
        rec_events = [e for e in events if any(ind in (e.get("paid_to") or e.get("title") or "").lower() for ind in ["netflix", "spotify", "aws", "gcp", "github", "subscription", "autopay"])]
        if rec_events:
            unique_rec = {}
            for e in rec_events:
                m_name = e.get("paid_to") or e.get("title")
                if m_name:
                    unique_rec[m_name] = e["amount"]
            for m, amt in unique_rec.items():
                st.write(f"- **{m}**: approx. {format_currency(amt)} / month")
        else:
            st.write("No recurring merchant spending patterns detected.")

if __name__ == "__main__":
    st.set_page_config(layout="wide")
    render()
