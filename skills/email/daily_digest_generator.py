from storage.repositories.signal_repository import (
    SignalRepository,
)


class DailyDigestGenerator:

    def generate(self):

        signals = (
            SignalRepository
            .get_today_signals()
        )

        finance = [
            s
            for s in signals
            if s.category
            == "finance"
        ]

        shopping = [
            s
            for s in signals
            if s.category
            == "shopping"
        ]

        insurance = [
            s
            for s in signals
            if s.category
            == "insurance"
        ]

        lines = []

        lines.append(
            "Jarvis Daily Brief"
        )

        lines.append(
            ""
        )

        lines.append(
            f"Finance Signals: "
            f"{len(finance)}"
        )

        lines.append(
            f"Shopping Signals: "
            f"{len(shopping)}"
        )

        lines.append(
            f"Insurance Signals: "
            f"{len(insurance)}"
        )

        return "\n".join(
            lines
        )