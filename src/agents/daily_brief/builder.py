# src/agents/daily_brief/builder.py

from src.agents.daily_brief.prioritizer import DailyBriefPrioritizer

class DailyBriefBuilder:
    """
    Constructs structured brief text for Morning and Evening briefings.
    """

    @staticmethod
    def build_morning_brief(todos: list, fyi_events: list, facts: list, db_session=None) -> str:
        """
        Generates Morning Brief layout.
        """
        # Sort by importance
        sorted_todos = DailyBriefPrioritizer.sort_by_importance(todos)[:5]
        sorted_fyis = DailyBriefPrioritizer.sort_by_importance(fyi_events)

        lines = ["Daily Briefing", ""]

        # Section 1: Priority Actions
        lines.append("## Priority Actions")
        if not sorted_todos:
            lines.append("No critical action items pending.")
        else:
            for idx, t in enumerate(sorted_todos, 1):
                due_info = f" (Due: {t.due_date.strftime('%Y-%m-%d')})" if t.due_date else ""
                lines.append(f"- [ ] {t.title}{due_info}")
        lines.append("")

        # Section 2: Financial Snapshot
        lines.append("## Financial Snapshot")
        total_credit = 0.0
        total_debit = 0.0
        large_txns = []
        refunds_received = []

        if db_session:
            try:
                from storage.models.monthly_financial_summary import MonthlyFinancialSummary
                latest_summary = db_session.query(MonthlyFinancialSummary).order_by(MonthlyFinancialSummary.created_at.desc()).first()
                if latest_summary:
                    total_credit = latest_summary.total_credit
                    total_debit = latest_summary.total_debit
            except Exception:
                pass
                
            try:
                from storage.models.financial_fact import FinancialFact
                txns = db_session.query(FinancialFact).filter(FinancialFact.fact_type == "EXPENSE_EVENT").all()
                for t in txns:
                    val = t.fact_value or {}
                    amount = val.get("amount", 0.0)
                    if amount >= 5000.0:
                        large_txns.append(f"{val.get('merchant_name', 'Unknown')}: INR {amount}")
                    if "refund" in (val.get("merchant_name") or "").lower():
                        refunds_received.append(f"INR {amount} from {val.get('merchant_name')}")
            except Exception:
                pass

        net_savings = total_credit - total_debit
        lines.append(f"- Money In: INR {total_credit:,.2f}")
        lines.append(f"- Money Out: INR {total_debit:,.2f}")
        lines.append(f"- Net Savings Position: INR {net_savings:,.2f}")
        if large_txns:
            lines.append(f"- Large Transactions: {', '.join(large_txns[:3])}")
        if refunds_received:
            lines.append(f"- Refunds: {', '.join(refunds_received[:3])}")
        lines.append("")

        # Section 3: Important Updates
        lines.append("## Important Updates")
        imp_fyis = [f for f in sorted_fyis if f.category in ("FINANCIAL", "ACCOUNT") and f.importance in ("HIGH", "MEDIUM")]
        # Prevent repeating what is already covered in Todo section
        todo_titles = {t.title.lower() for t in todos}
        unique_imp_fyis = []
        for f in imp_fyis:
            if f.title.lower() not in todo_titles:
                unique_imp_fyis.append(f)

        if not unique_imp_fyis:
            lines.append("No important updates.")
        else:
            for f in unique_imp_fyis[:5]:
                lines.append(f"- {f.title}: {f.description or 'No details available.'}")
        lines.append("")

        # Section 4: Family Updates
        lines.append("## Family Updates")
        fam_fyis = [f for f in sorted_fyis if f.category == "FAMILY"]
        if not fam_fyis:
            lines.append("No family updates today.")
        else:
            for f in fam_fyis[:3]:
                lines.append(f"- {f.title}")
        lines.append("")

        # Section 5: Insights
        lines.append("## Insights")
        insights = []
        if total_debit > total_credit:
            insights.append("- Monthly cash outflow currently exceeds inflow. Monitor spending closely.")
        
        renewals_count = sum(1 for t in todos if t.category == "FINANCIAL" and "renew" in t.title.lower())
        if renewals_count > 1:
            insights.append("- Multiple policy renewals are approaching soon.")
        
        if not insights:
            insights.append("- Spending patterns are within nominal bounds.")
        lines.extend(insights)
        lines.append("")

        return "\n".join(lines)

    @staticmethod
    def build_evening_brief(todos: list, fyi_events: list, facts: list, db_session=None) -> str:
        """
        Generates Evening Brief layout.
        """
        sorted_todos = DailyBriefPrioritizer.sort_by_importance(todos)
        sorted_fyis = DailyBriefPrioritizer.sort_by_importance(fyi_events)

        lines = ["Evening Briefing", ""]

        # Completed Actions
        lines.append("## Completed Actions")
        completed = [t for t in sorted_todos if t.status == "COMPLETED"]
        if not completed:
            lines.append("No actions completed today.")
        else:
            for idx, t in enumerate(completed, 1):
                lines.append(f"{idx}. {t.title}")
        lines.append("")

        # Facts Learned
        lines.append("## Facts Learned")
        if not facts:
            lines.append("No new facts recorded today.")
        else:
            for idx, f in enumerate(facts, 1):
                lines.append(f"{idx}. Learned fact of type {f.fact_type}")
        lines.append("")

        # FYI Alerts Received
        lines.append("## FYI Alerts Received")
        if not sorted_fyis:
            lines.append("No alerts received today.")
        else:
            for idx, f in enumerate(sorted_fyis[:5], 1):
                lines.append(f"{idx}. {f.title} ({f.category})")
        lines.append("")

        return "\n".join(lines)
