import json

from configs.constants import (
    TaskType,
)

from intelligence.routing.router import (
    IntelligenceRouter,
)


class TodoExtractor:

    def __init__(self):

        self.router = (
            IntelligenceRouter()
        )

    def extract(
        self,
        email,
    ):

        prompt = f"""
Determine whether
this email creates
an actionable task.

Return ONLY JSON.

Email:

Subject:
{email['subject']}

Snippet:
{email['snippet']}

Body:
{email['body'][:2000]}

JSON:

{{
    "create_task": false,
    "title": "",
    "priority": "",
    "due_date": "",
    "category": ""
}}
"""

        response = (
            self.router.ask(
                prompt=prompt,
                task_type=TaskType.EMAIL,
            )
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

            return {
                "create_task":
                False
            }