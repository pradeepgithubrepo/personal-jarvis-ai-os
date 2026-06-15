import json

from loguru import logger

from configs.constants import (
    TaskType,
)
from intelligence.routing.router import (
    IntelligenceRouter,
)


class EmailClassifier:

    def __init__(self):
        self.router = (
            IntelligenceRouter()
        )

    def classify_email(
        self,
        email_data,
    ):

        prompt = f"""
You are an email classifier.

Classify the email into ONLY one category:

expense
insurance
school
todo
important
ignore

Also classify priority:
high
medium
low

Return ONLY valid JSON.

Email:

Subject:
{email_data["subject"]}

Sender:
{email_data["sender"]}

Snippet:
{email_data["snippet"]}

JSON format:

{{
"category":"",
"priority":"",
"action_required":true
}}
"""

        response = self.router.ask(
            prompt=prompt,
            task_type=TaskType.EMAIL,
        )

        try:
            return json.loads(
                response
            )

        except Exception:
            logger.warning(
                "Failed parsing LLM "
                "response"
            )

            return {
                "category":
                "important",
                "priority":
                "medium",
                "action_required":
                False,
            }