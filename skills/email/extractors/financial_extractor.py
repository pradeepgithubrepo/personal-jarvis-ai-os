import json
import re

from loguru import logger

from configs.constants import (
    TaskType,
)

from intelligence.routing.router import (
    IntelligenceRouter,
)


class FinancialExtractor:

    FINANCE_KEYWORDS = [
        "debited",
        "credited",
        "payment",
        "transaction",
        "upi",
        "spent",
        "received",
        "refund",
        "emi",
        "bill",
        "salary",
        "cashback",
        "credit card",
        "bank",
    ]

    def __init__(self):

        self.router = (
            IntelligenceRouter()
        )

    def is_financial_email(
        self,
        email,
    ):

        content = (
            f"{email['subject']} "
            f"{email['snippet']} "
            f"{email['body']}"
        ).lower()

        return any(
            keyword in content
            for keyword
            in self.FINANCE_KEYWORDS
        )

    def extract(
        self,
        email,
    ):

        if not self.is_financial_email(
            email
        ):

            logger.info(
                "Skipping non-financial email"
            )

            return {}

        prompt = f"""
You are a financial
transaction extractor.

Extract ONLY factual data.

Rules:

1. NEVER hallucinate.

2. Detect:
- UPI payment
- UPI received
- card spend
- bank debit
- bank credit
- refund
- salary credit

3. transaction_type:
debit | credit

4. payment_channel:
UPI | Credit Card |
Debit Card | Bank Transfer

5. Use null
if unavailable.

Email:

Subject:
{email["subject"]}

Sender:
{email["sender"]}

Snippet:
{email["snippet"]}

Body:
{email["body"][:3500]}

Return ONLY JSON:

{{
"amount": null,
"currency": null,
"paid_to": null,
"paid_from": null,
"receiver_vpa": null,
"transaction_id": null,
"transaction_type": null,
"payment_channel": null,
"transaction_status": null,
"summary": ""
}}
"""

        response = self.router.ask(
            prompt=prompt,
            task_type=TaskType.EMAIL,
        )

        logger.info(
            f"Finance LLM Raw:\n"
            f"{response}"
        )

        try:

            cleaned = (
                response
                .replace(
                    "```json",
                    "",
                )
                .replace(
                    "```",
                    "",
                )
                .strip()
            )

            return json.loads(
                cleaned
            )

        except Exception as e:

            logger.warning(
                f"Finance extraction "
                f"failed: {e}"
            )

            amount_match = re.search(
                r"Rs\.?\s?([\d,]+(?:\.\d+)?)",
                email["body"],
            )

            amount = None

            if amount_match:

                amount = (
                    amount_match
                    .group(1)
                    .replace(",", "")
                )

            return {
                "amount":
                amount,

                "currency":
                "INR",

                "paid_to":
                None,

                "paid_from":
                email["sender"],

                "receiver_vpa":
                None,

                "transaction_id":
                None,

                "transaction_type":
                None,

                "payment_channel":
                None,

                "transaction_status":
                None,

                "summary":
                email["subject"],
            }