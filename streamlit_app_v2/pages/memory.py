# streamlit_app_v2/pages/memory.py

import streamlit as st
from streamlit_app_v2.services.supabase_service import SupabaseService
from streamlit_app_v2.components.fact_card import render_fact_card

def render():
    st.title("🧠 Memory Fact Store")
    st.write("---")

    data = SupabaseService.fetch_memory_facts()
    facts = data.get("facts") or []
    if not facts:
        st.info("No memory facts logged in the ledger yet.")
        return

    # Group by category
    family_facts = []
    financial_facts = []
    vehicle_facts = []
    insurance_facts = []

    for f in facts:
        ftype = f.get("fact_type", "").upper()
        val = f.get("fact_value", {})
        val_str = ", ".join(f"{k.replace('_',' ').title()}: {v}" for k, v in val.items())
        
        if ftype in ("SPOUSE", "CHILD", "CONTACT"):
            family_facts.append((f, val_str))
        elif ftype == "BANK_ACCOUNT":
            financial_facts.append((f, val_str))
        elif ftype == "VEHICLE":
            vehicle_facts.append((f, val_str))
        elif ftype == "INSURANCE_POLICY":
            insurance_facts.append((f, val_str))

    # Render sections
    st.subheader("Family")
    if family_facts:
        col1, col2 = st.columns(2)
        for idx, (f, val_str) in enumerate(family_facts):
            with (col1 if idx % 2 == 0 else col2):
                name = f.get("fact_value", {}).get("name", "Unknown Contact")
                render_fact_card(name, val_str, f.get("fact_type"), "border-primary")
    else:
        st.write("No family facts recorded.")

    st.write("---")

    st.subheader("Financial")
    if financial_facts:
        col1, col2 = st.columns(2)
        for idx, (f, val_str) in enumerate(financial_facts):
            with (col1 if idx % 2 == 0 else col2):
                bank = f.get("fact_value", {}).get("bank_name", "Unknown Account")
                render_fact_card(bank, val_str, f.get("fact_type"), "border-success")
    else:
        st.write("No financial account facts recorded.")

    st.write("---")

    st.subheader("Vehicles")
    if vehicle_facts:
        col1, col2 = st.columns(2)
        for idx, (f, val_str) in enumerate(vehicle_facts):
            with (col1 if idx % 2 == 0 else col2):
                make = f.get("fact_value", {}).get("make", "Vehicle")
                model = f.get("fact_value", {}).get("model", "")
                title = f"{make} {model}".strip()
                render_fact_card(title, val_str, f.get("fact_type"), "border-warning")
    else:
        st.write("No vehicle facts recorded.")

    st.write("---")

    st.subheader("Insurance Policies")
    if insurance_facts:
        col1, col2 = st.columns(2)
        for idx, (f, val_str) in enumerate(insurance_facts):
            with (col1 if idx % 2 == 0 else col2):
                provider = f.get("fact_value", {}).get("provider", "Insurance Policy")
                render_fact_card(provider, val_str, f.get("fact_type"), "border-danger")
    else:
        st.write("No insurance policy facts recorded.")
