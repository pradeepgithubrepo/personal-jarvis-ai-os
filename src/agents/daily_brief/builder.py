# src/agents/daily_brief/builder.py

from src.agents.daily_brief.prioritizer import DailyBriefPrioritizer

class DailyBriefBuilder:
    """
    Constructs structured brief text for Morning and Evening briefings.
    """

    @staticmethod
    def build_morning_brief(todos: list, fyi_events: list, facts: list) -> str:
        """
        Generates Morning Brief layout.
        """
        # Sort by importance
        sorted_todos = DailyBriefPrioritizer.sort_by_importance(todos)
        sorted_fyis = DailyBriefPrioritizer.sort_by_importance(fyi_events)

        lines = ["Morning Brief", ""]

        # Critical Actions
        lines.append("## Critical Actions")
        if not sorted_todos:
            lines.append("No pending actions.")
        else:
            for idx, t in enumerate(sorted_todos, 1):
                due_info = f" (Due: {t.due_date.strftime('%Y-%m-%d')})" if t.due_date else ""
                lines.append(f"{idx}. {t.title}{due_info}")
        lines.append("")

        # Financial Updates
        lines.append("## Financial Updates")
        fin_fyis = [f for f in sorted_fyis if f.category == "FINANCIAL"]
        if not fin_fyis:
            lines.append("No financial updates.")
        else:
            for idx, f in enumerate(fin_fyis, 1):
                lines.append(f"{idx}. {f.title}")
        lines.append("")

        # Family Updates
        lines.append("## Family Updates")
        fam_fyis = [f for f in sorted_fyis if f.category == "FAMILY"]
        if not fam_fyis:
            lines.append("No family updates.")
        else:
            for idx, f in enumerate(fam_fyis, 1):
                lines.append(f"{idx}. {f.title}")
        lines.append("")

        # System Updates
        lines.append("## System Updates")
        sys_fyis = [f for f in sorted_fyis if f.category == "SYSTEM"]
        if not sys_fyis:
            lines.append("No system updates.")
        else:
            for idx, f in enumerate(sys_fyis, 1):
                lines.append(f"{idx}. {f.title}")
        lines.append("")

        # Summary
        lines.append("## Summary")
        lines.append(f"Actions: {len(todos)}")
        lines.append(f"FYI Events: {len(fyi_events)}")
        lines.append(f"New Facts: {len(facts)}")

        return "\n".join(lines)

    @staticmethod
    def build_evening_brief(todos: list, fyi_events: list, facts: list) -> str:
        """
        Generates Evening Brief layout.
        """
        sorted_todos = DailyBriefPrioritizer.sort_by_importance(todos)
        sorted_fyis = DailyBriefPrioritizer.sort_by_importance(fyi_events)

        lines = ["Evening Brief", ""]

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
            lines.append("No FYI alerts received today.")
        else:
            for idx, f in enumerate(sorted_fyis, 1):
                lines.append(f"{idx}. {f.title} ({f.importance})")
        lines.append("")

        # Summary
        lines.append("## Summary")
        lines.append(f"Completed Actions: {len(completed)}")
        lines.append(f"FYI Events: {len(fyi_events)}")
        lines.append(f"Facts Logged: {len(facts)}")

        return "\n".join(lines)
