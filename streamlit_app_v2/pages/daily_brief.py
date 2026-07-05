# streamlit_app_v2/pages/daily_brief.py

import streamlit as st
from streamlit_app_v2.services.supabase_service import SupabaseService

def render():
    st.title("📋 Daily Intelligence Brief")
    st.write("---")

    briefs = SupabaseService.fetch_daily_briefs()
    if not briefs:
        st.info("No Daily Briefs compiled yet.")
        return

    # Tabs for Morning / Evening / Past Briefs
    tabs = st.tabs([f"{b['brief_type']} ({b['generated_at'][:10]})" for b in briefs[:3]])
    for idx, tab in enumerate(tabs):
        b = briefs[idx]
        with tab:
            content = b["content"]
            # Split sections based on markdown ##
            sections = content.split("## ")
            for sec in sections:
                if not sec.strip():
                    continue
                parts = sec.split("\n", 1)
                title = parts[0].strip()
                body = parts[1].strip() if len(parts) > 1 else ""
                
                # Render section as card
                border_class = "border-primary"
                if "priority" in title.lower():
                    border_class = "border-danger"
                elif "financial" in title.lower():
                    border_class = "border-success"
                elif "important" in title.lower() or "alert" in title.lower():
                    border_class = "border-warning"
                
                st.markdown(
                    f"""
                    <div class="jarvis-card {border_class}">
                        <h3 style="margin:0 0 0.5rem 0; color:#F3F4F6;">{title}</h3>
                        <div style="font-size:1rem; color:#E5E7EB; line-height:1.6; white-space: pre-wrap;">{body}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
