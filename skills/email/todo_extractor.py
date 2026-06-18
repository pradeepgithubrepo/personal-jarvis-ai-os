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
    You are Jarvis Task Intelligence.

    Your job is to determine whether
    this email requires the user to
    take action.

    IMPORTANT:

    Create tasks ONLY when the user
    must do something.

    CREATE TASK examples:

    - Pay a bill
    - Attend a meeting
    - School event
    - Appointment
    - Delivery arriving
    - Submit document
    - Respond to request
    - Complete registration
    - Payment due
    - Renewal due

    DO NOT CREATE TASK examples:

    - Marketing emails
    - Newsletters
    - Investment opportunities
    - Insurance offers
    - Product promotions
    - Blogs
    - Articles
    - Advertisements
    - News digests
    - Educational content
    - Feedback requests

    Email:

    Subject:
    {email['subject']}

    Sender:
    {email['sender']}

    Snippet:
    {email['snippet']}

    Body:
    {email['body'][:2500]}

    Return ONLY JSON:

    {{
        "create_task": false,
        "confidence": 0,
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