import json

from storage.repositories.signal_repository import (
    SignalRepository,
)


class DailyDigestGenerator:

    def generate(self):

        finance_signals = (
            SignalRepository
            .get_finance_signals()
        )

        shopping_signals = (
            SignalRepository
            .get_shopping_signals()
        )

        total_credit = 0
        total_debit = 0

        largest_credit = 0
        largest_debit = 0

        credit_count = 0
        debit_count = 0

        deliveries = []

        # ------------------------
        # Finance Analysis
        # ------------------------

        for signal in finance_signals:

            try:

                data = (
                    json.loads(
                        signal.raw_json
                    )
                    if signal.raw_json
                    else {}
                )

                amount = float(
                    data.get(
                        "amount",
                        0,
                    )
                    or 0
                )

                txn_type = (
                    data.get(
                        "transaction_type",
                        "",
                    )
                    .lower()
                )

                if txn_type == "credit":

                    total_credit += amount

                    credit_count += 1

                    largest_credit = max(
                        largest_credit,
                        amount,
                    )

                elif txn_type == "debit":

                    total_debit += amount

                    debit_count += 1

                    largest_debit = max(
                        largest_debit,
                        amount,
                    )

            except Exception:
                pass

        # ------------------------
        # Shopping Analysis
        # ------------------------

        for signal in shopping_signals:

            deliveries.append(
                signal.summary
            )

        net_flow = (
            total_credit
            - total_debit
        )

        # ------------------------
        # Build Digest
        # ------------------------

        lines = []

        lines.append(
            "Jarvis Morning Brief"
        )

        lines.append(
            "===================="
        )

        lines.append("")

        lines.append(
            "FINANCE"
        )

        lines.append(
            f"Credits : {credit_count}"
        )

        lines.append(
            f"Debits  : {debit_count}"
        )

        lines.append(
            f"Money In  : ₹{total_credit:,.2f}"
        )

        lines.append(
            f"Money Out : ₹{total_debit:,.2f}"
        )

        lines.append(
            f"Net Flow  : ₹{net_flow:,.2f}"
        )

        lines.append("")

        lines.append(
            f"Largest Credit : "
            f"₹{largest_credit:,.2f}"
        )

        lines.append(
            f"Largest Debit  : "
            f"₹{largest_debit:,.2f}"
        )

        lines.append("")

        lines.append(
            "SHOPPING"
        )

        if deliveries:

            for item in deliveries:

                lines.append(
                    f"• {item}"
                )

        else:

            lines.append(
                "• No deliveries"
            )

        return "\n".join(
            lines
        )