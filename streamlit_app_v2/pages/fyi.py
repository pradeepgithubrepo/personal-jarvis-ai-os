# streamlit_app_v2/pages/fyi.py

import streamlit as st
from streamlit_app_v2.services.supabase_service import SupabaseService

def render():
    st.title("ℹ️ FYI Awareness Notifications")
    st.write("---")

    fyi_events = SupabaseService.fetch_fyi_events()
    if not fyi_events:
        st.info("No FYI alerts received yet.")
        return

    # Group by category
    categories = {}
    for f in fyi_events:
        cat = f.get("category", "PERSONAL").upper()
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(f)

    # Accordion per category
    for cat in sorted(categories.keys()):
        events = categories[cat]
        unread_count = sum(1 for e in events if e.get("status") == "UNREAD")
        badge = f" ({unread_count} Unread)" if unread_count else ""
        
        with st.expander(f"{cat} Updates{badge}", expanded=(unread_count > 0)):
            for e in events:
                border_class = "border-success" if e.get("status") == "READ" else "border-warning"
                imp = e.get("importance", "MEDIUM").upper()
                if imp == "HIGH":
                    border_class = "border-danger"

                st.markdown(
                    f"""
                    <div class="jarvis-card {border_class}">
                        <h4 style="margin:0 0 0.5rem 0; color:#F3F4F6;">{e.get('title')}</h4>
                        <p style="margin:0; font-size:0.875rem; color:#9CA3AF;">
                            <strong>Importance:</strong> {imp} | <strong>Status:</strong> {e.get('status')}
                        </p>
                        <p style="margin:0.5rem 0 0.2rem 0; font-size:0.875rem; color:#D1D5DB;">
                            {e.get('description') or 'No details available.'}
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
                # Mark as Read / Delete buttons
                c1, c2, _ = st.columns([1.2, 1.2, 4])
                event_id = e["event_id"]
                with c1:
                    if e.get("status") == "UNREAD":
                        if st.button("Mark Read ✔️", key=f"read_{event_id}"):
                            if SupabaseService.mark_fyi_read(event_id):
                                st.success("Marked as read!")
                                st.rerun()
                with c2:
                    if st.button("Delete 🗑️", key=f"del_fyi_{event_id}"):
                        if SupabaseService.delete_fyi(event_id):
                            st.success("FYI alert deleted!")
                            st.rerun()
                st.write("")
