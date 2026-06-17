from loguru import logger

from storage.db.database import (
    SessionLocal,
)

from storage.models.expense import (
    Expense,
)


class ExpenseRepository:

    @staticmethod
    def create_expense(
        details,
    ):

        session = (
            SessionLocal()
        )

        try:

            expense = Expense(
                amount=details.get(
                    "amount"
                ),
                currency=details.get(
                    "currency"
                ),
                paid_to=details.get(
                    "paid_to"
                ),
                paid_from=details.get(
                    "paid_from"
                ),
                payment_channel=details.get(
                    "payment_channel"
                ),
                transaction_type=details.get(
                    "transaction_type"
                ),
                transaction_status=details.get(
                    "transaction_status"
                ),
                raw_summary=details.get(
                    "summary"
                ),
            )

            session.add(
                expense
            )

            session.commit()

            logger.success(
                "Expense saved"
            )

        finally:

            session.close()