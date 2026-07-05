# streamlit_app_v2/pages/finance_summary.py

import streamlit as st
from streamlit_app_v2.services.supabase_service import SupabaseService
from streamlit_app_v2.components.kpi_cards import render_kpi_card

def render():
    st.title("💰 Personal Finance Summary")
    st.write("---")

    fin_data = SupabaseService.fetch_financial_summaries()
    spending = fin_data.get("spending") or []
    events = fin_data.get("events") or []

    # Calculate aggregates
    money_in = sum(s.get("total_credit", 0.0) for s in spending)
    money_out = sum(s.get("total_debit", 0.0) for s in spending)
    net_position = money_in - money_out
    
    refunds = sum(e.get("amount", 0.0) for e in events if e.get("transaction_type") == "refund" or "refund" in e.get("title", "").lower())
    recurring = sum(e.get("amount", 0.0) for e in events if "bill" in e.get("title", "").lower() or "subscription" in e.get("title", "").lower())

    # Executive tiles
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        render_kpi_card("Money In", f"₹{money_in:,.2f}", "border-success")
    with col2:
        render_kpi_card("Money Out", f"₹{money_out:,.2f}", "border-danger")
    with col3:
        render_kpi_card("Net Position", f"₹{net_position:,.2f}", "border-primary")
    with col4:
        render_kpi_card("Refunds", f"₹{refunds:,.2f}", "border-warning")
    with col5:
        render_kpi_card("Recurring Payments", f"₹{recurring:,.2f}", "border-primary")

    st.write("---")

    # Category Drilldown selection
    st.subheader("Category Drilldown (Aggregated)")
    
    categories = {}
    for e in events:
        cat = e.get("category") or "Other"
        text = e.get("title", "").lower()
        if "insurance" in text:
            cat = "Insurance"
        elif "electricity" in text or "tangedco" in text or "utility" in text:
            cat = "Utilities"
        elif "axis" in text or "card" in text:
            cat = "Credit Card"
        elif "ola" in text or "uber" in text or "traffic" in text:
            cat = "Transport"
            
        if cat not in categories:
            categories[cat] = {
                "total": 0.0,
                "count": 0,
                "items": []
            }
        amt = e.get("amount", 0.0) or 0.0
        categories[cat]["total"] += amt
        categories[cat]["count"] += 1
        categories[cat]["items"].append(e)

    # Accordion per category
    for cat, data in sorted(categories.items()):
        with st.expander(f"📁 {cat} (Total: ₹{data['total']:,.2f} | Transactions: {data['count']})"):
            st.write(f"Aggregate financial spend in {cat} category.")
            st.write(f"- Average transaction size: ₹{data['total'] / max(1, data['count']):,.2f}")
            sorted_items = sorted(data["items"], key=lambda x: x.get("amount", 0.0) or 0.0, reverse=True)
            st.write("Top transactions:")
            for item in sorted_items[:3]:
                st.write(f"  * {item.get('title')} : ₹{item.get('amount', 0.0):,.2f}")
