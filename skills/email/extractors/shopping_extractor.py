import json

from loguru import logger

from configs.constants import (
    TaskType,
)

from intelligence.routing.router import (
    IntelligenceRouter,
)


class ShoppingExtractor:

    def __init__(self):

        self.router = (
            IntelligenceRouter()
        )

    def extract(
        self,
        email,
    ):

        prompt = f"""
Extract shopping/order details.

Return ONLY JSON.

Email:

Subject:
{email["subject"]}

Snippet:
{email["snippet"]}

Body:
{email["body"][:3000]}

Return JSON:

{{
"merchant": null,
"product": null,
"order_status": null,
"delivery_date": null,
"summary": ""
}}
"""

        response = self.router.ask(
            prompt=prompt,
            task_type=TaskType.EMAIL,
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

        except Exception:

            logger.warning(
                "Shopping extraction failed"
            )

            return {
                "merchant":
                None,
                "product":
                None,
                "order_status":
                None,
                "delivery_date":
                None,
                "summary":
                email["subject"],
            }