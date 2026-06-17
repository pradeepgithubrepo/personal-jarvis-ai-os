import json

from loguru import logger

from configs.constants import (
    TaskType,
)

from intelligence.routing.router import (
    IntelligenceRouter,
)


class EmailIntentExtractor:

    def __init__(self):

        self.router = (
            IntelligenceRouter()
        )

    def extract_intent(
        self,
        email,
    ):

        prompt = f"""
You are an email intent classifier.

Your job is ONLY to classify.

Return ONLY valid JSON.

Possible intents:

payment_confirmation
transaction_alert
bill_due
delivery_update
shopping_order
insurance_offer
insurance_reminder
otp
school_update
important
ignore

Possible categories:

finance
shopping
insurance
security
education
general

Rules:
- Keep response minimal
- No explanations
- No markdown
- action_required=true only if user must act

Email:

Subject:
{email["subject"]}

Sender:
{email["sender"]}

Snippet:
{email["snippet"]}

Body:
{email["body"][:2500]}

Return JSON:

{{
"intent":"",
"category":"",
"priority":"",
"action_required": false
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
                    ""
                )
                .replace(
                    "```",
                    ""
                )
                .strip()
            )

            return json.loads(
                cleaned
            )

        except Exception:

            logger.warning(
                "Intent parse failed"
            )

            return {
                "intent":
                "important",
                "category":
                "general",
                "priority":
                "medium",
                "action_required":
                False,
                "summary":
                email["subject"],
            }