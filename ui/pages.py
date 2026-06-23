# ui/pages.py

import streamlit as st
from datetime import datetime, timedelta

def format_priority(priority: str) -> str:
    priority_lower = priority.lower()
    if priority_lower == "high":
        return f'<span class="priority-high">🔴 High</span>'
    elif priority_lower == "medium":
        return f'<span class="priority-medium">🟡 Medium</span>'
    else:
        return f'<span class="priority-low">🔵 Low</span>'


def render_todos_page(data: dict):
    st.title("📋 Agent: Todos")
    
    todos = data.get("todos", [])
    if not todos:
        st.info("No todos found.")
        return

    # Interactive elements: Search & Sort
    col_search, col_sort, col_filter = st.columns([2, 1, 1])
    with col_search:
        search_query = st.text_input("Search Todos", placeholder="Type to search...").lower()
    with col_sort:
        sort_by = st.selectbox("Sort By", ["Due Date", "Priority", "Category", "Title"])
    with col_filter:
        status_filter = st.selectbox("Filter Status", ["All", "Pending", "Completed"])

    # Apply filters
    filtered_todos = []
    for todo in todos:
        # Search filter
        if search_query and search_query not in todo.get("title", "").lower() and search_query not in todo.get("category", "").lower():
            continue
        
        # Status filter
        status = todo.get("status", "pending").lower()
        if status_filter == "Pending" and status != "pending":
            continue
        if status_filter == "Completed" and status != "completed":
            continue
            
        filtered_todos.append(todo)

    # Apply Sorting
    def get_sort_key(t):
        if sort_by == "Due Date":
            return t.get("due_date", "9999-12-31")
        elif sort_by == "Priority":
            prio = t.get("priority", "low").lower()
            # Sort high first
            prio_map = {"high": 0, "medium": 1, "low": 2}
            return prio_map.get(prio, 3)
        elif sort_by == "Category":
            return t.get("category", "").lower()
        else:
            return t.get("title", "").lower()

    filtered_todos.sort(key=get_sort_key)

    # Display stats
    pending_count = sum(1 for t in todos if t.get("status") == "pending")
    completed_count = sum(1 for t in todos if t.get("status") == "completed")
    
    # Calculate Due Today & Due Tomorrow dynamically
    today_dt = datetime.now()
    today_str = today_dt.strftime("%Y-%m-%d")
    tomorrow_str = (today_dt + timedelta(days=1)).strftime("%Y-%m-%d")
    due_today_count = sum(1 for t in todos if t.get("due_date") == today_str and t.get("status") == "pending")
    due_tomorrow_count = sum(1 for t in todos if t.get("due_date") == tomorrow_str and t.get("status") == "pending")


    st.markdown("### Summary Statistics")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric-box"><div class="metric-label">Pending</div><div class="metric-num">{pending_count}</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-box"><div class="metric-label">Due Today</div><div class="metric-num">{due_today_count}</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-box"><div class="metric-label">Due Tomorrow</div><div class="metric-num">{due_tomorrow_count}</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="metric-box"><div class="metric-label">Completed</div><div class="metric-num">{completed_count}</div></div>', unsafe_allow_html=True)

    st.markdown("---")

    # Render Todos
    if not filtered_todos:
        st.write("No matching todos found.")
    else:
        for t in filtered_todos:
            status_emoji = "✅" if t.get("status") == "completed" else "⏳"
            prio_html = format_priority(t.get("priority", "low"))
            due_date = t.get("due_date", "No due date")
            category = t.get("category", "General")
            
            st.markdown(
                f"""
                <div class="custom-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 1.1rem; font-weight: 500;">{status_emoji} {t.get('title')}</span>
                        <span>{prio_html}</span>
                    </div>
                    <div style="margin-top: 10px; font-size: 0.85rem; color: #8b949e; display: flex; gap: 20px;">
                        <span>📅 Due: {due_date}</span>
                        <span>🏷️ Category: {category}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

def render_financial_page(data: dict):
    st.title("💳 Agent: Financial Intelligence (Monthly Outflow)")
    
    months = data.get("months", [])
    if not months:
        st.info("No monthly financial data found. Run the ingestion pipeline or check the logs.")
        return

    # Month Selector
    month_options = [m["month"] for m in months]
    selected_month_name = st.selectbox("Select Spending Month", month_options)
    
    # Find the selected month
    selected_month = next(m for m in months if m["month"] == selected_month_name)
    month_key = selected_month["month_key"]
    summary = selected_month["summary"]
    
    # 1. Summary Header
    st.markdown("### Spending Overview")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f'<div class="metric-box"><div class="metric-label">Total Outflow (Debits)</div><div class="metric-num" style="color: #ff7b72;">{summary.get("expenses", 0):,.2f} INR</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-box"><div class="metric-label">Transactions Tracked</div><div class="metric-num">{summary.get("transaction_count", 0)} Payments</div></div>', unsafe_allow_html=True)

    st.markdown("---")

    # 2. Spend Categories & Trends
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.markdown("### 📊 Spending by Category")
        cats = selected_month.get("spend_categories", {})
        if not cats:
            st.write("No spending categories found for this month.")
        else:
            # Sort categories by amount descending to show largest first
            sorted_cats = sorted(cats.items(), key=lambda x: x[1], reverse=True)
            total_spend = sum(cats.values())
            for cat, amount in sorted_cats:
                percentage = (amount / total_spend * 100) if total_spend > 0 else 0
                st.write(f"**{cat}** — {amount:,.2f} INR ({percentage:.1f}%)")
                st.progress(percentage / 100.0)

    with col_right:
        st.markdown("### 📈 Month-over-Month Trends")
        trends = data.get("trends", [])
        filtered_trends = [t for t in trends if t["month_key"] == month_key]
        if not filtered_trends:
            st.write("No MoM trend data available for this month.")
        else:
            for t in filtered_trends:
                pct = t["change_percentage"]
                if pct > 0:
                    pct_str = f'<span style="color: #ff7b72;">+{pct:.1f}% Increase</span>'
                elif pct < 0:
                    pct_str = f'<span style="color: #56d364;">{pct:.1f}% Decrease</span>'
                else:
                    pct_str = '<span style="color: #8b949e;">0% (No Change / New Category)</span>'
                    
                st.markdown(
                    f"""
                    <div style="background-color: #1f242c; padding: 12px; border-radius: 8px; margin-bottom: 8px; border-left: 3px solid #58a6ff;">
                        <strong>{t["category_name"]}:</strong> {pct_str}<br/>
                        <span style="font-size: 0.85rem; color: #8b949e;">Current: {t["current_amount"]:,.2f} INR | Prev: {t["previous_amount"]:,.2f} INR</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    st.markdown("---")

    # 3. Category Drilldown
    st.markdown("### 🔍 Category Transaction Drilldown")
    if not cats:
        st.write("No spending transactions to drill down.")
    else:
        drilldown_cat = st.selectbox("Choose Category to Drill Down", list(cats.keys()))
        if drilldown_cat:
            from services.supabase_repo import SupabaseRepo
            from services.supabase_repo import supabase
            
            try:
                db_events = SupabaseRepo.fetch_financial_events()
                signals_data = supabase.table("signals").select("signal_id, message").execute().data or []
                signal_messages = {s["signal_id"]: s["message"] for s in signals_data}
                
                start_dt = datetime.strptime(month_key, "%Y-%m")
                # End of month is 31 days or next month minus 1 sec
                if start_dt.month == 12:
                    end_dt = datetime(start_dt.year + 1, 1, 1) - timedelta(seconds=1)
                else:
                    end_dt = datetime(start_dt.year, start_dt.month + 1, 1) - timedelta(seconds=1)
                
                events = []
                for e in db_events:
                    dt_str = e.get("event_timestamp")
                    if not dt_str:
                        continue
                    try:
                        dt_clean = dt_str.replace("Z", "").split(".")[0]
                        dt = datetime.fromisoformat(dt_clean)
                    except Exception:
                        continue
                        
                    if start_dt <= dt <= end_dt and e.get("category") == drilldown_cat:
                        sig_id = e.get("source_signal_id")
                        message = (signal_messages.get(sig_id) or "").lower()
                        is_credit = "credited" in message or "salary" in message or "received" in message or "deposit" in message or "credit alert" in message
                        if not is_credit and e.get("category") != "INTERNAL_TRANSFER":
                            events.append({
                                "title": message[:100].strip() or "Debit Transaction",
                                "amount": float(e.get("amount") or 0),
                                "event_date": dt,
                                "merchant": e.get("merchant") or "N/A"
                            })
                
                if not events:
                    st.write("No transaction events found.")
                else:
                    for e in events:
                        st.markdown(
                            f"""
                            <div class="custom-card" style="padding: 12px; margin-bottom: 8px;">
                                <div style="display: flex; justify-content: space-between;">
                                    <strong>{e["title"]}</strong>
                                    <span style="color: #ff7b72; font-weight: bold;">-{e["amount"]:,.2f} INR</span>
                                </div>
                                <div style="font-size: 0.8rem; color: #8b949e; margin-top: 4px;">
                                    📅 Date: {e["event_date"].strftime("%Y-%m-%d %H:%M")} | Merchant: {e["merchant"]}
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
            except Exception as ex:
                st.error(f"Error fetching drilldown: {ex}")

def render_fyi_page(data: dict):
    st.title("ℹ️ Agent: FYI Updates")
    
    updates = data.get("updates", [])
    if not updates:
        st.info("No FYI updates available.")
        return

    # Category filter
    categories = ["All", "School", "Family", "Delivery", "General"]
    selected_cat = st.selectbox("Category Filter", categories)
    
    st.markdown("### Chronological Feed")
    
    # Sort updates chronologically (newest first)
    sorted_updates = sorted(updates, key=lambda x: x.get("timestamp", ""), reverse=True)
    
    count = 0
    for item in sorted_updates:
        category = item.get("category", "general").lower()
        if selected_cat != "All" and selected_cat.lower() != category:
            continue
            
        count += 1
        # Pretty category tags
        cat_colors = {
            "school": "background-color: rgba(88, 166, 255, 0.15); color: #58a6ff;",
            "family": "background-color: rgba(86, 213, 100, 0.15); color: #56d364;",
            "delivery": "background-color: rgba(210, 153, 34, 0.15); color: #d29922;",
            "general": "background-color: rgba(139, 148, 158, 0.15); color: #8b949e;"
        }
        badge_style = cat_colors.get(category, cat_colors["general"])
        
        # Format Timestamp
        try:
            dt = datetime.fromisoformat(item.get("timestamp").replace("Z", "+00:00"))
            time_str = dt.strftime("%B %d, %Y at %I:%M %p")
        except Exception:
            time_str = item.get("timestamp")

        st.markdown(
            f"""
            <div class="custom-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span style="font-size: 1.15rem; font-weight: 600; color: #ffffff;">{item.get('title')}</span>
                    <span style="padding: 2px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 500; {badge_style}">{category.upper()}</span>
                </div>
                <div style="font-size: 0.95rem; color: #c9d1d9; margin-bottom: 12px; line-height: 1.5;">
                    {item.get('content')}
                </div>
                <div style="font-size: 0.75rem; color: #8b949e; border-top: 1px solid #21262d; padding-top: 8px;">
                    🕒 Received: {time_str}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
    if count == 0:
        st.write("No updates under this category.")

def render_daily_brief_page(data: dict):
    st.title("☀️ Agent: Daily Brief")
    
    st.markdown(f"## {data.get('greeting', 'Good Morning Pradeep')}")
    
    st.markdown("---")
    
    # Render sections
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.markdown("### 🚨 Today's Priorities")
        priorities = data.get("priorities", [])
        if not priorities:
            st.write("No priorities set for today.")
        else:
            for prio in priorities:
                st.markdown(f"🎯 **{prio}**")
                
        st.markdown("### 💳 Financial Alerts")
        fin_alerts = data.get("financial_alerts", [])
        if not fin_alerts:
            st.write("No financial alerts.")
        else:
            for alert in fin_alerts:
                st.markdown(f"• {alert}")
                
        st.markdown("### 📌 Important Reminders")
        reminders = data.get("important_reminders", [])
        if not reminders:
            st.write("No reminders for today.")
        else:
            for reminder in reminders:
                st.markdown(f"⏰ {reminder}")

    with col_right:
        st.markdown("### 👨‍👩‍👧 Family Updates")
        family = data.get("family_updates", [])
        if not family:
            st.write("No family updates.")
        else:
            for fam in family:
                st.markdown(f"• {fam}")
                
        st.markdown("### 🏫 School Circulars")
        school = data.get("school_circulars", [])
        if not school:
            st.write("No circulars today.")
        else:
            for sc in school:
                st.markdown(f"• {sc}")

def render_family_page(data: dict):
    st.title("👨‍👩‍👧 Agent: Family Updates")
    
    messages = data.get("messages", [])
    events = data.get("events", [])
    reminders = data.get("reminders", [])
    
    # Create all events with date key
    timeline = {}
    
    def add_to_timeline(date_str, item, item_type):
        if not date_str:
            date_str = "Undated"
        if date_str not in timeline:
            timeline[date_str] = []
        timeline[date_str].append((item_type, item))
        
    for msg in messages:
        add_to_timeline(msg.get("date"), msg, "Message")
    for ev in events:
        add_to_timeline(ev.get("date"), ev, "Event")
    for rem in reminders:
        add_to_timeline(rem.get("date"), rem, "Reminder")
        
    # Sort dates chronologically
    sorted_dates = sorted(timeline.keys(), reverse=True)
    
    if not sorted_dates:
        st.info("No family updates found.")
        return
        
    for date_str in sorted_dates:
        st.markdown(f"### 📅 {date_str}")
        for item_type, item in timeline[date_str]:
            if item_type == "Message":
                st.markdown(
                    f"""
                    <div style="background-color: #1f242c; padding: 12px; border-radius: 8px; margin-bottom: 8px; border-left: 3px solid #56d364;">
                        <strong>💬 Message from {item.get('sender')}:</strong><br/>
                        <span style="font-size: 0.95rem; color: #c9d1d9;">"{item.get('content')}"</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            elif item_type == "Event":
                st.markdown(
                    f"""
                    <div style="background-color: #1f242c; padding: 12px; border-radius: 8px; margin-bottom: 8px; border-left: 3px solid #58a6ff;">
                        <strong>🎉 Event: {item.get('title')}</strong><br/>
                        <span style="font-size: 0.9rem; color: #8b949e;">{item.get('description')}</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            elif item_type == "Reminder":
                st.markdown(
                    f"""
                    <div style="background-color: #1f242c; padding: 12px; border-radius: 8px; margin-bottom: 8px; border-left: 3px solid #ff7b72;">
                        <strong>⏰ Reminder: {item.get('title')}</strong>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

def render_school_page(data: dict):
    st.title("🏫 Agent: School")
    
    circulars = data.get("circulars", [])
    activities = data.get("activities", [])
    homework = data.get("homework", [])
    events = data.get("events", [])
    
    # We want to group by child and then date. Ravi is the only child here.
    # Grouping logic
    child_groups = {}
    
    def add_to_child(child_name, date_str, item, item_type):
        if not child_name:
            child_name = "General / Unspecified"
        if child_name not in child_groups:
            child_groups[child_name] = {}
        if date_str not in child_groups[child_name]:
            child_groups[child_name][date_str] = []
        child_groups[child_name][date_str].append((item_type, item))

    for circ in circulars:
        add_to_child(circ.get("child"), circ.get("date"), circ, "Circular")
    for act in activities:
        add_to_child(act.get("child"), act.get("date"), act, "Activity")
    for hw in homework:
        add_to_child(hw.get("child"), hw.get("due_date"), hw, "Homework Due")
    for ev in events:
        add_to_child(ev.get("child"), ev.get("date"), ev, "Event")

    if not child_groups:
        st.info("No school updates found.")
        return

    for child, dates in child_groups.items():
        st.header(f"🧑‍🎓 Student: {child}")
        
        # Sort dates
        for date_str in sorted(dates.keys(), reverse=True):
            st.subheader(f"📅 {date_str}")
            for item_type, item in dates[date_str]:
                if item_type == "Circular":
                    st.markdown(
                        f"""
                        <div style="background-color: #161b22; border: 1px solid #30363d; padding: 12px; border-radius: 8px; margin-bottom: 8px;">
                            <span style="color: #58a6ff; font-weight: bold;">📋 School Circular: {item.get('title')}</span><br/>
                            <span style="font-size: 0.9rem; color: #c9d1d9;">{item.get('description')}</span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                elif item_type == "Homework Due":
                    st.markdown(
                        f"""
                        <div style="background-color: #161b22; border: 1px solid #30363d; padding: 12px; border-radius: 8px; margin-bottom: 8px;">
                            <span style="color: #ff7b72; font-weight: bold;">📝 Homework Due ({item.get('subject')}): {item.get('title')}</span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                elif item_type == "Activity":
                    st.markdown(
                        f"""
                        <div style="background-color: #161b22; border: 1px solid #30363d; padding: 12px; border-radius: 8px; margin-bottom: 8px;">
                            <span style="color: #56d364; font-weight: bold;">⚽ Activity: {item.get('title')}</span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                elif item_type == "Event":
                    st.markdown(
                        f"""
                        <div style="background-color: #161b22; border: 1px solid #30363d; padding: 12px; border-radius: 8px; margin-bottom: 8px;">
                            <span style="color: #d29922; font-weight: bold;">🏫 Event: {item.get('title')}</span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

def render_travel_page(data: dict):
    st.title("✈️ Agent: Travel")
    
    tickets = data.get("tickets", [])
    bookings = data.get("bookings", [])
    alerts = data.get("alerts", [])
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🎫 Tickets & Flight Info")
        if not tickets:
            st.write("No active tickets.")
        else:
            for t in tickets:
                st.markdown(
                    f"""
                    <div class="custom-card">
                        <span style="font-size: 1.1rem; font-weight: bold; color: #58a6ff;">✈️ {t.get('from')} → {t.get('to')}</span><br/>
                        <div style="margin-top: 8px; font-size: 0.9rem; color: #c9d1d9;">
                            <strong>Passenger:</strong> {t.get('passenger')}<br/>
                            <strong>Departure:</strong> {t.get('date')} at {t.get('departure_time')}<br/>
                            <strong>Reference:</strong> {t.get('booking_ref')}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
    with col2:
        st.markdown("### 🏨 Accommodation Bookings")
        if not bookings:
            st.write("No hotel bookings.")
        else:
            for b in bookings:
                st.markdown(
                    f"""
                    <div class="custom-card">
                        <span style="font-size: 1.1rem; font-weight: bold; color: #56d364;">🏨 {b.get('name')}</span><br/>
                        <div style="margin-top: 8px; font-size: 0.9rem; color: #c9d1d9;">
                            <strong>Type:</strong> {b.get('type')}<br/>
                            <strong>Stay:</strong> {b.get('check_in')} to {b.get('check_out')}<br/>
                            <strong>Status:</strong> <span style="color: #56d364;">{b.get('status').upper()}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
    st.markdown("---")
    st.markdown("### ⚠️ Travel Alerts")
    if not alerts:
        st.info("No travel alerts active.")
    else:
        for alert in alerts:
            st.warning(alert)

def render_health_page(data: dict):
    st.title("🏥 Agent: Health")
    
    reminders = data.get("medical_reminders", [])
    alerts = data.get("health_alerts", [])
    appointments = data.get("appointments", [])
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 💊 Medication Reminders")
        if not reminders:
            st.write("No medication reminders.")
        else:
            for r in reminders:
                st.markdown(
                    f"""
                    <div class="custom-card" style="padding: 16px; margin-bottom: 12px; border-left: 4px solid #ff7b72;">
                        <strong>🧬 {r.get('medicine_name')}</strong> ({r.get('dosage')})<br/>
                        <span style="font-size: 0.85rem; color: #8b949e;">🕒 {r.get('time')}</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
    with col2:
        st.markdown("### 📅 Medical Appointments")
        if not appointments:
            st.write("No upcoming appointments.")
        else:
            for app in appointments:
                try:
                    dt = datetime.fromisoformat(app.get("time").replace("Z", "+00:00"))
                    time_str = dt.strftime("%B %d, %Y at %I:%M %p")
                except Exception:
                    time_str = app.get("time")
                st.markdown(
                    f"""
                    <div class="custom-card" style="padding: 16px; margin-bottom: 12px; border-left: 4px solid #58a6ff;">
                        <strong>🩺 {app.get('doctor')}</strong><br/>
                        <span style="font-size: 0.85rem; color: #c9d1d9;">🕒 {time_str}</span><br/>
                        <span style="font-size: 0.8rem; color: #8b949e;">📍 {app.get('clinic')}</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
    st.markdown("---")
    st.markdown("### ⚠️ Health Alerts")
    if not alerts:
        st.info("No health alerts active.")
    else:
        for alert in alerts:
            st.markdown(
                f"""
                <div style="background-color: rgba(255, 123, 114, 0.1); border-left: 4px solid #ff7b72; padding: 12px; margin-bottom: 8px; border-radius: 4px; font-size: 0.9rem;">
                    🏥 {alert}
                </div>
                """,
                unsafe_allow_html=True
            )
